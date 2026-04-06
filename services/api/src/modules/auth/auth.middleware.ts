import type { UserRole } from "@confit/contracts";
import type { FastifyInstance, FastifyRequest } from "fastify";
import { TokenService } from "./token.service.js";

export type AuthedUser = {
  userId: string;
  sessionId: string;
  role: UserRole;
};

declare module "fastify" {
  interface FastifyRequest {
    user?: AuthedUser;
  }
}

export function requireAuth(app: FastifyInstance) {
  const tokenService = new TokenService(app.ctx.env);
  return async function (req: FastifyRequest) {
    const at = (req.cookies as Record<string, string | undefined>)?.access_token;
    if (!at || typeof at !== "string") throw new Error("UNAUTHENTICATED");
    const claims = await tokenService.verifyAccessToken(at);
    req.user = { userId: claims.sub, sessionId: claims.sid, role: claims.role };
  };
}

