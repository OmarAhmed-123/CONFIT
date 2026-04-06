import Redis from "ioredis";
import type { Env } from "../config/env.js";
import { MemoryRedis } from "./memoryRedis.js";

export type AnyRedis = Redis | MemoryRedis;

export function isMemoryRedis(r: AnyRedis): r is MemoryRedis {
  return r instanceof MemoryRedis;
}

export function createRedis(env: Env): AnyRedis {
  if (env.NODE_ENV === "test") return new MemoryRedis();
  const client = new Redis(env.REDIS_URL, {
    maxRetriesPerRequest: null,
    enableReadyCheck: true,
    lazyConnect: true
  });
  // Prevent noisy unhandled-error events; connection failures are handled by app fallback logic.
  client.on("error", () => {});
  return client;
}

