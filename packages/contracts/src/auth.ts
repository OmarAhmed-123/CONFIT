import { z } from "zod";

export const OAuthProviderSchema = z.enum(["google", "facebook", "instagram", "x", "tiktok"]);
export type OAuthProvider = z.infer<typeof OAuthProviderSchema>;

export const UserRoleSchema = z.enum(["user", "admin", "super_admin"]);
export type UserRole = z.infer<typeof UserRoleSchema>;

export const SessionSummarySchema = z.object({
  sessionId: z.string(),
  userId: z.string(),
  role: UserRoleSchema,
  createdAt: z.number(),
  lastSeenAt: z.number(),
  ip: z.string().optional(),
  userAgent: z.string().optional(),
  deviceFingerprint: z.string().optional(),
  isCurrent: z.boolean().optional()
});
export type SessionSummary = z.infer<typeof SessionSummarySchema>;

export const MeResponseSchema = z.object({
  user: z.object({
    userId: z.string(),
    createdAt: z.number(),
    primaryEmail: z.string().optional(),
    name: z.string().optional(),
    pictureUrl: z.string().optional(),
    trustLevel: z.enum(["new", "trusted"]),
    role: UserRoleSchema
  })
});
export type MeResponse = z.infer<typeof MeResponseSchema>;

export const AuthErrorSchema = z.enum([
  "PROVIDER_DENIED",
  "INVALID_STATE",
  "TOKEN_FAILED",
  "SESSION_EXPIRED",
  "PROVIDER_UNAVAILABLE",
  "UNAUTHORIZED",
  "FORBIDDEN"
]);
