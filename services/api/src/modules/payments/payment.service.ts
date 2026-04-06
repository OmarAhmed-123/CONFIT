import Stripe from "stripe";
import type { AnyRedis } from "../../infra/redis.js";
import type { Env } from "../../config/env.js";

export type PaymentResult = {
  provider: "stripe" | "mock";
  providerPaymentId: string;
  status: "CONFIRMED" | "REQUIRES_ACTION" | "FAILED";
};

export class PaymentService {
  private stripe: Stripe | null;

  constructor(private env: Env, private redis: AnyRedis) {
    this.stripe = env.STRIPE_SECRET_KEY ? new Stripe(env.STRIPE_SECRET_KEY, { apiVersion: "2025-02-24.acacia" as any }) : null;
  }

  getPublishableKey(): string | null {
    const pk = this.env.STRIPE_PUBLISHABLE_KEY?.trim();
    return pk || null;
  }

  isStripeReady(): boolean {
    return Boolean(this.stripe && this.getPublishableKey());
  }

  async createPaymentIntent(input: {
    orderId: string;
    amountCents: number;
    currency: string;
    idempotencyKey: string;
  }): Promise<{ clientSecret: string; paymentIntentId: string } | null> {
    if (!this.stripe) return null;
    const intent = await this.stripe.paymentIntents.create(
      {
        amount: input.amountCents,
        currency: input.currency,
        automatic_payment_methods: { enabled: true },
        metadata: { orderId: input.orderId }
      },
      { idempotencyKey: `${input.idempotencyKey}:pi` }
    );
    if (!intent.client_secret) return null;
    return { clientSecret: intent.client_secret, paymentIntentId: intent.id };
  }

  async confirmPayment(input: {
    orderId: string;
    amountCents: number;
    currency: string;
    idempotencyKey: string;
    paymentIntentId?: string;
  }): Promise<PaymentResult> {
    if (!this.stripe) {
      if (this.env.NODE_ENV === "production") {
        return { provider: "mock", providerPaymentId: "none", status: "FAILED" };
      }
      const pid = `mock_${input.orderId}`;
      await this.redis.set(`pay:${input.orderId}`, JSON.stringify({ pid, status: "CONFIRMED" }), "EX", 60 * 60 * 24);
      return { provider: "mock", providerPaymentId: pid, status: "CONFIRMED" };
    }

    if (!input.paymentIntentId) {
      return { provider: "stripe", providerPaymentId: "none", status: "FAILED" };
    }

    const intent = await this.stripe.paymentIntents.retrieve(input.paymentIntentId);
    if (intent.metadata?.orderId && intent.metadata.orderId !== input.orderId) {
      return { provider: "stripe", providerPaymentId: intent.id, status: "FAILED" };
    }
    if (intent.amount !== input.amountCents) {
      return { provider: "stripe", providerPaymentId: intent.id, status: "FAILED" };
    }

    const status =
      intent.status === "succeeded"
        ? "CONFIRMED"
        : intent.status === "requires_action"
          ? "REQUIRES_ACTION"
          : "FAILED";

    await this.redis.set(
      `pay:${input.orderId}`,
      JSON.stringify({ pid: intent.id, status, rawStatus: intent.status }),
      "EX",
      60 * 60 * 24
    );
    return { provider: "stripe", providerPaymentId: intent.id, status };
  }
}
