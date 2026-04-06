import type { UserRole } from "@confit/contracts";
import { importPKCS8, importSPKI, SignJWT, jwtVerify } from "jose";
import type { Env } from "../../config/env.js";

export type AccessTokenClaims = {
  sub: string;
  sid: string;
  role: UserRole;
};

export class TokenService {
  private env: Env;
  constructor(env: Env) {
    this.env = env;
  }

  async signAccessToken(claims: AccessTokenClaims, ttlSeconds: number): Promise<string> {
    const privateKey = await importPKCS8(this.env.JWT_PRIVATE_KEY_PEM!, "RS256");
    const now = Math.floor(Date.now() / 1000);
    return await new SignJWT({ sid: claims.sid, role: claims.role })
      .setProtectedHeader({ alg: "RS256", typ: "JWT" })
      .setIssuer(this.env.JWT_ISSUER)
      .setAudience(this.env.JWT_AUDIENCE)
      .setSubject(claims.sub)
      .setIssuedAt(now)
      .setExpirationTime(now + ttlSeconds)
      .setJti(crypto.randomUUID())
      .sign(privateKey);
  }

  async verifyAccessToken(token: string): Promise<AccessTokenClaims> {
    const publicKey = await importSPKI(this.env.JWT_PUBLIC_KEY_PEM!, "RS256");
    const { payload } = await jwtVerify(token, publicKey, {
      issuer: this.env.JWT_ISSUER,
      audience: this.env.JWT_AUDIENCE
    });
    const sub = payload.sub;
    const sid = payload.sid;
    const role = payload.role;
    if (typeof sub !== "string" || typeof sid !== "string" || (role !== "user" && role !== "admin" && role !== "super_admin")) {
      throw new Error("Invalid token claims");
    }
    return { sub, sid, role };
  }
}

