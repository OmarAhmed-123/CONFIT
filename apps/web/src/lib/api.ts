import { z } from "zod";
import { UserRoleSchema } from "@confit/contracts";

const envSchema = z.object({
  NEXT_PUBLIC_API_ORIGIN: z.string().url().default("http://localhost:3000")
});

export const clientEnv = envSchema.parse({
  NEXT_PUBLIC_API_ORIGIN: process.env.NEXT_PUBLIC_API_ORIGIN
});

export const authErrors = z.enum(["PROVIDER_DENIED", "INVALID_STATE", "TOKEN_FAILED", "SESSION_EXPIRED", "PROVIDER_UNAVAILABLE"]);
export type AuthError = z.infer<typeof authErrors>;

export const userSchema = z.object({
  userId: z.string(),
  createdAt: z.number(),
  primaryEmail: z.string().optional(),
  name: z.string().optional(),
  pictureUrl: z.string().optional(),
  trustLevel: z.enum(["new", "trusted"]),
  role: UserRoleSchema
});

export type User = z.infer<typeof userSchema>;

export async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${clientEnv.NEXT_PUBLIC_API_ORIGIN}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.headers ?? {})
    }
  });
  return res;
}

export async function getMe(): Promise<User> {
  const res = await apiFetch("/me", { method: "GET" });
  if (!res.ok) throw new Error("SESSION_EXPIRED");
  const json = await res.json();
  return userSchema.parse(json.user);
}

export async function refresh(): Promise<void> {
  const csrf = getCookie("csrf_token");
  const res = await apiFetch("/auth/refresh", {
    method: "POST",
    headers: csrf ? { "x-csrf-token": csrf } : undefined
  });
  if (!res.ok) throw new Error("SESSION_EXPIRED");
}

export async function logout(): Promise<void> {
  const csrf = getCookie("csrf_token");
  await apiFetch("/logout", {
    method: "POST",
    headers: csrf ? { "x-csrf-token": csrf } : undefined
  });
}

function getCookie(name: string) {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${name.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, "\\$&")}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

