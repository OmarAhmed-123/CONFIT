import type { AnyRedis } from "../../infra/redis.js";

export type PickupNotification = {
  type: "PICKUP_REQUEST";
  customerName: string;
  locationName: string;
  pickupTime: string;
  orderId: string;
};

export class NotificationService {
  constructor(private redis: AnyRedis) {}

  async storeForPolling(userId: string, payload: PickupNotification) {
    const key = `notif:${userId}`;
    await this.redis.lpush(key, JSON.stringify({ ts: Date.now(), payload }));
    await this.redis.ltrim(key, 0, 50);
    await this.redis.expire(key, 60 * 60);
  }

  async poll(userId: string): Promise<PickupNotification[]> {
    const key = `notif:${userId}`;
    const items = await this.redis.lrange(key, 0, 10);
    return items.map((s) => (JSON.parse(s) as any).payload) as PickupNotification[];
  }
}

