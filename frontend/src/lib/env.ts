/**
 * Centralized public env access for Next.js (replaces Vite `import.meta.env`).
 * Only `NEXT_PUBLIC_*` variables are available in the browser bundle.
 */

export const isDev = process.env.NODE_ENV === 'development';

export function getPublicApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
}

/** OAuth / auth authority (falls back to app origin in dev). */
export function getPublicAuthOrigin(): string {
  return (
    process.env.NEXT_PUBLIC_AUTH_ORIGIN ||
    process.env.NEXT_PUBLIC_APP_URL ||
    (typeof window !== 'undefined' ? window.location.origin : '') ||
    'http://localhost:3000'
  ).replace(/\/$/, '');
}

export function getTryOnPollMs(): number {
  const n = Number(process.env.NEXT_PUBLIC_TRYON_RENDER_POLL_MS);
  return Number.isFinite(n) && n > 0 ? n : 1500;
}

export function getTryOnMaxWaitMs(): number {
  const n = Number(process.env.NEXT_PUBLIC_TRYON_RENDER_MAX_WAIT_MS);
  return Number.isFinite(n) && n > 0 ? n : 180_000;
}

export function isTryOnLocalHistoryEnabled(): boolean {
  return process.env.NEXT_PUBLIC_TRYON_LOCAL_HISTORY !== 'false';
}

export function getTryOnTimeoutMs(): number {
  const n = Number(process.env.NEXT_PUBLIC_TRYON_TIMEOUT_MS);
  return Number.isFinite(n) && n >= 30_000 ? n : 330_000;
}

export function getTryOnPreviewTimeoutMs(): number {
  const n = Number(process.env.NEXT_PUBLIC_TRYON_PREVIEW_TIMEOUT_MS);
  return Number.isFinite(n) && n >= 3_000 ? n : 15_000;
}
