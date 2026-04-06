/**
 * Virtual try-on client limits.
 * Align with backend TRYON_REQUEST_TIMEOUT_SEC; classical CPU work can take minutes without GPU.
 */
import { getTryOnPreviewTimeoutMs as readPreviewMs, getTryOnTimeoutMs as readFetchMs } from '@/lib/env';

/** Must be ≥ server TRYON_REQUEST_TIMEOUT_SEC (default 300s) so the browser does not abort first. */
export const TRYON_FETCH_TIMEOUT_MS = 330_000;
export const TRYON_PREVIEW_TIMEOUT_MS = 15_000;

export function getTryOnFetchTimeoutMs(): number {
  return readFetchMs();
}

export function getTryOnPreviewTimeoutMs(): number {
  return readPreviewMs();
}
