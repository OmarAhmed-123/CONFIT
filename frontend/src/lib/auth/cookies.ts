const COOKIE_NAME = 'confit_token';
const DEFAULT_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

export function syncAuthTokenCookie(
  token: string,
  options?: { maxAgeSeconds?: number }
): void {
  if (typeof document === 'undefined') return;

  const maxAge = options?.maxAgeSeconds ?? DEFAULT_MAX_AGE_SECONDS;
  document.cookie = [
    `${COOKIE_NAME}=${encodeURIComponent(token)}`,
    'Path=/',
    `Max-Age=${maxAge}`,
    'SameSite=Lax',
  ].join('; ');
}

export function clearAuthTokenCookie(): void {
  if (typeof document === 'undefined') return;

  document.cookie = [
    `${COOKIE_NAME}=`,
    'Path=/',
    'Max-Age=0',
    'SameSite=Lax',
  ].join('; ');
}
