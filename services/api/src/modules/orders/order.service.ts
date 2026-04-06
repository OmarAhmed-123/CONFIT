import { nanoid } from "nanoid";
import type { AnyRedis } from "../../infra/redis.js";

export type OrderStatus = "CREATED" | "PAYMENT_PENDING" | "CONFIRMED" | "CANCELLED";

export type Order = {
  orderId: string;
  userId: string;
  amountCents: number;
  currency: string;
  status: OrderStatus;
  createdAt: number;
  updatedAt: number;
};

function orderKey(orderId: string) {
  return `order:${orderId}`;
}

export class OrderService {
  constructor(private redis: AnyRedis) {}

  async createOrder(input: { userId: string; amountCents: number; currency: string }): Promise<Order> {
    const now = Date.now();
    const order: Order = {
      orderId: `CF${nanoid(10).toUpperCase()}`,
      userId: input.userId,
      amountCents: input.amountCents,
      currency: input.currency,
      status: "CREATED",
      createdAt: now,
      updatedAt: now
    };
    await this.redis.set(orderKey(order.orderId), JSON.stringify(order), "EX", 60 * 60 * 24);
    return order;
  }

  async getOrder(orderId: string): Promise<Order | null> {
    const raw = await this.redis.get(orderKey(orderId));
    if (!raw) return null;
    return JSON.parse(raw) as Order;
  }

  async setStatus(orderId: string, status: OrderStatus): Promise<Order> {
    const order = await this.getOrder(orderId);
    if (!order) throw new Error("ORDER_NOT_FOUND");
    order.status = status;
    order.updatedAt = Date.now();
    await this.redis.set(orderKey(orderId), JSON.stringify(order), "EX", 60 * 60 * 24);
    return order;
  }
}

