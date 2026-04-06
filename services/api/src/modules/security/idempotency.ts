import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import type { AnyRedis } from "../../infra/redis.js";

function keyFor(req: FastifyRequest) {
  const k = req.headers["idempotency-key"];
  if (!k || typeof k !== "string") throw new Error("IDEMPOTENCY_KEY_REQUIRED");
  const userPart = req.user?.userId ?? req.ip;
  return `idem:${userPart}:${req.method}:${req.url.split("?")[0]}:${k}`;
}

export function idempotencyPreHandler(redis: AnyRedis) {
  return async (req: FastifyRequest, reply: FastifyReply) => {
    const k = keyFor(req);
    const existing = await redis.get(k);
    if (existing) {
      const parsed = JSON.parse(existing) as { statusCode: number; body: any; headers?: Record<string, string> };
      if (parsed.headers) {
        for (const [hk, hv] of Object.entries(parsed.headers)) reply.header(hk, hv);
      }
      return reply.code(parsed.statusCode).send(parsed.body);
    }

    reply.header("Idempotency-Key", req.headers["idempotency-key"] as string);

    const originalSend = reply.send.bind(reply);
    reply.send = ((payload?: any) => {
      // best-effort cache: only cache JSON-ish bodies
      const statusCode = reply.statusCode;
      void (async () => {
        try {
          await redis.set(
            k,
            JSON.stringify({ statusCode, body: payload }),
            "EX",
            60 * 10
          );
        } catch {
          // ignore
        }
      })();
      return originalSend(payload);
    }) as any;
  };
}

export async function registerIdempotency(app: FastifyInstance) {
  // no-op placeholder for future global wiring
  void app;
}

