import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { UserProfile } from '@/types';
import { api, APIError } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import {
  clearAuthCredentials,
  getAuthToken,
  getRefreshToken as getStoredRefreshToken,
  getStoredUser,
  setAuthCredentials,
  setRefreshToken,
} from '@/lib/auth';
import { normalizeRoles } from '@/lib/auth/roles';

// Backend response types
interface AuthResponsePayload {
  success?: boolean;
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  user?: UserDTO;
  message?: string;
  dev_reset_link?: string;
}

interface UserDTO {
  id?: string;
  userId?: string;
  email?: string;
  primaryEmail?: string;
  name?: string;
  display_name?: string;
  avatar_url?: string;
  pictureUrl?: string;
  roles?: string[];
  email_verified: boolean;
  phone_verified: boolean;
  is_verified: boolean;
  created_at?: string;
  createdAt?: number | string;
}

// Define the shape of the context
interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<{ error?: string; user?: UserProfile }>;
  signUp: (email: string, password: string, fullName: string) => Promise<{ error?: string; needsLogin?: boolean }>;
  signOut: () => Promise<void>;
  updateProfile: (data: Partial<UserProfile>) => Promise<{ error?: string }>;
  refreshUser: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error?: string; resetLink?: string }>;
  confirmPasswordReset: (token: string, newPassword: string) => Promise<{ error?: string; user?: UserProfile }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Convert backend UserDTO to frontend UserProfile
function toUserProfile(dto: UserDTO): UserProfile {
  const nowIso = new Date().toISOString();
  const userId = dto.id ?? dto.userId ?? '';
  if (!userId) console.error('Auth: received user without ID from backend');
  const createdIso = dto.created_at
    ?? (typeof dto.createdAt === 'number'
      ? new Date(dto.createdAt).toISOString()
      : typeof dto.createdAt === 'string'
        ? dto.createdAt
        : nowIso);
  const email = dto.email ?? dto.primaryEmail ?? '';
  const name = dto.name ?? dto.display_name ?? email.split('@')[0] ?? 'User';
  const avatarUrl = dto.avatar_url ?? dto.pictureUrl;
  return {
    id: userId,
    email,
    name,
    avatar: avatarUrl,
    avatar_url: avatarUrl,
    createdAt: new Date(createdIso),
    created_at: createdIso,
    updatedAt: new Date(createdIso),
    updated_at: createdIso,
    roles: normalizeRoles(dto.roles),
  };
}

// In development, use empty string to leverage Next.js rewrites (proxy to backend)
// In production, use the explicit backend URL
const isDev = process.env.NODE_ENV === 'development';
const AUTH_ORIGIN = (
  process.env.NEXT_PUBLIC_AUTH_ORIGIN ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (isDev ? 'http://127.0.0.1:8000' : 'http://localhost:8000')
).replace(/\/$/, '');

// Timeout wrapper for fetch to prevent hanging
function fetchWithTimeout(url: string, options: RequestInit & { timeout?: number } = {}): Promise<Response> {
  const { timeout = 5000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  return fetch(url, {
    ...fetchOptions,
    signal: controller.signal,
  }).finally(() => clearTimeout(timeoutId));
}

async function authFetch(path: string, init?: RequestInit & { timeout?: number }): Promise<Response> {
  const token = typeof window !== 'undefined' ? getAuthToken() : null;
  // Use relative URL in dev (via Next.js rewrites), absolute URL in production
  const url = `${AUTH_ORIGIN}/api${path}`;
  return fetchWithTimeout(url, {
    ...init,
    timeout: init?.timeout ?? 5000,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof APIError) {
    return error.detail || error.message || fallback;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

function getAccessTokenFromPayload(payload: AuthResponsePayload): string {
  return payload.access_token || '';
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(() => {
    // Hydrate immediately from cache to avoid blocking render
    if (typeof window !== 'undefined') {
      return getStoredUser<UserProfile>() ?? null;
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState(() => {
    // Only show loading if we have a token that needs validation
    if (typeof window !== 'undefined') {
      return !!getAuthToken() || !!getStoredUser<UserProfile>();
    }
    return false;
  });

  const hydrateSession = useCallback(async (payload: AuthResponsePayload): Promise<UserProfile> => {
    const accessToken = getAccessTokenFromPayload(payload);
    if (!accessToken) {
      throw new Error(payload.message || 'Authentication response did not include an access token.');
    }

    if (payload.refresh_token) {
      setRefreshToken(payload.refresh_token);
    }

    if (payload.user) {
      const profile = toUserProfile(payload.user);
      setAuthCredentials(accessToken, profile);
      setUser(profile);
      return profile;
    }

    setAuthCredentials(accessToken, null);
    const meRes = await authFetch('/auth/me', { method: 'GET' });
    if (!meRes.ok) {
      clearAuthCredentials();
      throw new Error('Signed in, but failed to load your profile.');
    }

    const meJson = (await meRes.json()) as AuthResponsePayload;
    if (!meJson.user) {
      clearAuthCredentials();
      throw new Error('Signed in, but the profile response was incomplete.');
    }

    const profile = toUserProfile(meJson.user);
    setAuthCredentials(accessToken, profile);
    setUser(profile);
    return profile;
  }, []);

  // Validate session with auth authority on startup — NON-BLOCKING
  // Strategy: show cached user immediately, validate silently in background
  useEffect(() => {
    const controller = new AbortController();
    let isMounted = true;

    (async () => {
      const token = getAuthToken();
      if (!token) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        // Fast validation: 1.5s timeout (was 3s) — don't block UI
        const meRes = await authFetch('/auth/me', { method: 'GET', signal: controller.signal, timeout: 1500 });

        if (meRes.ok) {
          const meJson = (await meRes.json()) as AuthResponsePayload;
          if (meJson.user && isMounted) {
            const profile = toUserProfile(meJson.user);
            setUser(profile);
            setAuthCredentials(token, profile);
          }
          if (isMounted) setIsLoading(false);
          return;
        }

        // Fast token refresh: 1.5s timeout
        const refreshToken = getStoredRefreshToken();
        if (!refreshToken) {
          if (isMounted) {
            setUser(null);
            clearAuthCredentials();
            setIsLoading(false);
          }
          return;
        }

        const refreshRes = await authFetch('/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
          signal: controller.signal,
          timeout: 1500,
        });

        if (!refreshRes.ok) {
          if (isMounted) {
            setUser(null);
            clearAuthCredentials();
            setIsLoading(false);
          }
          return;
        }

        const refreshJson = (await refreshRes.json()) as AuthResponsePayload;
        if (refreshJson.access_token && isMounted) {
          setAuthCredentials(refreshJson.access_token, getStoredUser<UserProfile>());
        }
        if (refreshJson.refresh_token) {
          setRefreshToken(refreshJson.refresh_token);
        }

        const meAfterRefreshRes = await authFetch('/auth/me', { method: 'GET', signal: controller.signal, timeout: 1500 });
        if (!meAfterRefreshRes.ok) {
          if (isMounted) {
            setUser(null);
            clearAuthCredentials();
            setIsLoading(false);
          }
          return;
        }

        const meAfterRefreshJson = (await meAfterRefreshRes.json()) as AuthResponsePayload;
        if (meAfterRefreshJson.user && isMounted) {
          const profile = toUserProfile(meAfterRefreshJson.user);
          setUser(profile);
          const refreshedAccessToken = refreshJson.access_token || token;
          if (refreshedAccessToken) {
            setAuthCredentials(refreshedAccessToken, profile);
          }
        }
      } catch (error) {
        // Backend unavailable or timeout — keep cached user, fail gracefully
        console.warn('Auth validation deferred (backend may be unavailable):', error);
        // Don't clear user if we have one cached — improves perceived performance
        const storedUser = getStoredUser<UserProfile>();
        if (!storedUser && isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    })();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const meRes = await authFetch('/auth/me', { method: 'GET' });
      if (!meRes.ok) return;
      const meJson = (await meRes.json()) as AuthResponsePayload;
      if (!meJson.user) return;
      const profile = toUserProfile(meJson.user);
      setUser(profile);
      const token = getAuthToken();
      if (token) {
        setAuthCredentials(token, profile);
      }
    } catch (error) {
      console.warn('Failed to refresh user data', error);
    }
  }, []);

  const signIn = async (email: string, password: string): Promise<{ error?: string; user?: UserProfile }> => {
    try {
      clearAuthCredentials();
      const response = await api.post<AuthResponsePayload>(API_ENDPOINTS.AUTH.LOGIN, {
        email,
        password,
      }, { skipAuth: true });
      const profile = await hydrateSession(response);

      return { user: profile };
    } catch (error) {
      console.error('Auth signIn failed:', error);
      return { error: getErrorMessage(error, 'Unable to sign in right now.') };
    }
  };

  const signUp = async (
    email: string,
    password: string,
    fullName: string
  ): Promise<{ error?: string; needsLogin?: boolean; user?: UserProfile }> => {
    try {
      const response = await api.post<AuthResponsePayload>(API_ENDPOINTS.AUTH.REGISTER, {
        email,
        password,
        name: fullName,
      }, { skipAuth: true });

      // Backend now returns tokens for auto-login
      if (response.access_token) {
        const profile = await hydrateSession(response);
        return { user: profile };
      }

      // Fallback: registration successful but needs manual login
      return { needsLogin: true };
    } catch (error) {
      console.error('Auth signUp failed:', error);
      return { error: getErrorMessage(error, 'Unable to create your account right now.') };
    }
  };

  const signOut = async () => {
    try {
      await authFetch('/auth/logout', { method: 'POST' });
    } catch (err) {
      console.warn('Logout API call failed:', err);
    }

    // Clear legacy local storage keys, then clear in-memory state.
    clearAuthCredentials();
    setUser(null);
  };

  const updateProfile = async (data: Partial<UserProfile>): Promise<{ error?: string }> => {
    try {
      const userData = await api.patch<UserDTO>(API_ENDPOINTS.PROFILE.UPDATE, data);
      const profile = toUserProfile(userData);
      const token = getAuthToken();
      if (token) {
        setAuthCredentials(token, profile);
      }
      setUser(profile);
      return {};
    } catch (error) {
      return { error: getErrorMessage(error, 'Unable to update your profile right now.') };
    }
  };

  const resetPassword = async (email: string): Promise<{ error?: string; resetLink?: string }> => {
    try {
      const response = await api.post<AuthResponsePayload>(
        API_ENDPOINTS.AUTH.FORGOT_PASSWORD,
        { email },
        { skipAuth: true }
      );
      return { resetLink: response.dev_reset_link };
    } catch (error) {
      return { error: getErrorMessage(error, 'Unable to request a password reset right now.') };
    }
  };

  const confirmPasswordReset = async (
    token: string,
    newPassword: string
  ): Promise<{ error?: string; user?: UserProfile }> => {
    try {
      clearAuthCredentials();
      const response = await api.post<AuthResponsePayload>(API_ENDPOINTS.AUTH.RESET_PASSWORD, {
        token,
        new_password: newPassword,
      }, { skipAuth: true });
      const profile = await hydrateSession(response);
      return { user: profile };
    } catch (error) {
      return { error: getErrorMessage(error, 'Unable to reset your password right now.') };
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        signIn,
        signUp,
        signOut,
        updateProfile,
        refreshUser,
        resetPassword,
        confirmPasswordReset,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
