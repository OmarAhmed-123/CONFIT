import { getPublicApiBaseUrl, isDev } from '@/lib/env';

function backendOrigin(): string {
  if (isDev) {
    return getPublicApiBaseUrl();
  }
  return typeof window !== 'undefined' ? window.location.origin : getPublicApiBaseUrl();
}

export function resolveImageUrl(value: unknown): string {
  const raw = String(value ?? '').trim();
  if (!raw) return '';
  if (raw.startsWith('data:') || raw.startsWith('blob:')) return raw;
  if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
  if (raw.startsWith('/')) return `${backendOrigin()}${raw}`;
  return `${backendOrigin()}/${raw}`;
}

