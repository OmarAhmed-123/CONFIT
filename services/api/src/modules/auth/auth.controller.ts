import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { z } from "zod";
import { OAuthProviderSchema } from "@confit/contracts";
import { OAuthService } from "./oauth.service.js";
import { AuthService } from "./auth.service.js";
import { SessionService } from "./session.service.js";
import { TokenService } from "./token.service.js";
import { GoogleProvider } from "../../providers/google.provider.js";
import { createFacebookProvider } from "../../providers/facebook.provider.js";
import { createInstagramProvider } from "../../providers/instagram.provider.js";
import { createXProvider } from "../../providers/x.provider.js";
import { createTikTokProvider } from "../../providers/tiktok.provider.js";
import type { OAuthProviderId } from "./types.js";

const OAUTH_COOKIE = "oauth_flow";
const RT_COOKIE = "refresh_token";
const AT_COOKIE = "access_token";

function oauthCookieOptions() {
  return { httpOnly: true, sameSite: "lax" as const, secure: true, path: "/" };
}

function tokenCookieOptions() {
  return { httpOnly: true, sameSite: "lax" as const, secure: true, path: "/" };
}

export async function registerAuthController(app: FastifyInstance) {
  const { env, redis } = app.ctx;
  const secureCookies = env.NODE_ENV === "production";
  const devOAuthMockEnabled = env.NODE_ENV !== "production" && env.DEV_OAUTH_MOCK_ENABLED;

  const providers = {
    google: new GoogleProvider(env),
    facebook: createFacebookProvider(env),
    instagram: createInstagramProvider(env),
    x: createXProvider(env),
    tiktok: createTikTokProvider(env)
  } satisfies Record<OAuthProviderId, any>;

  const oauthService = new OAuthService(providers);
  const authService = new AuthService(redis);
  const sessionService = new SessionService(redis);
  const tokenService = new TokenService(env);

  async function completeLogin(
    user: Awaited<ReturnType<typeof authService.upsertUserFromOAuth>>,
    req: FastifyRequest,
    reply: FastifyReply
  ) {
    const refreshToken = crypto.randomUUID() + crypto.randomUUID();
    const session = await sessionService.createSession({
      userId: user.userId,
      role: user.role,
      refreshToken,
      ip: req.ip,
      userAgent: req.headers["user-agent"],
      deviceFingerprint: typeof req.headers["x-device-fingerprint"] === "string" ? req.headers["x-device-fingerprint"] : undefined
    });

    const accessToken = await tokenService.signAccessToken({ sub: user.userId, sid: session.sessionId, role: user.role }, 15 * 60);
    reply.clearCookie(OAUTH_COOKIE, { path: "/" });
    reply.setCookie(AT_COOKIE, accessToken, { ...tokenCookieOptions(), secure: secureCookies, maxAge: 15 * 60 });
    reply.setCookie(RT_COOKIE, `${session.sessionId}.${refreshToken}`, { ...tokenCookieOptions(), secure: secureCookies, maxAge: 60 * 60 * 24 * 30 });
    return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?ok=1`);
  }

  app.get("/auth/:provider", async (req, reply) => {
    const provider = OAuthProviderSchema.parse((req.params as Record<string, unknown>).provider) as OAuthProviderId;
    let start;
    try {
      start = oauthService.start(provider, env.PUBLIC_APP_ORIGIN);
    } catch (error) {
      const isProviderConfigError = error instanceof Error && error.message.includes("not configured");
      if (isProviderConfigError) {
        if (devOAuthMockEnabled) {
          const mockUser = await authService.upsertUserFromOAuth({
            provider,
            providerAccountId: `dev-${provider}`,
            email: `dev-${provider}@confit.local`,
            emailVerified: true,
            name: `Dev ${provider.toUpperCase()} User`
          });
          return completeLogin(mockUser, req, reply);
        }
        const accept = req.headers.accept ?? "";
        if (accept.includes("application/json")) {
          return reply.code(503).send({
            statusCode: 503,
            error: "Service Unavailable",
            message: `${provider.toUpperCase()} OAuth not configured`
          });
        }
        return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=PROVIDER_UNAVAILABLE`);
      }
      throw error;
    }

    // Replay protection: server-side single-use state record (authoritative).
    await redis.set(`oauth:state:${start.state}`, JSON.stringify({ provider, nonce: start.nonce, codeVerifier: start.codeVerifier }), "EX", 10 * 60);

    reply.setCookie(
      OAUTH_COOKIE,
      JSON.stringify({ provider, state: start.state, nonce: start.nonce, codeVerifier: start.codeVerifier }),
      { ...oauthCookieOptions(), secure: secureCookies, signed: true, maxAge: 10 * 60 }
    );
    return reply.redirect(start.authorizeUrl);
  });

  app.get("/auth/callback/:provider", async (req, reply) => {
    const provider = OAuthProviderSchema.parse((req.params as Record<string, unknown>).provider) as OAuthProviderId;
    const q = z
      .object({
        code: z.string().min(1).optional(),
        state: z.string().min(1).optional(),
        error: z.string().optional()
      })
      .parse(req.query as Record<string, unknown>);

    if (q.error) return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=PROVIDER_DENIED`);
    if (!q.code || !q.state) return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=TOKEN_FAILED`);

    const flowRaw = (req.cookies as Record<string, string | undefined>)?.[OAUTH_COOKIE];
    const unsignedFlow = flowRaw ? reply.unsignCookie(flowRaw) : null;
    const flow = unsignedFlow && unsignedFlow.valid && unsignedFlow.value ? JSON.parse(unsignedFlow.value) : null;
    if (!flow || flow.provider !== provider) return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=INVALID_STATE`);
    if (flow.state !== q.state) return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=INVALID_STATE`);

    try {
      const serverStateRaw = await redis.get(`oauth:state:${q.state}`);
      if (!serverStateRaw) return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=INVALID_STATE`);
      await redis.del(`oauth:state:${q.state}`);
      const serverState = JSON.parse(serverStateRaw) as { provider: OAuthProviderId; nonce: string; codeVerifier: string };
      if (serverState.provider !== provider) return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=INVALID_STATE`);

      const profile = await oauthService.exchangeAndNormalize(provider, {
        code: q.code,
        codeVerifier: serverState.codeVerifier,
        nonce: serverState.nonce
      });
      const user = await authService.upsertUserFromOAuth(profile);
      return completeLogin(user, req, reply);
    } catch (e) {
      app.log.error({ err: e }, "oauth callback failed");
      return reply.redirect(`${env.PUBLIC_APP_ORIGIN}/callback?error=TOKEN_FAILED`);
    }
  });

  app.post("/api/auth/refresh", async (req, reply) => {
    const rt = (req.cookies as Record<string, string | undefined>)?.[RT_COOKIE];
    if (!rt || typeof rt !== "string" || !rt.includes(".")) return reply.code(401).send({ error: "SESSION_EXPIRED" });
    const [sessionId, token] = rt.split(".", 2);
    try {
      const rotated = await sessionService.rotateRefreshToken(sessionId, token);
      const accessToken = await tokenService.signAccessToken({
        sub: rotated.session.userId,
        sid: rotated.session.sessionId,
        role: rotated.session.role
      }, 15 * 60);
      reply.setCookie(AT_COOKIE, accessToken, { ...tokenCookieOptions(), secure: secureCookies, maxAge: 15 * 60 });
      reply.setCookie(RT_COOKIE, `${rotated.session.sessionId}.${rotated.newRefreshToken}`, { ...tokenCookieOptions(), secure: secureCookies, maxAge: 60 * 60 * 24 * 30 });
      return { ok: true };
    } catch (e) {
      return reply.code(401).send({ error: "SESSION_EXPIRED" });
    }
  });

  app.post("/api/auth/logout", async (req, reply) => {
    const rt = (req.cookies as Record<string, string | undefined>)?.[RT_COOKIE];
    if (typeof rt === "string" && rt.includes(".")) {
      const [sessionId] = rt.split(".", 2);
      await sessionService.revokeSession(sessionId, "user_logout");
    }
    reply.clearCookie(AT_COOKIE, { path: "/" });
    reply.clearCookie(RT_COOKIE, { path: "/" });
    return { ok: true };
  });

  app.get("/api/auth/me", async (req, reply) => {
    const at = (req.cookies as Record<string, string | undefined>)?.[AT_COOKIE];
    if (!at || typeof at !== "string") return reply.code(401).send({ error: "SESSION_EXPIRED" });
    try {
      const claims = await tokenService.verifyAccessToken(at);
      const user = await authService.getUser(claims.sub);
      if (!user) return reply.code(401).send({ error: "SESSION_EXPIRED" });
      await sessionService.touchSession(claims.sid);
      return { user };
    } catch {
      return reply.code(401).send({ error: "SESSION_EXPIRED" });
    }
  });

  app.get("/api/auth/sessions", async (req, reply) => {
    const at = (req.cookies as Record<string, string | undefined>)?.[AT_COOKIE];
    if (!at || typeof at !== "string") return reply.code(401).send({ error: "SESSION_EXPIRED" });
    try {
      const claims = await tokenService.verifyAccessToken(at);
      const sessions = await sessionService.listUserSessions(claims.sub);
      return {
        sessions: sessions.map((session) => ({
          sessionId: session.sessionId,
          userId: session.userId,
          role: session.role,
          createdAt: session.createdAt,
          lastSeenAt: session.lastSeenAt,
          ip: session.ip,
          userAgent: session.userAgent,
          deviceFingerprint: session.deviceFingerprint,
          isCurrent: session.sessionId === claims.sid
        }))
      };
    } catch {
      return reply.code(401).send({ error: "SESSION_EXPIRED" });
    }
  });

  app.post("/api/auth/sessions/revoke", async (req, reply) => {
    const at = (req.cookies as Record<string, string | undefined>)?.[AT_COOKIE];
    if (!at || typeof at !== "string") return reply.code(401).send({ error: "SESSION_EXPIRED" });
    const body = z.object({ sessionId: z.string().min(1) }).parse(req.body as Record<string, unknown>);
    try {
      const claims = await tokenService.verifyAccessToken(at);
      const targetSession = await sessionService.getSession(body.sessionId);
      if (!targetSession || targetSession.userId !== claims.sub) return reply.code(404).send({ error: "SESSION_NOT_FOUND" });
      await sessionService.revokeSession(body.sessionId, "user_revoke");
      if (body.sessionId === claims.sid) {
        reply.clearCookie(AT_COOKIE, { path: "/" });
        reply.clearCookie(RT_COOKIE, { path: "/" });
      }
      return { ok: true };
    } catch {
      return reply.code(401).send({ error: "SESSION_EXPIRED" });
    }
  });

  app.post("/api/auth/logout-all", async (req, reply) => {
    const at = (req.cookies as Record<string, string | undefined>)?.[AT_COOKIE];
    if (!at || typeof at !== "string") return reply.code(401).send({ error: "SESSION_EXPIRED" });
    try {
      const claims = await tokenService.verifyAccessToken(at);
      await sessionService.revokeAllUserSessions(claims.sub, "logout_all");
      reply.clearCookie(AT_COOKIE, { path: "/" });
      reply.clearCookie(RT_COOKIE, { path: "/" });
      return { ok: true };
    } catch {
      return reply.code(401).send({ error: "SESSION_EXPIRED" });
    }
  });
}

