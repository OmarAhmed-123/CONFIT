import argon2 from "argon2";
import { nanoid } from "nanoid";
import type { AnyRedis } from "../../infra/redis.js";
import type { Session } from "./types.js";
import type { UserRole } from "@confit/contracts";

const SESSION_TTL_SECONDS = 60 * 60 * 24 * 30; // 30d

function sessionKey(sessionId: string) {
  return `auth:sess:${sessionId}`;
}

function userSessionsKey(userId: string) {
  return `auth:user_sessions:${userId}`;
}

export class SessionService {
  constructor(private redis: AnyRedis) {}

  async createSession(input: {
    userId: string;
    role: UserRole;
    refreshToken: string;
    ip?: string;
    userAgent?: string;
    deviceFingerprint?: string;
  }): Promise<Session> {
    const sessionId = nanoid(24);
    const familyId = nanoid(24);
    const now = Date.now();
    const refreshTokenHash = await argon2.hash(input.refreshToken);
    const sess: Session = {
      sessionId,
      userId: input.userId,
      role: input.role,
      familyId,
      createdAt: now,
      lastSeenAt: now,
      refreshTokenHash,
      refreshTokenRotations: 0,
      ip: input.ip,
      userAgent: input.userAgent,
      deviceFingerprint: input.deviceFingerprint
    };

    await this.redis.set(sessionKey(sessionId), JSON.stringify(sess), "EX", SESSION_TTL_SECONDS);
    await this.redis.sadd(userSessionsKey(input.userId), sessionId);
    await this.redis.expire(userSessionsKey(input.userId), SESSION_TTL_SECONDS);
    return sess;
  }

  async getSession(sessionId: string): Promise<Session | null> {
    const raw = await this.redis.get(sessionKey(sessionId));
    if (!raw) return null;
    return JSON.parse(raw) as Session;
  }

  async touchSession(sessionId: string): Promise<void> {
    const sess = await this.getSession(sessionId);
    if (!sess || sess.revokedAt) return;
    sess.lastSeenAt = Date.now();
    await this.redis.set(sessionKey(sessionId), JSON.stringify(sess), "EX", SESSION_TTL_SECONDS);
  }

  async revokeSession(sessionId: string, reason?: string): Promise<void> {
    const sess = await this.getSession(sessionId);
    if (!sess) return;
    sess.revokedAt = Date.now();
    await this.redis.set(sessionKey(sessionId), JSON.stringify(sess), "EX", SESSION_TTL_SECONDS);
    await this.redis.srem(userSessionsKey(sess.userId), sessionId);
    if (reason) {
      await this.redis.lpush(`auth:revoked:${sessionId}`, `${new Date().toISOString()} ${reason}`);
      await this.redis.ltrim(`auth:revoked:${sessionId}`, 0, 50);
      await this.redis.expire(`auth:revoked:${sessionId}`, SESSION_TTL_SECONDS);
    }
  }

  async rotateRefreshToken(sessionId: string, presentedToken: string): Promise<{ newRefreshToken: string; session: Session }> {
    const sess = await this.getSession(sessionId);
    if (!sess) throw new Error("SESSION_NOT_FOUND");
    if (sess.revokedAt) throw new Error("SESSION_REVOKED");

    const ok = await argon2.verify(sess.refreshTokenHash, presentedToken);
    if (!ok) {
      await this.revokeSession(sessionId, "refresh_token_reuse_or_mismatch");
      await this.revokeSessionFamily(sess.userId, sess.familyId, "session_family_revoked_reuse_detected");
      throw new Error("REFRESH_REUSE_DETECTED");
    }

    const newRefreshToken = nanoid(48);
    sess.refreshTokenHash = await argon2.hash(newRefreshToken);
    sess.refreshTokenRotations += 1;
    sess.lastSeenAt = Date.now();
    await this.redis.set(sessionKey(sessionId), JSON.stringify(sess), "EX", SESSION_TTL_SECONDS);
    return { newRefreshToken, session: sess };
  }

  async listUserSessions(userId: string): Promise<Session[]> {
    const sessionIds = await this.redis.smembers(userSessionsKey(userId));
    if (!sessionIds.length) return [];
    const sessions = await Promise.all(sessionIds.map((sessionId) => this.getSession(sessionId)));
    return sessions.filter((session): session is Session => Boolean(session && !session.revokedAt));
  }

  async revokeAllUserSessions(userId: string, reason?: string): Promise<void> {
    const sessions = await this.listUserSessions(userId);
    await Promise.all(sessions.map((session) => this.revokeSession(session.sessionId, reason ?? "logout_all")));
  }

  async revokeSessionFamily(userId: string, familyId: string, reason?: string): Promise<void> {
    const sessions = await this.listUserSessions(userId);
    const familySessions = sessions.filter((session) => session.familyId === familyId);
    await Promise.all(familySessions.map((session) => this.revokeSession(session.sessionId, reason ?? "family_revoked")));
  }
}

