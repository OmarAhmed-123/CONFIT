import type { UserRole } from "@confit/contracts";
import { nanoid } from "nanoid";
import type { AnyRedis } from "../../infra/redis.js";
import type { NormalizedProfile } from "./types.js";

export type User = {
  userId: string;
  createdAt: number;
  primaryEmail?: string;
  name?: string;
  pictureUrl?: string;
  trustLevel: "new" | "trusted";
  role: UserRole;
};

function userKey(userId: string) {
  return `auth:user:${userId}`;
}

function accountKey(provider: string, providerAccountId: string) {
  return `auth:acct:${provider}:${providerAccountId}`;
}

export class AuthService {
  constructor(private redis: AnyRedis) {}

  async upsertUserFromOAuth(profile: NormalizedProfile): Promise<User> {
    const acctK = accountKey(profile.provider, profile.providerAccountId);
    const existingUserId = await this.redis.get(acctK);
    if (existingUserId) {
      const u = await this.getUser(existingUserId);
      if (u) return u;
    }

    const userId = nanoid(16);
    const now = Date.now();
    const user: User = {
      userId,
      createdAt: now,
      primaryEmail: profile.email,
      name: profile.name,
      pictureUrl: profile.pictureUrl,
      trustLevel: "new",
      role: "user"
    };
    await this.redis.set(userKey(userId), JSON.stringify(user));
    await this.redis.set(acctK, userId);
    return user;
  }

  async getUser(userId: string): Promise<User | null> {
    const raw = await this.redis.get(userKey(userId));
    if (!raw) return null;
    return JSON.parse(raw) as User;
  }
}

