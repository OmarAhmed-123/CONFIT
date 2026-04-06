import { Queue } from "bullmq";
import type Redis from "ioredis";
import type { MemoryRedis } from "./memoryRedis.js";

export type Queues = {
  notifications: { add: Queue["add"] };
};

export function createQueues(redis: Redis | MemoryRedis): Queues {
  if ("store" in (redis as any)) {
    return {
      notifications: { add: async () => ({ id: "test" } as any) }
    };
  }
  const connection = (redis as Redis).duplicate();
  return {
    notifications: new Queue("notifications", { connection })
  };
}

