import { describe, it, expect } from "vitest";
import { buildApp } from "../../app.js";
import { generateKeyPairSync } from "node:crypto";

describe("auth", () => {
  it("rejects callback with missing state cookie", async () => {
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

    const app = await buildApp();
    const res = await app.inject({
      method: "GET",
      url: "/auth/callback/google?code=abc&state=def"
    });
    expect(res.statusCode).toBe(302);
    expect(res.headers.location).toContain("error=INVALID_STATE");
    await app.close();
  });
});

