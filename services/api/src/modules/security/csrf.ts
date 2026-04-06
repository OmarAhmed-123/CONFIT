import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { nanoid } from "nanoid";

export const CSRF_COOKIE = "csrf_token";

export function setCsrfCookie(reply: FastifyReply, secure: boolean) {
  const token = nanoid(32);
  reply.setCookie(CSRF_COOKIE, token, {
    httpOnly: false,
    sameSite: "lax",
    secure,
    path: "/"
  });
  return token;
}

export function requireCsrf(req: FastifyRequest) {
  const cookieToken = (req.cookies as any)?.[CSRF_COOKIE];
  const headerToken = req.headers["x-csrf-token"];
  if (!cookieToken || typeof cookieToken !== "string") throw new Error("CSRF_MISSING_COOKIE");
  if (!headerToken || typeof headerToken !== "string") throw new Error("CSRF_MISSING_HEADER");
  if (cookieToken !== headerToken) throw new Error("CSRF_MISMATCH");
}

export async function registerCsrf(app: FastifyInstance) {
  app.addHook("onRequest", async (req, reply) => {
    // Ensure token exists for browser to echo back.
    const existing = (req.cookies as any)?.[CSRF_COOKIE];
    if (!existing) setCsrfCookie(reply, app.ctx.env.NODE_ENV === "production");
  });

  app.addHook("preHandler", async (req) => {
    const method = req.method.toUpperCase();
    const isWrite = !["GET", "HEAD", "OPTIONS"].includes(method);
    const path = req.url.split("?")[0] ?? "";
    const exempt =
      path.startsWith("/auth/") || // OAuth redirects/callbacks rely on state cookie, not CSRF header
      path.startsWith("/webhooks/") || // webhooks use signatures
      path === "/health";

    if (isWrite && !exempt) requireCsrf(req);
  });

  app.setErrorHandler((err, req, reply) => {
    const msg = err instanceof Error ? err.message : "";
    if (msg.startsWith("CSRF_")) return reply.code(400).send({ error: msg });
    if (msg === "IDEMPOTENCY_KEY_REQUIRED") return reply.code(400).send({ error: msg });
    if (msg === "UNAUTHENTICATED") return reply.code(401).send({ error: "SESSION_EXPIRED" });
    return reply.send(err);
  });
}

