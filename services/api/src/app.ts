import Fastify, { type FastifyInstance } from "fastify";
import cors from "@fastify/cors";
import cookie from "@fastify/cookie";
import helmet from "@fastify/helmet";
import rateLimit from "@fastify/rate-limit";
import websocket from "@fastify/websocket";
import { loadEnv, type Env } from "./config/env.js";
import { createRedis, isMemoryRedis } from "./infra/redis.js";
import { createQueues, type Queues } from "./infra/queue.js";
import { registerCsrf } from "./modules/security/csrf.js";
import { registerAuthController } from "./modules/auth/auth.controller.js";
import { registerRealtime, type WsHub } from "./modules/notifications/realtime.js";
import { registerCommerce } from "./modules/commerce/routes.js";
import { registerIntegrationsRoutes } from "./modules/integrations/routes.js";

export type AppContext = {
  env: Env;
  redis: ReturnType<typeof createRedis>;
  queues: Queues;
};

export async function buildApp(): Promise<FastifyInstance> {
  const env = loadEnv(process.env);

  const app = Fastify({
    logger: {
      level: env.NODE_ENV === "production" ? "info" : "debug"
    },
    trustProxy: true
  });

  let redis = createRedis(env);
  // Development resilience: if Redis isn't available locally, fall back to in-memory
  if (!isMemoryRedis(redis)) {
    try {
      await (redis as any).connect?.();
      await (redis as any).ping?.();
    } catch (e) {
      app.log.warn({ err: e }, "Redis unavailable; falling back to in-memory store");
      try {
        await (redis as any).quit?.();
      } catch {
        // ignore
      }
      redis = createRedis({ ...env, NODE_ENV: "test" });
    }
  }
  const queues = createQueues(redis as any);

  app.decorate("ctx", { env, redis, queues } satisfies AppContext);

  await app.register(helmet, {
    global: true,
    contentSecurityPolicy: env.NODE_ENV === "production" ? undefined : false
  });

  await app.register(cors, {
    origin: [env.PUBLIC_APP_ORIGIN],
    credentials: true
  });

  await app.register(cookie, {
    hook: "onRequest",
    secret: env.COOKIE_SECRET
  });

  await app.register(rateLimit, {
    global: true,
    max: 300,
    timeWindow: "1 minute",
    keyGenerator: (req) => req.ip
  });

  await app.register(websocket);

  await registerCsrf(app);
  await registerAuthController(app);
  const wsHub = registerRealtime(app);
  await registerCommerce(app, wsHub);
  await registerIntegrationsRoutes(app);

  app.get("/health", async () => ({ ok: true }));

  return app;
}

declare module "fastify" {
  interface FastifyInstance {
    ctx: AppContext;
  }
}

