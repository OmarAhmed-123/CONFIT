import { resolveImageUrl } from '@/lib/imageUrl';

const INLINE_PLACEHOLDER =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">' +
      '<rect width="600" height="800" fill="#f3f4f6"/>' +
      '<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#9ca3af" font-size="28" font-family="Arial, sans-serif">Image unavailable</text>' +
    '</svg>'
  );

export function safeImageSrc(value: unknown): string {
  const resolved = resolveImageUrl(value);
  return resolved || INLINE_PLACEHOLDER;
}

