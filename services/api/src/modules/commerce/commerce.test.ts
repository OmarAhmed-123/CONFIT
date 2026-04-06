import { describe, it, expect } from "vitest";
import { buildApp } from "../../app.js";
import { generateKeyPairSync } from "node:crypto";
import { AuthService } from "../auth/auth.service.js";
import { SessionService } from "../auth/session.service.js";
import { TokenService } from "../auth/token.service.js";

function setBaseEnv() {
  process.env.NODE_ENV = "test";
  process.env.PORT = "4001";
  process.env.PUBLIC_APP_ORIGIN = "http://localhost:3000";
  process.env.REDIS_URL = "redis://localhost:6379";
  process.env.COOKIE_SECRET = "x".repeat(40);
  process.env.JWT_ISSUER = "confit";
  process.env.JWT_AUDIENCE = "confit-web";
  const kp = generateKeyPairSync("rsa", { modulusLength: 2048 });
  process.env.JWT_PRIVATE_KEY_PEM = kp.privateKey.export({ type: "pkcs8", format: "pem" }).toString();
  process.env.JWT_PUBLIC_KEY_PEM = kp.publicKey.export({ type: "spki", format: "pem" }).toString();
}

async function createAuthedCookies(app: Awaited<ReturnType<typeof buildApp>>) {
  const auth = new AuthService(app.ctx.redis as any);
  const sessions = new SessionService(app.ctx.redis as any);
  const tokens = new TokenService(app.ctx.env);

  const user = await auth.upsertUserFromOAuth({
    provider: "google",
    providerAccountId: "acct1",
    email: "test@example.com",
    emailVerified: true,
    name: "Test User"
  });

  const refreshToken = "rt_" + crypto.randomUUID();
  const session = await sessions.createSession({ userId: user.userId, role: user.role, refreshToken });
  const access = await tokens.signAccessToken({ sub: user.userId, sid: session.sessionId, role: user.role }, 15 * 60);

  return {
    access_token: access,
    refresh_token: `${session.sessionId}.${refreshToken}`,
    csrf_token: "csrf123"
  };
}

describe("commerce security", () => {
  it("blocks write without CSRF", async () => {
    setBaseEnv();
    const app = await buildApp();
    const cookies = await createAuthedCookies(app);

    const res = await app.inject({
      method: "POST",
      url: "/api/orders",
      cookies,
      payload: { amountCents: 5000, currency: "usd" }
    });
    expect(res.statusCode).toBe(400); // CSRF missing header
    await app.close();
  });

  it("requires idempotency key on payments confirm", async () => {
    setBaseEnv();
    const app = await buildApp();
    const cookies = await createAuthedCookies(app);

    const orderRes = await app.inject({
      method: "POST",
      url: "/api/orders",
      cookies,
      headers: { "x-csrf-token": "csrf123" },
      payload: { amountCents: 5000, currency: "usd" }
    });
    expect(orderRes.statusCode).toBe(200);
    const order = orderRes.json();

    const res = await app.inject({
      method: "POST",
      url: "/api/payments/confirm",
      cookies,
      headers: { "x-csrf-token": "csrf123" },
      payload: { orderId: order.orderId }
    });
    expect(res.statusCode).toBe(400); // missing Idempotency-Key
    await app.close();
  });
});

