/**
 * CONFIT API Utilities
 * =====================
 * Legacy exports for backwards compatibility.
 *
 * For new code, import from '@/lib/api/client' or '@/lib/api' instead.
 */

import { getAuthToken } from '@/lib/auth';
import { getPublicApiBaseUrl, isDev } from '@/lib/env';

// Re-export from unified API client
export { api, APIError } from './api/client';
export { API_ENDPOINTS } from './api/endpoints';

// Use the FastAPI backend directly so backend access logs show every API request.
const BACKEND_URL = getPublicApiBaseUrl();
const EXPLICIT_BACKEND_URL = getPublicApiBaseUrl();
const NEXTAUTH_RESERVED_ACTIONS = new Set([
  'callback',
  'csrf',
  'error',
  'providers',
  'session',
  'signin',
  'signout',
  'verify-request',
]);

function shouldUseExplicitBackend(path: string): boolean {
  if (!EXPLICIT_BACKEND_URL) {
    return false;
  }

  if (!path.startsWith('/api/auth/')) {
    return true;
  }

  const authAction = path.slice('/api/auth/'.length).split('/')[0];
  return !NEXTAUTH_RESERVED_ACTIONS.has(authAction);
}

export function getBackendUrl(): string {
  return BACKEND_URL || window.location.origin;
}

/**
 * Build API URL with proper handling.
 * FastAPI routes are defined without trailing slashes, so we don't add them.
 * @deprecated Use api.get/post/etc from '@/lib/api/client' instead
 */
export function apiUrl(path: string): string {
  // Ensure path starts with /
  let p = path.startsWith('/') ? path : `/${path}`;
  
  // Remove trailing slash if present (except for root path)
  if (p !== '/' && p.endsWith('/')) {
    p = p.slice(0, -1);
  }

  const base = shouldUseExplicitBackend(p) ? EXPLICIT_BACKEND_URL : BACKEND_URL.replace(/\/$/, '');
  
  return `${base}${p}`;
}

export interface ApiOptions extends RequestInit {
  token?: string | null;
}

/**
 * Authenticated fetch. Adds Authorization header when token is provided.
 * @deprecated Use api.get/post/etc from '@/lib/api/client' instead
 */
export async function apiFetch(path: string, options: ApiOptions = {}): Promise<Response> {
  const { token, ...init } = options;
  const url = apiUrl(path);
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && (init.body && typeof init.body === 'string')) {
    headers.set('Content-Type', 'application/json');
  }
  const authToken = token ?? getAuthToken();
  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }
  return fetch(url, { ...init, headers });
}

export { getAuthToken } from '@/lib/auth';

/**
 * Fetch JSON with optional auth. Throws on non-ok response with parsed detail when possible.
 * @deprecated Use api.get/post/etc from '@/lib/api/client' instead
 */
export async function apiJson<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = options.token !== undefined ? options.token : getAuthToken();
  const res = await apiFetch(path, { ...options, token });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : data?.detail?.msg ?? `Request failed: ${res.status}`;
    throw new Error(detail);
  }
  return data as T;
}
