/**
 * CONFIT — useWardrobeViewModel
 * Encapsulates wardrobe item fetching, upload, filtering, deletion, outfit generation, and resale listing.
 * Used by: Wardrobe page.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { apiUrl, apiFetch } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';
import type { ProductCategory } from '@/types';
import { sampleWardrobeItems, mockAutoTagging } from '@/services/mockData';
import { closetService, type ClosetItem } from '@/services/aiFeaturesService';

export interface WardrobeItemData {
    id: string;
    name: string;
    category: ProductCategory;
    color: string;
    image: string;
    brand?: string;
    tags?: string[];
    price?: number; // Estimated resale value or original price
    created_at?: string;
}

export interface WardrobeItemInput {
    name: string;
    category: ProductCategory;
    color: string;
    brand?: string;
    image: string; // Base64 or URL
    tags?: string[];
}

export function useWardrobeViewModel() {
    const { toast } = useToast();
    const [token, setToken] = useState<string | null>(getAuthToken());

    const [items, setItems] = useState<WardrobeItemData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [isUploading, setIsUploading] = useState(false);

    // Refresh token on mount/change
    useEffect(() => {
        setToken(getAuthToken());
    }, []);

    // ── Fetch Items ────────────────────────────────────────────────
    const fetchItems = useCallback(async () => {
        setIsLoading(true);
        const currentToken = getAuthToken();

        // Use samples if not authenticated
        if (!currentToken) {
            setItems(sampleWardrobeItems as unknown as WardrobeItemData[]);
            setIsLoading(false);
            return;
        }

        try {
            // Use v1 CLOSET service
            const data = await closetService.getItems();
            const mapped: WardrobeItemData[] = (data || []).map((item: ClosetItem) => ({
                id: String(item.id),
                name: String(item.name),
                category: item.category as ProductCategory,
                color: (item.colors?.[0]) || 'unknown',
                image: item.image_url || 'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=300&h=400&fit=crop',
                brand: item.brands?.[0],
                tags: item.tags,
                price: item.purchase_price,
            }));

            if (mapped.length > 0) {
                setItems(mapped);
            } else {
                setItems([]);
            }
        } catch {
            // Fallback to legacy endpoint
            try {
                const res = await apiFetch('/api/wardrobe/items', { token: currentToken });
                if (res.ok) {
                    const data = await res.json();
                    const mapped = Array.isArray(data) ? data.map((item: any) => ({
                        id: String(item.id),
                        name: String(item.name),
                        category: item.category as ProductCategory,
                        color: String(item.color),
                        image: item.image_url || item.image || 'https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=300&h=400&fit=crop',
                        brand: item.brand,
                        tags: item.tags,
                        price: item.price,
                    })) : [];
                    setItems(mapped);
                } else {
                    setItems(sampleWardrobeItems as unknown as WardrobeItemData[]);
                }
            } catch {
                setItems(sampleWardrobeItems as unknown as WardrobeItemData[]);
            }
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchItems();
    }, [fetchItems]);

    // ── Filtering ──────────────────────────────────────────────────
    const filteredItems = useMemo(() => {
        return items.filter((item) => {
            const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory;
            const matchesSearch =
                !searchQuery ||
                item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (item.brand ?? '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                item.color.toLowerCase().includes(searchQuery.toLowerCase());
            return matchesCategory && matchesSearch;
        });
    }, [items, selectedCategory, searchQuery]);

    const categories = useMemo(() => {
        const unique = new Set(items.map((i) => i.category).filter(Boolean));
        return ['all', ...Array.from(unique)];
    }, [items]);

    // ── Actions ────────────────────────────────────────────────────

    const addItem = useCallback(async (input: WardrobeItemInput) => {
        const currentToken = getAuthToken();
        const tempId = `item-${Date.now()}`;

        // Optimistic update for unauthenticated or fallback
        const newItem: WardrobeItemData = {
            id: tempId,
            name: input.name,
            category: input.category,
            color: input.color,
            brand: input.brand,
            image: input.image,
            tags: input.tags,
        };

        if (!currentToken) {
            setItems((prev) => [newItem, ...prev]);
            toast({ title: 'Item added (Local)', description: 'Sign in to save permanently.' });
            return;
        }

        setIsUploading(true);
        try {
            const res = await apiFetch('/api/wardrobe/items', {
                method: 'POST',
                token: currentToken,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: input.name,
                    category: input.category,
                    color: input.color,
                    brand: input.brand,
                    tags: input.tags,
                    image_url: input.image.startsWith('http') ? input.image : undefined,
                    // Note: Base64 images for upload might need separate handling or specific backend support.
                    // If image is a data URL, we might need to assume the backend handles it or we upload it separately.
                    // For now, we try to pass it.
                }),
            });

            if (res.ok) {
                const created = await res.json();
                const mapped: WardrobeItemData = {
                    id: String(created.id),
                    name: String(created.name),
                    category: created.category as ProductCategory,
                    color: String(created.color),
                    image: created.image_url || input.image,
                    brand: created.brand,
                    tags: created.tags,
                };
                setItems((prev) => [mapped, ...prev]);
                toast({ title: 'Item added successfully' });
            } else {
                // Fallback to local
                setItems((prev) => [newItem, ...prev]);
                toast({ title: 'Item added (Local)', description: 'Could not sync to server.' });
            }
        } catch {
            setItems((prev) => [newItem, ...prev]);
            toast({ title: 'Item added (Local)', description: 'Network error.' });
        } finally {
            setIsUploading(false);
        }
    }, [toast]);

    const analyzeImage = useCallback(async (file: File) => {
        setIsUploading(true);
        const currentToken = getAuthToken();

        try {
            // Try v1 CLOSET service (auto-tags on upload)
            if (currentToken) {
                try {
                    const item = await closetService.uploadItem(file);
                    setIsUploading(false);
                    return {
                        category: item.category as ProductCategory,
                        color: item.colors?.[0] || 'unknown',
                        tags: item.tags || [],
                    };
                } catch {
                    // Fallback to legacy auto-tag endpoint
                }

                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch(apiUrl('/api/wardrobe/auto-tag'), {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${currentToken}` },
                    body: formData,
                });

                if (res.ok) {
                    const data = await res.json();
                    setIsUploading(false);
                    return {
                        category: data.category as ProductCategory,
                        color: data.color,
                        tags: data.tags || [],
                    };
                }
            }

            // Fallback to mock
            const tags = await mockAutoTagging(file);
            setIsUploading(false);
            return tags;

        } catch (error) {
            console.error("Analysis failed", error);
            // Fallback to mock
            const tags = await mockAutoTagging(file);
            setIsUploading(false);
            return tags;
        }
    }, []);

    const checkDuplicate = useCallback(async (input: WardrobeItemInput) => {
        const currentToken = getAuthToken();
        if (!currentToken) {
            const duplicate = items.find((i) =>
                i.category === input.category &&
                i.color === input.color &&
                i.name === input.name
            );
            return duplicate ? { hasDuplicates: true, matches: [duplicate] } : { hasDuplicates: false };
        }

        try {
            // Use v1 CLOSET duplicate check
            const result = await closetService.checkDuplicate({
                product_name: input.name,
                category: input.category,
                color: input.color,
            });
            return {
                hasDuplicates: result.has_duplicate,
                matches: result.existing_item ? [result.existing_item] : [],
            };
        } catch {
            // Fallback to legacy endpoint
            try {
                const res = await fetch(apiUrl('/api/wardrobe/items/check-duplicate'), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${currentToken}`
                    },
                    body: JSON.stringify(input),
                });
                if (res.ok) {
                    return await res.json();
                }
            } catch {
                return { hasDuplicates: false };
            }
            return { hasDuplicates: false };
        }
    }, [items]);

    const deleteItem = useCallback(async (id: string) => {
        const currentToken = getAuthToken();
        if (!currentToken) {
            setItems(prev => prev.filter(i => i.id !== id));
            toast({ title: 'Item removed (Local)' });
            return;
        }

        try {
            const res = await apiFetch(`/api/wardrobe/items/${id}`, {
                method: 'DELETE',
                token: currentToken
            });

            if (res.ok) {
                setItems((prev) => prev.filter((item) => item.id !== id));
                toast({ title: 'Item removed from wardrobe' });
            } else {
                throw new Error('Delete failed');
            }
        } catch {
            toast({ title: 'Failed to remove item', variant: 'destructive' });
        }
    }, [toast]);

    const generateOutfitIdea = useCallback(async () => {
        const currentToken = getAuthToken();
        if (currentToken) {
            try {
                // Use v1 CLOSET outfit suggestions
                const suggestions = await closetService.getSuggestions();
                if (suggestions && suggestions.length > 0) {
                    toast({
                        title: 'Outfit ideas generated!',
                        description: `${suggestions.length} look(s) found mixing your closet + catalog.`,
                    });
                    return;
                }
            } catch {
                // Fallback to legacy
                try {
                    const res = await apiFetch('/api/wardrobe/outfits/suggestions', { token: currentToken });
                    if (res.ok) {
                        const suggestions = await res.json();
                        if (Array.isArray(suggestions) && suggestions.length > 0) {
                            toast({
                                title: 'Outfit ideas generated!',
                                description: `${suggestions.length} look(s) found.`,
                            });
                            return;
                        }
                    }
                } catch {
                    // fallback
                }
            }
        }

        // Local logic
        const top = items.find((i) => i.category === 'tops');
        const bottom = items.find((i) => i.category === 'bottoms');
        if (top && bottom) {
            toast({
                title: 'Outfit idea',
                description: `Try pairing your ${top.name} with your ${bottom.name}!`,
            });
        } else {
            toast({
                title: 'Add more items',
                description: 'Add tops and bottoms to get outfit suggestions!',
            });
        }

    }, [items, toast]);

    const listForResale = useCallback(async (id: string, price: number = 49) => {
        const currentToken = getAuthToken();
        if (!currentToken) {
            toast({ title: 'Please sign in', description: 'You need to be signed in to list items for resale.', variant: 'destructive' });
            return false;
        }

        try {
            const res = await fetch(apiUrl(`/api/resale/list-from-wardrobe/${id}`), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${currentToken}`,
                },
                body: JSON.stringify({ price, currency: 'USD' }),
            });
            if (res.ok) {
                toast({ title: 'Listed for resale', description: 'Your item is now in the marketplace.' });
                return true;
            } else {
                const errorData = await res.json().catch(() => ({}));
                const errorMsg = errorData.detail || `Error: ${res.status}`;
                toast({ title: 'Failed to list item', description: errorMsg, variant: 'destructive' });
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error';
            toast({ title: 'Failed to list item', description: message, variant: 'destructive' });
        }
        return false;
    }, [toast]);


    return {
        // State
        items: filteredItems,
        allItems: items, // Exposed for logic if needed
        isLoading,
        isUploading,
        searchQuery,
        selectedCategory,
        categories,

        // Setters
        setSearchQuery,
        setSelectedCategory,

        // Actions
        addItem,
        deleteItem,
        analyzeImage,
        checkDuplicate,
        generateOutfitIdea,
        listForResale,
        refresh: fetchItems,
    };
}
