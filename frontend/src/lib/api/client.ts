/**
 * CONFIT API Client
 * Central HTTP client for all backend communication
 */

import type { AuthTokens } from '@/types';
import { clearAuthTokenCookie, syncAuthTokenCookie } from '@/lib/auth/cookies';

// In development, use empty string to leverage Next.js rewrites (proxy to backend)
// In production, use the explicit backend URL
const isDev = process.env.NODE_ENV === 'development';
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || (isDev ? 'http://127.0.0.1:8000' : 'http://localhost:8000')).replace(/\/$/, '');

// Token storage keys
const TOKEN_KEY = 'confit_token';
const REFRESH_TOKEN_KEY = 'confit_refresh_token';
const CSRF_TOKEN_KEY = 'confit_csrf_token';

// ===========================================
// Token Management
// ===========================================

export function getCsrfToken(): string | null {
  if (typeof window === 'undefined') return null;
  // Try cookie first (for cookie-based sessions)
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  if (match) return decodeURIComponent(match[1]);
  // Fall back to localStorage (for hybrid flows)
  return localStorage.getItem(CSRF_TOKEN_KEY);
}

export function setCsrfToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(CSRF_TOKEN_KEY, token);
}

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  syncAuthTokenCookie(tokens.access_token);
}

export function clearTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  clearAuthTokenCookie();
}

// ===========================================
// API Error Class
// ===========================================

export class APIError extends Error {
  status: number;
  detail?: string;
  code?: string;

  constructor(status: number, message: string, detail?: string, code?: string) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

// ===========================================
// HTTP Client
// ===========================================

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  params?: Record<string, string | number | boolean | null | undefined>;
  [key: string]: unknown;
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearTokens();
      return false;
    }

    const data = await parseJsonResponse<Record<string, string>>(response);
    setTokens({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      token_type: data.token_type || 'Bearer',
    });
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  const text = await response.text();
  if (!text) return {} as T;
  if (!contentType.includes('application/json')) {
    const snippet = text.trim().slice(0, 120);
    throw new APIError(
      response.status || 0,
      snippet.startsWith('<')
        ? 'Server returned an HTML page instead of JSON'
        : 'Server returned a non-JSON response',
      snippet
    );
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new APIError(response.status || 0, 'Server returned invalid JSON');
  }
}

async function makeRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { skipAuth, params, ...fetchOptions } = options;
  const isAuthEndpoint = endpoint.startsWith('/api/auth/login')
    || endpoint.startsWith('/api/auth/register')
    || endpoint.startsWith('/api/auth/exists')
    || endpoint.startsWith('/api/auth/forgot-password')
    || endpoint.startsWith('/api/auth/reset-password');
  const shouldUseAuth = !skipAuth && !isAuthEndpoint;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Add auth header if not skipped and token exists
  if (shouldUseAuth) {
    const token = getAccessToken();
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }

  // Add CSRF token for cookie-based session flows or state-changing requests
  const csrfToken = getCsrfToken();
  if (csrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(fetchOptions.method || 'GET')) {
    (headers as Record<string, string>)['X-CSRF-Token'] = csrfToken;
  }

  const requestUrl = new URL(`${API_BASE_URL}${endpoint}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        requestUrl.searchParams.set(key, String(value));
      }
    }
  }

  const response = await fetch(requestUrl.toString(), {
    ...fetchOptions,
    headers,
  });

  // Handle 401 - attempt token refresh
  if (response.status === 401 && shouldUseAuth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry with new token
      const newToken = getAccessToken();
      const retryHeaders: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
        Authorization: `Bearer ${newToken}`,
      };
      const retryResponse = await fetch(requestUrl.toString(), {
        ...fetchOptions,
        headers: retryHeaders,
      });
      return handleResponse<T>(retryResponse);
    }
    // Clear invalid tokens and throw
    clearTokens();
    throw new APIError(401, 'Authentication required', 'Session expired');
  }

  return handleResponse<T>(response);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    let detail: string | undefined;
    let code: string | undefined;

    try {
      const errorData = await parseJsonResponse<any>(response);
      const nestedError = errorData.error;
      errorMessage = nestedError?.message
        || errorData.message
        || errorData.detail
        || errorMessage;
      detail = typeof errorData.detail === 'string'
        ? errorData.detail
        : nestedError?.message || errorMessage;
      code = nestedError?.code || errorData.code || errorData.error_code;
    } catch (error) {
      if (error instanceof APIError) {
        errorMessage = error.message;
        detail = error.detail;
      }
    }

    // Handle rate limiting (429) — propagate with retry-after hint if available
    if (response.status === 429) {
      const retryAfter = response.headers.get('retry-after') || response.headers.get('X-RateLimit-Reset');
      throw new APIError(
        429,
        errorMessage,
        retryAfter ? `Retry after ${retryAfter} seconds` : detail,
        'RATE_LIMITED'
      );
    }

    throw new APIError(response.status, errorMessage, detail, code);
  }

  return parseJsonResponse<T>(response);
}

// ===========================================
// Exported API Methods
// ===========================================

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    makeRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    makeRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    makeRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  patch: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    makeRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    makeRequest<T>(endpoint, { ...options, method: 'DELETE' }),

  // File upload helper
  upload: async <T>(
    endpoint: string,
    file: File,
    fieldName: string = 'file',
    additionalData?: Record<string, string>
  ): Promise<T> => {
    const formData = new FormData();
    formData.append(fieldName, file);
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const token = getAccessToken();
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    return handleResponse<T>(response);
  },
};

export { API_BASE_URL };
