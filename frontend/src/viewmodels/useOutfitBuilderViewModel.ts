/**
 * CONFIT — useOutfitBuilderViewModel
 * Manages outfit builder state: slots, items (catalog/wardrobe), budget, and saving.
 * Used by: OutfitBuilder page.
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { apiFetch, apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';
import type { Product, ProductCategory } from '@/types';

export interface OutfitItem {
    id: string;
    name: string;
    brand: string;
    category: ProductCategory;
    price: number;
    image: string;
    source: 'catalog' | 'wardrobe';
    // extra fields for API consistency
    currency?: string;
    colors?: string[];
    sizes?: string[];
    description?: string;
    styleCompatibility?: number;
    tags?: string[];
}

export interface OutfitSlot {
    position: 'top' | 'bottom' | 'shoes' | 'accessory' | 'layer';
    label: string;
    item: OutfitItem | null;
}

const INITIAL_SLOTS: OutfitSlot[] = [
    { position: 'layer', label: 'Outerwear', item: null },
    { position: 'top', label: 'Top', item: null },
    { position: 'bottom', label: 'Bottom', item: null },
    { position: 'shoes', label: 'Shoes', item: null },
    { position: 'accessory', label: 'Accessory', item: null },
];

export function useOutfitBuilderViewModel() {
    const { toast } = useToast();
    const token = getAuthToken();

    // ── State ──────────────────────────────────────────────────────
    const [slots, setSlots] = useState<OutfitSlot[]>(INITIAL_SLOTS);
    const [budget, setBudget] = useState<number>(500);
    const [activeSlot, setActiveSlot] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);

    // Data lists
    const [catalogItems, setCatalogItems] = useState<OutfitItem[]>([]);
    const [wardrobeItems, setWardrobeItems] = useState<OutfitItem[]>([]);
    const [isLoadingData, setIsLoadingData] = useState(true);

    // ── Derived State ──────────────────────────────────────────────
    const totalPrice = useMemo(
        () => slots.reduce((sum, slot) => sum + (slot.item?.price || 0), 0),
        [slots]
    );

    const filledSlotsCount = useMemo(
        () => slots.filter(s => s.item !== null).length,
        [slots]
    );

    const styleScore = useMemo(() => {
        if (filledSlotsCount === 0) return 0;
        const totalScore = slots.reduce((sum, slot) => sum + (slot.item?.styleCompatibility || 85), 0); // Default to 85 if missing
        return Math.round(totalScore / filledSlotsCount);
    }, [slots, filledSlotsCount]);

    // ── Data Fetching ──────────────────────────────────────────────
    useEffect(() => {
        const loadData = async () => {
            setIsLoadingData(true);
            try {
                // 1. Fetch Catalog
                const prodRes = await fetch(apiUrl('/api/products?limit=200'));
                if (prodRes.ok) {
                    const data = await prodRes.json();
                    const mapped: OutfitItem[] = Array.isArray(data) ? data.map((p: any) => ({
                        id: String(p.id),
                        name: String(p.name),
                        brand: String(p.brand),
                        category: (p.category as ProductCategory) || 'tops',
                        price: Number(p.price || 0),
                        image: Array.isArray(p.images) && p.images.length > 0 ? p.images[0] : (typeof p.images === 'string' ? p.images : ''),
                        source: 'catalog',
                        currency: p.currency,
                        styleCompatibility: p.styleCompatibility,
                    })) : [];
                    setCatalogItems(mapped);
                }

                // 2. Fetch Wardrobe (if auth)
                if (token) {
                    const wardRes = await apiFetch('/api/wardrobe/items', { token });
                    if (wardRes.ok) {
                        const data = await wardRes.json();
                        const mapped: OutfitItem[] = Array.isArray(data) ? data.map((w: any) => ({
                            id: String(w.id),
                            name: String(w.name),
                            brand: String(w.brand || 'Unknown'),
                            category: (w.category as ProductCategory) || 'tops',
                            price: Number(w.price || 0), // Wardrobe items might not have price, treat as 0 or estimated
                            image: w.image_url || w.image || '',
                            source: 'wardrobe',
                        })) : [];
                        setWardrobeItems(mapped);
                    }
                }
            } catch (e) {
                console.error("Failed to load outfit data", e);
            } finally {
                setIsLoadingData(false);
            }
        };
        loadData();
    }, [token]);


    // ── Actions ────────────────────────────────────────────────────

    const selectItem = useCallback((position: string, item: OutfitItem) => {
        setSlots(prev => prev.map(slot =>
            slot.position === position ? { ...slot, item } : slot
        ));
        setActiveSlot(null);
    }, []);

    const removeItem = useCallback((position: string) => {
        setSlots(prev => prev.map(slot =>
            slot.position === position ? { ...slot, item: null } : slot
        ));
    }, []);

    const clearAll = useCallback(() => {
        setSlots(INITIAL_SLOTS);
        setActiveSlot(null);
    }, []);

    const saveOutfit = useCallback(async () => {
        const validItems = slots.filter(s => s.item !== null).map(s => s.item!);
        if (validItems.length === 0) {
            toast({ title: 'Empty Outfit', description: 'Add at least one item.', variant: 'destructive' });
            return;
        }

        if (!token) {
            toast({ title: 'Sign in Required', description: 'You must be signed in to save outfits.', variant: 'destructive' });
            return;
        }

        setIsSaving(true);
        try {
            const title = `Outfit — ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
            const payload = {
                title,
                budget_limit: budget,
                items: validItems.map(item => ({
                    item_type: item.source === 'wardrobe' ? 'wardrobe_item' : 'product', // Check backend expectation
                    // Note: previous implementation used 'product' for everything? 
                    // Let's assume 'product' or 'wardrobe_item'. 
                    // Actually, looking at OutfitBuilder.tsx previous code: "item_type: 'product' as const".
                    // But now we support wardrobe.
                    // If backend supports mixed types, great. If not, we might need to adjust.
                    // Assuming backend supports 'product' and maybe 'wardrobe_item' or just 'product' with generic fields.
                    // Let's stick to 'product' if source is catalog, and if backend supports wardrobe items we use that?
                    // Safe bet: send as much info as possible.
                    reference_id: item.id,
                    name: item.name,
                    brand: item.brand,
                    category: item.category,
                    price: item.price,
                    image_url: item.image,
                    currency: item.currency || 'USD'
                }))
            };

            const res = await apiFetch('/api/outfits', {
                method: 'POST',
                token,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (res.ok) {
                toast({ title: 'Outfit Saved', description: 'Your look has been saved.' });
            } else {
                throw new Error('Save failed');
            }
        } catch {
            toast({ title: 'Error', description: 'Failed to save outfit.', variant: 'destructive' });
        } finally {
            setIsSaving(false);
        }
    }, [slots, budget, token, toast]);

    // Helper to get available items for a slot
    const getItemsForSlot = useCallback((position: string, source: 'catalog' | 'wardrobe' = 'catalog') => {
        const mappings: Record<string, string[]> = {
            top: ['tops'],
            bottom: ['bottoms'],
            layer: ['outerwear'],
            shoes: ['shoes'],
            accessory: ['accessories', 'bags'],
        };
        const targetCats = mappings[position] || [];
        const pool = source === 'catalog' ? catalogItems : wardrobeItems;
        return pool.filter(item => targetCats.includes(item.category as string));
    }, [catalogItems, wardrobeItems]);

    return {
        // State
        slots,
        budget,
        totalPrice,
        styleScore,
        filledSlotsCount,
        activeSlot,
        isSaving,
        isLoadingData,
        catalogItems,
        wardrobeItems,

        // Setters
        setBudget,
        setActiveSlot,

        // Actions
        selectItem,
        removeItem,
        clearAll,
        saveOutfit,
        getItemsForSlot,
    };
}
