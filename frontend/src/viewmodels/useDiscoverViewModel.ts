/**
 * CONFIT — useDiscoverViewModel
 * Encapsulates product fetching, filtering, sorting, and search for the Discover page.
 * Separates all business/data logic from the View component.
 */

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { mockProducts } from '@/services/mockData';
import { apiUrl } from '@/lib/api';
import { unwrapApiData } from '@/lib/api/envelope';
import { resolveImageUrl } from '@/lib/imageUrl';
import type { Product, ProductCategory, SortOption } from '@/types';

export interface PriceRange {
    min: number;
    max: number;
}

const DEFAULT_PRICE_RANGE: PriceRange = { min: 0, max: 1000 };

function normalizeProductGender(value: unknown): Product['gender'] {
    const normalized = String(value ?? '').toLowerCase().trim();
    if (['men', 'male', 'man', 'boys'].includes(normalized)) return 'men';
    if (['women', 'female', 'woman', 'girls', 'ladies'].includes(normalized)) return 'women';
    if (['unisex', 'all', 'any'].includes(normalized)) return 'unisex';
    return 'unisex';
}

/** Normalize API product to frontend Product type */
function toProduct(p: Record<string, unknown>): Product {
    return {
        id: String(p.id ?? ''),
        name: String(p.name ?? ''),
        brand: String(p.brand ?? ''),
        brandId: String(p.brandId ?? p.brand_id ?? ''),
        price: Number(p.price ?? 0),
        originalPrice: p.originalPrice != null ? Number(p.originalPrice) : undefined,
        currency: String(p.currency ?? 'USD'),
        category: (p.category as Product['category']) ?? 'tops',
        subcategory: String(p.subcategory ?? ''),
        images: Array.isArray(p.images)
            ? (p.images as unknown[]).map(resolveImageUrl).filter(Boolean)
            : p.image_url
                ? [resolveImageUrl(p.image_url)]
                : [],
        colors: Array.isArray(p.colors) ? (p.colors as string[]) : [],
        sizes: Array.isArray(p.sizes) ? (p.sizes as string[]) : ['S', 'M', 'L'],
        description: String(p.description ?? ''),
        styleCompatibility: Number(p.styleCompatibility ?? p.style_compatibility ?? 85),
        inStock: p.inStock !== false && p.is_active !== false,
        tags: Array.isArray(p.tags) ? (p.tags as string[]) : [],
        gender: normalizeProductGender(p.gender ?? p.target_gender),
    };
}

export function useDiscoverViewModel() {
    // ── Product data ──────────────────────────────────────────────
    const [products, setProducts] = useState<Product[]>(() => mockProducts);
    const [isLoading, setIsLoading] = useState(false);
    const [fetchError, setFetchError] = useState<string | null>(null);

    // ── Filter state ──────────────────────────────────────────────
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedQuery, setDebouncedQuery] = useState('');
    const [selectedCategories, setSelectedCategories] = useState<ProductCategory[]>([]);
    const [priceRange, setPriceRange] = useState<PriceRange>(DEFAULT_PRICE_RANGE);
    const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
    const [selectedColors, setSelectedColors] = useState<string[]>([]);
    const [inStockOnly, setInStockOnly] = useState(false);
    const [sortBy, setSortBy] = useState<SortOption>('relevance');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [showFilters, setShowFilters] = useState(false);

    // ── Infinite scroll state ─────────────────────────────────────
    const PAGE_SIZE = 24;
    const seenIdsRef = useRef<Set<string>>(new Set(mockProducts.map((p) => p.id)));
    const loadMoreLockRef = useRef(false);
    const [offset, setOffset] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);

    // ── Debounce search query ──────────────────────────────────────
    useEffect(() => {
        const id = setTimeout(() => setDebouncedQuery(searchQuery), 300);
        return () => clearTimeout(id);
    }, [searchQuery]);

    // ── Fetch page (reset + append) ─────────────────────────────────────
    const fetchPage = useCallback(
        async ({
            pageOffset,
            replace,
            controller,
        }: {
            pageOffset: number;
            replace: boolean;
            controller: AbortController;
        }) => {
            const params = new URLSearchParams();
            params.set("limit", String(PAGE_SIZE));
            params.set("offset", String(pageOffset));

            if (debouncedQuery) params.set("search", debouncedQuery);
            if (selectedCategories.length === 1) params.set("category", selectedCategories[0] as string);

            // Backend supports min/max price; keep aligned with UI bounds.
            if (priceRange.min > 0) params.set("min_price", String(priceRange.min));
            if (priceRange.max < DEFAULT_PRICE_RANGE.max) params.set("max_price", String(priceRange.max));

            const url = `${apiUrl("/api/products")}?${params.toString()}`;

            const res = await fetch(url, {
                method: "GET",
                headers: { "Content-Type": "application/json", Accept: "application/json" },
                signal: controller.signal,
            });

            // Handle 307 redirect manually (mirrors existing logic).
            if (res.status === 307) {
                const redirectUrl = res.headers.get("Location");
                if (redirectUrl) {
                    const redirectRes = await fetch(redirectUrl, {
                        method: "GET",
                        headers: { Accept: "application/json" },
                    });
                    if (redirectRes.ok) {
                        return (await redirectRes.json()) as unknown;
                    }
                }
            }

            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);

            return res.json() as Promise<unknown>;
        },
        [PAGE_SIZE, debouncedQuery, selectedCategories, priceRange.max, priceRange.min]
    );

    // Reset pagination when key inputs change.
    useEffect(() => {
        let cancelled = false;
        const controller = new AbortController();
        let timeoutId: ReturnType<typeof setTimeout> | null = null;

        const run = async () => {
            try {
                timeoutId = setTimeout(() => controller.abort("DISCOVER_PRODUCTS_TIMEOUT"), 45000);

                seenIdsRef.current = new Set();
                loadMoreLockRef.current = false;
                setOffset(0);
                setHasMore(true);
                setIsLoading(true);
                setIsLoadingMore(false);
                setFetchError(null);

                const payload = await fetchPage({ pageOffset: 0, replace: true, controller });
                const data = unwrapApiData<unknown>(payload);
                const list = Array.isArray(data) ? data.map((p: Record<string, unknown>) => toProduct(p)) : [];

                if (cancelled) return;

                if (list.length > 0) {
                    seenIdsRef.current = new Set(list.map((p) => p.id));
                    setProducts(list);
                    setHasMore(list.length === PAGE_SIZE);
                } else {
                    // Keep mock data as fallback if backend returned nothing.
                    setProducts(mockProducts);
                    setHasMore(false);
                }
            } catch (error) {
                if (cancelled) return;
                if (!(error instanceof DOMException && error.name === "AbortError")) {
                    setFetchError(`API Error: ${error instanceof Error ? error.message : "Unknown error"}`);
                }
                setProducts(mockProducts);
                setHasMore(false);
                setIsLoading(false);
            } finally {
                if (!cancelled) setIsLoading(false);
                if (timeoutId) clearTimeout(timeoutId);
            }
        };

        void run();

        return () => {
            cancelled = true;
            controller.abort("DISCOVER_RESET");
            if (timeoutId) clearTimeout(timeoutId);
        };
    }, [
        fetchPage,
        selectedBrands,
        selectedColors,
        inStockOnly,
        priceRange.min,
        priceRange.max,
        selectedCategories,
        debouncedQuery,
    ]);

    // ── Load next page ─────────────────────────────────────────────────
    const loadMore = useCallback(async () => {
        if (isLoadingMore || isLoading || !hasMore) return;
        if (loadMoreLockRef.current) return;

        const controller = new AbortController();
        let timeoutId: ReturnType<typeof setTimeout> | null = null;
        try {
            loadMoreLockRef.current = true;
            setIsLoadingMore(true);
            timeoutId = setTimeout(() => controller.abort("DISCOVER_LOAD_MORE_TIMEOUT"), 45000);

            const nextOffset = offset + PAGE_SIZE;
            const payload = await fetchPage({ pageOffset: nextOffset, replace: false, controller });
            const data = unwrapApiData<unknown>(payload);
            const list = Array.isArray(data) ? data.map((p: Record<string, unknown>) => toProduct(p)) : [];

            if (list.length === 0) {
                setHasMore(false);
                return;
            }

            const deduped = list.filter((p) => !seenIdsRef.current.has(p.id));
            deduped.forEach((p) => seenIdsRef.current.add(p.id));

            setProducts((prev) => [...prev, ...deduped]);
            setOffset(nextOffset);
            setHasMore(list.length === PAGE_SIZE);
        } catch {
            // Best-effort: stop further loading on failure.
            setHasMore(false);
        } finally {
            if (timeoutId) clearTimeout(timeoutId);
            setIsLoadingMore(false);
            loadMoreLockRef.current = false;
        }
    }, [fetchPage, hasMore, isLoading, isLoadingMore, offset, PAGE_SIZE]);

    // ── Derived: filtered products ─────────────────────────────────
    const filteredProducts = useMemo(() => {
        const filtered = products.filter((product) => {
            // Ensure product has required fields
            if (!product || !product.name || product.price === undefined || !product.category) {
                return false;
            }

            // Text search
            if (debouncedQuery) {
                const q = debouncedQuery.toLowerCase();
                const matches =
                    product.name.toLowerCase().includes(q) ||
                    (product.brand && product.brand.toLowerCase().includes(q)) ||
                    product.category.toLowerCase().includes(q);
                if (!matches) return false;
            }

            // Category
            if (selectedCategories.length > 0 && !selectedCategories.includes(product.category as ProductCategory)) {
                return false;
            }

            // Price - ensure price is a number
            const productPrice = Number(product.price);
            if (isNaN(productPrice) || productPrice < priceRange.min || productPrice > priceRange.max) {
                return false;
            }

            // Brand
            if (selectedBrands.length > 0 && (!product.brand || !selectedBrands.includes(product.brand))) return false;

            // Color - ensure colors array exists
            if (selectedColors.length > 0 && (!product.colors || !product.colors.some((c) => selectedColors.includes(c)))) return false;

            // Stock
            if (inStockOnly && product.inStock === false) return false;

            return true;
        });
        return filtered;
    }, [products, debouncedQuery, selectedCategories, priceRange, selectedBrands, selectedColors, inStockOnly]);

    // ── Derived: sorted products ───────────────────────────────────
    const sortedProducts = useMemo(() => {
        return [...filteredProducts].sort((a, b) => {
            switch (sortBy) {
                case 'price-asc': 
                    return Number(a.price || 0) - Number(b.price || 0);
                case 'price-desc': 
                    return Number(b.price || 0) - Number(a.price || 0);
                case 'popularity': 
                    return (b.styleCompatibility || 0) - (a.styleCompatibility || 0);
                case 'newest':
                    return String(b.id).localeCompare(String(a.id));
                default: 
                    return 0;
            }
        });
    }, [filteredProducts, sortBy]);

    // ── Active filter count ────────────────────────────────────────
    const activeFiltersCount = useMemo(() =>
        selectedCategories.length +
        selectedBrands.length +
        selectedColors.length +
        (priceRange.min > 0 || priceRange.max < DEFAULT_PRICE_RANGE.max ? 1 : 0) +
        (inStockOnly ? 1 : 0),
        [selectedCategories, selectedBrands, selectedColors, priceRange, inStockOnly]
    );

    const clearAllFilters = useCallback(() => {
        setSelectedCategories([]);
        setPriceRange(DEFAULT_PRICE_RANGE);
        setSelectedBrands([]);
        setSelectedColors([]);
        setInStockOnly(false);
        setSearchQuery('');
    }, []);

    const toggleCategory = useCallback((cat: ProductCategory) => {
        setSelectedCategories((prev) =>
            prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
        );
    }, []);

    const toggleBrand = useCallback((brand: string) => {
        setSelectedBrands((prev) =>
            prev.includes(brand) ? prev.filter((b) => b !== brand) : [...prev, brand]
        );
    }, []);

    const toggleColor = useCallback((color: string) => {
        setSelectedColors((prev) =>
            prev.includes(color) ? prev.filter((c) => c !== color) : [...prev, color]
        );
    }, []);

    return {
        // State
        products,
        sortedProducts,
        isLoading,
        isLoadingMore,
        hasMore,
        fetchError,
        searchQuery,
        selectedCategories,
        priceRange,
        selectedBrands,
        selectedColors,
        inStockOnly,
        sortBy,
        viewMode,
        showFilters,
        activeFiltersCount,
        isDebouncing: searchQuery !== debouncedQuery,
        resultCount: sortedProducts.length,
        totalCount: products.length,

        // Setters
        setSearchQuery,
        setSelectedCategories,
        setPriceRange,
        setSelectedBrands,
        setSelectedColors,
        setInStockOnly,
        setSortBy,
        setViewMode,
        setShowFilters,

        // Actions
        clearAllFilters,
        toggleCategory,
        toggleBrand,
        toggleColor,
        loadMore,
    };
}
