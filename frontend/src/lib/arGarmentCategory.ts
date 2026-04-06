/**
 * Maps catalog `Product.category` + name hints to AR canvas overlay placement mode.
 * Used by ARCamera (MoveNet + canvas) — not the same as FASHN category strings.
 */
import type { Product } from '@/types';

export type ArOverlayCategory = 'tops' | 'pants' | 'dress' | 'outerwear';

export function resolveArOverlayCategory(product: Product): ArOverlayCategory {
  const cat = product.category;
  if (cat === 'bottoms') return 'pants';
  if (cat === 'dresses') return 'dress';
  if (cat === 'outerwear') return 'outerwear';

  const name = product.name?.toLowerCase() || '';
  if (['pants', 'jeans', 'shorts', 'skirt', 'trousers'].some((k) => name.includes(k))) {
    return 'pants';
  }
  if (['dress', 'jumpsuit', 'romper'].some((k) => name.includes(k))) {
    return 'dress';
  }
  if (
    ['jacket', 'coat', 'bomber', 'blazer', 'parka', 'windbreaker', 'outerwear'].some((k) =>
      name.includes(k)
    )
  ) {
    return 'outerwear';
  }
  return 'tops';
}
