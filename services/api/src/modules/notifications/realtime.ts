import type { FastifyInstance } from "fastify";
import type { WebSocket } from "ws";
import { TokenService } from "../auth/token.service.js";

export type WsHub = {
  sendToUser: (userId: string, payload: any) => void;
};

export function registerRealtime(app: FastifyInstance): WsHub {
  const tokenService = new TokenService(app.ctx.env);
  const conns = new Map<string, Set<WebSocket>>();

  app.get(
    "/ws",
    { websocket: true },
    async (socket: WebSocket, req) => {
      try {
        const at = (req.cookies as any)?.access_token;
        if (!at || typeof at !== "string") throw new Error("UNAUTHENTICATED");
        const claims = await tokenService.verifyAccessToken(at);
        const userId = claims.sub;

        const set = conns.get(userId) ?? new Set();
        set.add(socket);
        conns.set(userId, set);

        socket.on("close", () => {
          const s = conns.get(userId);
          if (!s) return;
          s.delete(socket);
          if (s.size === 0) conns.delete(userId);
        });
      } catch {
        socket.close();
      }
    }
  );

  return {
    sendToUser(userId: string, payload: any) {
      const set = conns.get(userId);
      if (!set) return;
      const msg = JSON.stringify(payload);
      for (const sock of set) {
        try {
          sock.send(msg);
        } catch {
          // ignore
        }
      }
    }
  };
}

