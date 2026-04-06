import { z } from "zod";

export const CurrencySchema = z.string().min(3).max(3).transform((v) => v.toLowerCase());

export const OrderLineItemSchema = z.object({
  productId: z.union([z.string(), z.number()]).transform((v) => String(v)),
  price: z.number().positive(),
  quantity: z.number().int().positive()
});

export const CreateOrderInputSchema = z.object({
  amountCents: z.number().int().positive().optional(),
  currency: CurrencySchema.default("usd"),
  items: z.array(OrderLineItemSchema).min(1).optional()
}).refine((value) => Boolean(value.amountCents) || Boolean(value.items?.length), {
  message: "amountCents or items is required"
});

export const OrderStatusSchema = z.enum(["CREATED", "PAYMENT_PENDING", "CONFIRMED", "CANCELLED"]);
export type OrderStatus = z.infer<typeof OrderStatusSchema>;

export const PaymentStatusSchema = z.enum(["CONFIRMED", "REQUIRES_ACTION", "FAILED"]);
export type PaymentStatus = z.infer<typeof PaymentStatusSchema>;

export const PaymentConfirmRequestSchema = z.object({
  orderId: z.string().min(3),
  /** Set after Stripe.js confirms PaymentIntent (Node API + Stripe). */
  paymentIntentId: z.string().min(3).optional()
});
export type PaymentConfirmRequest = z.infer<typeof PaymentConfirmRequestSchema>;

export const PaymentIntentRequestSchema = z.object({
  orderId: z.string().min(3)
});
export type PaymentIntentRequest = z.infer<typeof PaymentIntentRequestSchema>;

export const PaymentIntentResponseSchema = z.object({
  clientSecret: z.string(),
  publishableKey: z.string(),
  paymentIntentId: z.string()
});
export type PaymentIntentResponse = z.infer<typeof PaymentIntentResponseSchema>;

export const PaymentOrderSchema = z.object({
  orderId: z.string(),
  userId: z.string(),
  amountCents: z.number().int().nonnegative(),
  currency: z.string(),
  status: OrderStatusSchema,
  createdAt: z.number()
});
export type PaymentOrder = z.infer<typeof PaymentOrderSchema>;

export const PaymentConfirmResponseSchema = z.object({
  ok: z.literal(true),
  orderId: z.string(),
  paymentStatus: PaymentStatusSchema,
  order: PaymentOrderSchema
});
export type PaymentConfirmResponse = z.infer<typeof PaymentConfirmResponseSchema>;

export const PaymentConfirmErrorSchema = z.object({
  error: z.enum(["ORDER_NOT_FOUND", "PAYMENT_NOT_CONFIRMED", "VALIDATION_ERROR"])
});
export type PaymentConfirmError = z.infer<typeof PaymentConfirmErrorSchema>;
