/**
 * CONFIT Authentication Service
 * Handles all authentication-related API calls
 */

import { api, setTokens, clearTokens, getAccessToken } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import type { User, AuthTokens } from '@/types';

// ===========================================
// Types
// ===========================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  phone?: string;
  address?: Record<string, unknown>;
  style_preference?: string;
  body_profile?: Record<string, unknown>;
  budget_range?: Record<string, unknown>;
  preferred_brands?: string[];
  occasion_preferences?: string[];
  marketing_consent?: boolean;
  data_sharing_consent?: boolean;
}

export interface OAuthCallbackRequest {
  provider: 'google' | 'apple';
  id_token?: string;
  access_token?: string;
  code?: string;
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  access_token?: string;
  refresh_token?: string;
  user?: User;
  message: string;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ===========================================
// Auth Service
// ===========================================

export const authService = {
  /**
   * Login with email and password
   */
  async login(email: string, password: string): Promise<{ user: User; tokens: AuthTokens }> {
    const response = await api.post<AuthResponse>(API_ENDPOINTS.AUTH.LOGIN, { email, password });
    
    if (!response.success || !response.user) {
      throw new Error(response.message || 'Login failed');
    }

    const tokens: AuthTokens = {
      access_token: response.access_token || response.token || '',
      refresh_token: response.refresh_token || '',
      token_type: 'Bearer',
    };

    setTokens(tokens);
    return { user: response.user, tokens };
  },

  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<{ user: User; tokens: AuthTokens }> {
    const response = await api.post<AuthResponse>(API_ENDPOINTS.AUTH.REGISTER, data);
    
    if (!response.success || !response.user) {
      throw new Error(response.message || 'Registration failed');
    }

    const tokens: AuthTokens = {
      access_token: response.access_token || response.token || '',
      refresh_token: response.refresh_token || '',
      token_type: 'Bearer',
    };

    setTokens(tokens);
    return { user: response.user, tokens };
  },

  /**
   * OAuth callback - exchange OAuth tokens with backend
   */
  async oauthCallback(data: OAuthCallbackRequest): Promise<{ user: User; tokens: AuthTokens }> {
    const response = await api.post<AuthResponse>(API_ENDPOINTS.AUTH.OAUTH_CALLBACK, data);
    
    if (!response.success || !response.user) {
      throw new Error(response.message || 'OAuth authentication failed');
    }

    const tokens: AuthTokens = {
      access_token: response.access_token || response.token || '',
      refresh_token: response.refresh_token || '',
      token_type: 'Bearer',
    };

    setTokens(tokens);
    return { user: response.user, tokens };
  },

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User | null> {
    try {
      const response = await api.get<AuthResponse>(API_ENDPOINTS.AUTH.ME);
      return response.user || null;
    } catch {
      return null;
    }
  },

  /**
   * Update user profile
   */
  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await api.patch<AuthResponse>(API_ENDPOINTS.AUTH.UPDATE_PROFILE, data);
    
    if (!response.success || !response.user) {
      throw new Error(response.message || 'Profile update failed');
    }

    return response.user;
  },

  /**
   * Logout - clear local tokens
   */
  async logout(): Promise<void> {
    try {
      await api.post(API_ENDPOINTS.AUTH.LOGOUT);
    } catch {
      // Ignore logout API errors
    } finally {
      clearTokens();
    }
  },

  /**
   * Check if email is already registered
   */
  async emailExists(email: string): Promise<boolean> {
    try {
      const response = await api.get<{ exists: boolean }>(
        `${API_ENDPOINTS.AUTH.EXISTS}?email=${encodeURIComponent(email)}`
      );
      return response.exists;
    } catch {
      return false;
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!getAccessToken();
  },
};
