/**
 * Fastify commerce + Stripe — used by Next.js / @confit/contracts clients.
 * Unified Paymob / PayPal / invoice ledger: FastAPI only (`routers/payment_platform.py`, `/api/payments/unified/*`).
 * Do not duplicate new provider logic here; proxy or call Python when extending checkout.
 */
import type { FastifyInstance } from "fastify";
import {
  CreateOrderInputSchema,
  PaymentConfirmRequestSchema,
  PaymentConfirmResponseSchema,
  PaymentIntentRequestSchema,
  PaymentIntentResponseSchema
} from "@confit/contracts";
import { requireAuth } from "../auth/auth.middleware.js";
import { idempotencyPreHandler } from "../security/idempotency.js";
import { OrderService } from "../orders/order.service.js";
import { PaymentService } from "../payments/payment.service.js";
import { NotificationService } from "../notifications/notification.service.js";
import type { WsHub } from "../notifications/realtime.js";
import { AuthService } from "../auth/auth.service.js";

export async function registerCommerce(app: FastifyInstance, wsHub: WsHub) {
  const authGuard = requireAuth(app);
  const orders = new OrderService(app.ctx.redis);
  const payments = new PaymentService(app.ctx.env, app.ctx.redis);

  app.get("/api/payments/config", async () => {
    const pk = payments.getPublishableKey();
    const enabled = payments.isStripeReady();
    return { stripe_enabled: enabled, publishable_key: enabled ? pk : null };
  });

  app.post(
    "/api/payments/intent",
    { preHandler: [authGuard, idempotencyPreHandler(app.ctx.redis)] },
    async (req, reply) => {
      const body = PaymentIntentRequestSchema.parse(req.body);
      const order = await orders.getOrder(body.orderId);
      if (!order || order.userId !== req.user!.userId) return reply.code(404).send({ error: "ORDER_NOT_FOUND" });
      if (order.status !== "CREATED" && order.status !== "PAYMENT_PENDING") {
        return reply.code(400).send({ error: "ORDER_NOT_PAYABLE" });
      }
      const idem = String(req.headers["idempotency-key"]);
      const created = await payments.createPaymentIntent({
        orderId: order.orderId,
        amountCents: order.amountCents,
        currency: order.currency,
        idempotencyKey: idem
      });
      if (!created) {
        return reply.code(503).send({ error: "STRIPE_NOT_CONFIGURED" });
      }
      const pk = payments.getPublishableKey();
      if (!pk) return reply.code(503).send({ error: "STRIPE_PUBLISHABLE_KEY_MISSING" });
      return PaymentIntentResponseSchema.parse({
        clientSecret: created.clientSecret,
        publishableKey: pk,
        paymentIntentId: created.paymentIntentId
      });
    }
  );
  const notifications = new NotificationService(app.ctx.redis);
  const auth = new AuthService(app.ctx.redis);

  // Mode B: structured flow
  app.post(
    "/api/orders",
    { preHandler: authGuard },
    async (req) => {
      const body = CreateOrderInputSchema.parse(req.body);
      const amountCents =
        typeof body.amountCents === "number"
          ? body.amountCents
          : Math.round((body.items ?? []).reduce((sum, item) => sum + item.price * item.quantity, 0) * 100);
      return await orders.createOrder({ userId: req.user!.userId, amountCents, currency: body.currency });
    }
  );

  app.post(
    "/api/payments/confirm",
    { preHandler: [authGuard, idempotencyPreHandler(app.ctx.redis)] },
    async (req, reply) => {
      const body = PaymentConfirmRequestSchema.parse(req.body);
      const order = await orders.getOrder(body.orderId);
      if (!order || order.userId !== req.user!.userId) return reply.code(404).send({ error: "ORDER_NOT_FOUND" });
      if (order.status === "CONFIRMED") {
        return PaymentConfirmResponseSchema.parse({
          ok: true,
          orderId: order.orderId,
          paymentStatus: "CONFIRMED",
          order,
        });
      }

      await orders.setStatus(order.orderId, "PAYMENT_PENDING");
      const idem = String(req.headers["idempotency-key"]);
      const result = await payments.confirmPayment({
        orderId: order.orderId,
        amountCents: order.amountCents,
        currency: order.currency,
        idempotencyKey: idem,
        paymentIntentId: body.paymentIntentId
      });

      if (result.status !== "CONFIRMED") return reply.code(402).send({ error: "PAYMENT_NOT_CONFIRMED", result });

      const confirmed = await orders.setStatus(order.orderId, "CONFIRMED");

      const user = await auth.getUser(req.user!.userId);
      const payload = {
        type: "PICKUP_REQUEST" as const,
        customerName: user?.name ?? "Customer",
        locationName: "CONFIT Store",
        pickupTime: "6:30 PM",
        orderId: confirmed.orderId
      };
      wsHub.sendToUser(req.user!.userId, payload);
      await notifications.storeForPolling(req.user!.userId, payload);
      await app.ctx.queues.notifications.add("pickup", { userId: req.user!.userId, payload }, { attempts: 5, backoff: { type: "exponential", delay: 500 } });

      return PaymentConfirmResponseSchema.parse({
        ok: true,
        orderId: confirmed.orderId,
        paymentStatus: result.status,
        order: confirmed,
      });
    }
  );

  // Mode A: fast flow (auto-switch based on trust + low-risk)
  app.post(
    "/api/checkout/confirm",
    { preHandler: [authGuard, idempotencyPreHandler(app.ctx.redis)] },
    async (req, reply) => {
      const body = CreateOrderInputSchema.parse(req.body);
      const user = await auth.getUser(req.user!.userId);
      const amountCents =
        typeof body.amountCents === "number"
          ? body.amountCents
          : Math.round((body.items ?? []).reduce((sum, item) => sum + item.price * item.quantity, 0) * 100);

      const lowRisk = amountCents <= 10_000; // $100
      const trusted = user?.trustLevel === "trusted";
      if (!(trusted && lowRisk)) {
        const order = await orders.createOrder({ userId: req.user!.userId, amountCents, currency: body.currency });
        return reply.code(409).send({ error: "STRUCTURED_FLOW_REQUIRED", orderId: order.orderId });
      }

      const order = await orders.createOrder({ userId: req.user!.userId, amountCents, currency: body.currency });
      const idem = String(req.headers["idempotency-key"]);
      const result = await payments.confirmPayment({
        orderId: order.orderId,
        amountCents: order.amountCents,
        currency: order.currency,
        idempotencyKey: idem
      });
      if (result.status !== "CONFIRMED") return reply.code(402).send({ error: "PAYMENT_NOT_CONFIRMED", result });

      const confirmed = await orders.setStatus(order.orderId, "CONFIRMED");
      const payload = {
        type: "PICKUP_REQUEST" as const,
        customerName: user?.name ?? "Customer",
        locationName: "CONFIT Store",
        pickupTime: "6:30 PM",
        orderId: confirmed.orderId
      };
      wsHub.sendToUser(req.user!.userId, payload);
      await notifications.storeForPolling(req.user!.userId, payload);
      await app.ctx.queues.notifications.add("pickup", { userId: req.user!.userId, payload }, { attempts: 5, backoff: { type: "exponential", delay: 500 } });

      return { ok: true, order: confirmed, mode: "A" };
    }
  );

  // Polling fallback
  app.get("/api/notifications/poll", { preHandler: authGuard }, async (req) => {
    return { notifications: await notifications.poll(req.user!.userId) };
  });
}

