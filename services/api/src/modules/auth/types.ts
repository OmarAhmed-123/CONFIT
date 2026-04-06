import type { OAuthProvider, UserRole } from "@confit/contracts";

export type OAuthProviderId = OAuthProvider;

export type NormalizedProfile = {
  provider: OAuthProviderId;
  providerAccountId: string;
  email?: string;
  emailVerified?: boolean;
  name?: string;
  pictureUrl?: string;
};

export type Session = {
  sessionId: string;
  userId: string;
  role: UserRole;
  familyId: string;
  createdAt: number;
  lastSeenAt: number;
  refreshTokenHash: string;
  refreshTokenRotations: number;
  revokedAt?: number;
  ip?: string;
  userAgent?: string;
  deviceFingerprint?: string;
};

