/**
 * CONFIT — Auth Utility
 * Centralised token access helpers shared across all modules.
 * Mirrors the same localStorage keys used by AuthContext.
 */

import { clearAuthTokenCookie, syncAuthTokenCookie } from '@/lib/auth/cookies';

const TOKEN_KEY = 'confit_token';
const USER_KEY = 'confit_user';
const REFRESH_TOKEN_KEY = 'confit_refresh_token';

/**
 * Retrieve the current JWT token from storage, or null if not signed in.
 */
export function getAuthToken(): string | null {
    try {
        return localStorage.getItem(TOKEN_KEY);
    } catch {
        return null;
    }
}

/**
 * Retrieve the stored user object from storage, or null if not found.
 */
export function getStoredUser<T = Record<string, unknown>>(): T | null {
    try {
        const raw = localStorage.getItem(USER_KEY);
        return raw ? (JSON.parse(raw) as T) : null;
    } catch {
        return null;
    }
}

/**
 * Persist authentication credentials to storage.
 */
export function setAuthCredentials(token: string, user: unknown): void {
    try {
        localStorage.setItem(TOKEN_KEY, token);
        syncAuthTokenCookie(token);
        if (user != null) {
            localStorage.setItem(USER_KEY, JSON.stringify(user));
        }
    } catch {
        // Storage may be unavailable in private-browsing mode.
    }
}

export function setAccessToken(token: string): void {
    try {
        localStorage.setItem(TOKEN_KEY, token);
        syncAuthTokenCookie(token);
    } catch {}
}

/**
 * Clear all auth credentials from storage (sign-out helper).
 */
export function clearAuthCredentials(): void {
    try {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        clearAuthTokenCookie();
    } catch {
        // Ignore storage errors during sign-out.
    }
}

export function getRefreshToken(): string | null {
    try {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
    } catch {
        return null;
    }
}

export function setRefreshToken(token: string): void {
    try {
        localStorage.setItem(REFRESH_TOKEN_KEY, token);
    } catch {}
}

/**
 * Build a standard Authorization header object when a token is present.
 * Returns an empty object when the user is not authenticated.
 */
export function bearerHeader(token?: string | null): Record<string, string> {
    const t = token ?? getAuthToken();
    return t ? { Authorization: `Bearer ${t}` } : {};
}
