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
  token?: string;
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  user?: UserDTO;
  message?: string;
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
  resetPassword: (email: string) => Promise<{ error?: string }>;
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
const AUTH_ORIGIN = isDev ? '' : (
  process.env.NEXT_PUBLIC_AUTH_ORIGIN ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8001'
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
  return payload.access_token || payload.token || '';
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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

  // Validate session with auth authority on startup
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        // First, try to restore user from localStorage if available (faster)
        const storedUser = getStoredUser<UserProfile>();
        const token = getAuthToken();
        if (storedUser && token) {
          setUser(storedUser);
        }

        // Then verify with backend
        const meRes = await authFetch('/auth/me', { method: 'GET', signal: controller.signal, timeout: 3000 });
        if (meRes.ok) {
          const meJson = (await meRes.json()) as AuthResponsePayload;
          if (!meJson.user) {
            throw new Error('Profile validation returned an incomplete payload.');
          }
          const profile = toUserProfile(meJson.user);
          setUser(profile);
          if (token) {
            setAuthCredentials(token, profile);
          }
          return;
        }

        // If /auth/me fails but we have stored user, keep the stored user (it's recent)
        if (storedUser && token) {
          console.warn('Backend /auth/me validation failed but restoring from cache');
          return;
        }

        // Try token refresh
        const refreshToken = getStoredRefreshToken();
        if (!refreshToken) {
          setUser(null);
          return;
        }

        const refreshRes = await authFetch('/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
          signal: controller.signal,
          timeout: 3000,
        });

        if (!refreshRes.ok) {
          setUser(null);
          return;
        }

        const refreshJson = (await refreshRes.json()) as AuthResponsePayload;
        if (refreshJson.access_token) {
          setAuthCredentials(refreshJson.access_token, storedUser);
        }
        if (refreshJson.refresh_token) {
          setRefreshToken(refreshJson.refresh_token);
        }

        const meAfterRefreshRes = await authFetch('/auth/me', { method: 'GET', signal: controller.signal, timeout: 3000 });
        if (!meAfterRefreshRes.ok) {
          setUser(null);
          return;
        }

        const meAfterRefreshJson = (await meAfterRefreshRes.json()) as AuthResponsePayload;
        if (!meAfterRefreshJson.user) {
          throw new Error('Profile refresh returned an incomplete payload.');
        }
        const profile = toUserProfile(meAfterRefreshJson.user);
        setUser(profile);
        const refreshedAccessToken = refreshJson.access_token || token;
        if (refreshedAccessToken) {
          setAuthCredentials(refreshedAccessToken, profile);
        }
      } catch (error) {
        // Backend unavailable or timeout - fail gracefully without blocking the app
        console.warn('Auth initialization failed (backend may be unavailable):', error);
        // Don't clear user if we have one cached
        const storedUser = getStoredUser<UserProfile>();
        if (!storedUser) {
          setUser(null);
        }
      } finally {
        setIsLoading(false);
      }
    })();
    return () => controller.abort();
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
      const response = await api.post<AuthResponsePayload>(API_ENDPOINTS.AUTH.LOGIN, {
        email,
        password,
      });
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
      });

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

  const resetPassword = async (email: string): Promise<{ error?: string }> => {
    try {
      await api.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD, { email });
      return {};
    } catch (error) {
      return { error: getErrorMessage(error, 'Unable to request a password reset right now.') };
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
