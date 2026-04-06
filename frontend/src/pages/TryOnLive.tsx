/**
 * Live camera AR try-on — BlazePose (MediaPipe TF.js) + TPS mesh warp + anchor smoothing.
 * Photo-based neural try-on remains on /try-on (VirtualTryOn).
 */

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/layout';
import { ARCameraPage } from '@/components/try-on/ARCameraPage';
import { useCart } from '@/context/CartContext';
import { useGender } from '@/context/GenderContext';
import { apiUrl } from '@/lib/api';
import { unwrapApiData } from '@/lib/api/envelope';
import { resolveImageUrl } from '@/lib/imageUrl';
import { CATEGORY_IMAGE_FALLBACK } from '@/lib/productImages';
import { getFeaturedProducts } from '@/services/mockData';
import type { Product } from '@/types';

function normalizeProductGender(value: unknown): Product['gender'] {
  const normalized = String(value ?? '').toLowerCase().trim();
  if (['men', 'male', 'man', 'boys'].includes(normalized)) return 'men';
  if (['women', 'female', 'woman', 'girls', 'ladies'].includes(normalized)) return 'women';
  if (['unisex', 'all', 'any'].includes(normalized)) return 'unisex';
  return 'unisex';
}

function toProduct(p: Record<string, unknown>): Product {
  const cat = (p.category as Product['category']) ?? 'tops';
  let images: string[] = Array.isArray(p.images)
    ? (p.images as unknown[]).map(resolveImageUrl).filter(Boolean)
    : p.image_url
      ? [resolveImageUrl(p.image_url)]
      : [];
  if (images.length === 0) {
    const fb = CATEGORY_IMAGE_FALLBACK[cat] ?? CATEGORY_IMAGE_FALLBACK.tops;
    images = [fb];
  }
  return {
    id: String(p.id ?? ''),
    name: String(p.name ?? ''),
    brand: String(p.brand ?? ''),
    brandId: String(p.brandId ?? p.brand_id ?? ''),
    price: Number(p.price ?? 0),
    originalPrice: p.originalPrice != null ? Number(p.originalPrice) : undefined,
    currency: String(p.currency ?? 'USD'),
    category: cat,
    subcategory: String(p.subcategory ?? ''),
    images,
    colors: Array.isArray(p.colors) ? (p.colors as string[]) : [],
    sizes: Array.isArray(p.sizes) ? (p.sizes as string[]) : ['S', 'M', 'L'],
    description: String(p.description ?? ''),
    styleCompatibility: Number(p.styleCompatibility ?? p.style_compatibility ?? 85),
    inStock: p.inStock !== false,
    tags: Array.isArray(p.tags) ? (p.tags as string[]) : [],
    gender: normalizeProductGender(p.gender ?? p.target_gender),
  };
}

export default function TryOnLive() {
  const router = useRouter();
  const { selectedGender } = useGender();
  const { addToCart } = useCart();

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort('FEATURED_PRODUCTS_TIMEOUT'), 20000);
    setLoading(true);
    setApiError(null);

    const url = apiUrl(`/api/products/featured?limit=24&gender=${selectedGender || ''}`);

    fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      signal: controller.signal,
    })
      .then(async (res) => {
        if (res.status === 307) {
          const redirectUrl = res.headers.get('Location');
          if (redirectUrl) {
            return fetch(redirectUrl, { method: 'GET', headers: { Accept: 'application/json' } });
          }
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        return res;
      })
      .then((res) => res?.json())
      .then((payload: unknown) => {
        if (cancelled) return;
        const data = unwrapApiData<unknown>(payload);
        const list = Array.isArray(data)
          ? data.map((p) => toProduct(p as Record<string, unknown>))
          : [];
        if (list.length > 0) {
          setProducts(list);
        } else {
          setProducts(getFeaturedProducts(12));
        }
      })
      .catch((error) => {
        if (!cancelled) {
          if (error instanceof DOMException && error.name === 'AbortError') {
            setApiError('Loading products took too long. Using curated fallback list.');
          } else {
            setApiError(error instanceof Error ? error.message : 'Failed to load products');
          }
          setProducts(getFeaturedProducts(12));
        }
      })
      .finally(() => {
        clearTimeout(timeoutId);
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      controller.abort('COMPONENT_UNMOUNT');
    };
  }, [selectedGender]);

  const handleAddToCart = useCallback(
    (product: Product) => {
      const size = product.sizes?.[0] || 'M';
      const color = product.colors?.[0] || 'Default';
      addToCart(product, 1, size, color);
    },
    [addToCart]
  );

  const filtered = products.filter((p) => p.gender === 'unisex' || p.gender === selectedGender);

  return (
    <MainLayout>
      {apiError && (
        <div className="container px-4 pt-4">
          <p className="text-sm text-amber-600 dark:text-amber-400">{apiError}</p>
        </div>
      )}

      {loading ? (
        <div className="container px-4 py-12 text-center text-muted-foreground">Loading catalog…</div>
      ) : (
        <ARCameraPage
          products={filtered.length > 0 ? filtered : products}
          onBack={() => router.push('/try-on')}
          onAddToCart={handleAddToCart}
        />
      )}
    </MainLayout>
  );
}
