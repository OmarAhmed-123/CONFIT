/**
 * Canonical product image URLs — never rely on a single broken CDN field.
 * Used by try-on grids where Unsplash fallbacks must match backend catalog.
 */
import { resolveImageUrl } from '@/lib/imageUrl';
import type { Product } from '@/types';

export const CATEGORY_IMAGE_FALLBACK: Record<string, string> = {
  tops: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop&q=80',
  bottoms: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop&q=80',
  dresses: 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop&q=80',
  outerwear: 'https://images.unsplash.com/photo-1544923246-77307dd628b8?w=400&h=500&fit=crop&q=80',
  shoes: 'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop&q=80',
  accessories: 'https://images.unsplash.com/photo-1611923134239-b9be5816f80d?w=400&h=500&fit=crop&q=80',
  bags: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&h=500&fit=crop&q=80',
};

function isLikelyValidHttpUrl(s: string): boolean {
  const t = s.trim();
  return t.startsWith('http://') || t.startsWith('https://');
}

/**
 * Returns a non-empty image URL for thumbnails.
 * Prefer absolute https URLs; avoid empty strings that trigger placeholder SVG.
 */
export function getPrimaryProductImageUrl(product: Product): string {
  const list = Array.isArray(product.images) ? product.images : [];
  for (const raw of list) {
    if (raw == null || String(raw).trim() === '') continue;
    const resolved = resolveImageUrl(raw);
    if (resolved && isLikelyValidHttpUrl(resolved)) {
      return resolved;
    }
  }
  const cat = (product.category || 'tops').toLowerCase();
  return CATEGORY_IMAGE_FALLBACK[cat] || CATEGORY_IMAGE_FALLBACK.tops;
}
