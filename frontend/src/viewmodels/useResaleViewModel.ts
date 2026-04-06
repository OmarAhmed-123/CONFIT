/**
 * CONFIT — useResaleViewModel
 * Handles resale marketplace loading, filtering, buying, and eco-impact.
 * Used by: Resale page.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { apiFetch, apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';

export interface ResaleListing {
    id: string;
    wardrobe_item_id: string;
    seller_user_id: string;
    buyer_user_id?: string | null;
    status: 'draft' | 'active' | 'sold' | 'cancelled';
    price: number;
    currency: string;
    created_at: string;
    sold_at?: string | null;
    item_name?: string | null;
    item_brand?: string | null;
    item_category?: string | null;
    item_color?: string | null;
    item_image_url?: string | null;
}

export interface EcoImpact {
    co2_saved_kg: number;
    water_saved_l: number;
    message: string;
}

export function useResaleViewModel() {
    const { toast } = useToast();
    const token = getAuthToken();

    const [tab, setTab] = useState<'market' | 'seller'>('market');
    const [listings, setListings] = useState<ResaleListing[]>([]); // Market listings
    const [myListings, setMyListings] = useState<ResaleListing[]>([]); // Seller listings
    const [impact, setImpact] = useState<EcoImpact | null>(null);
    const [search, setSearch] = useState('');
    const [isBuying, setIsBuying] = useState<string | null>(null); // listing id being purchased
    const [isLoading, setIsLoading] = useState(true);

    const fetchMarket = useCallback(async () => {
        try {
            const res = await apiFetch('/api/resale/listings?status=active&limit=80');
            if (res.ok) setListings(await res.json());
        } catch { /* silent */ }
    }, []);

    const fetchSeller = useCallback(async () => {
        const currentToken = getAuthToken();
        if (!currentToken) return;
        try {
            const [listRes, impactRes] = await Promise.all([
                apiFetch('/api/resale/my-listings', { token: currentToken }),
                apiFetch('/api/resale/eco-impact?period=weekly', { token: currentToken }),
            ]);
            if (listRes.ok) setMyListings(await listRes.json());
            if (impactRes.ok) setImpact(await impactRes.json());
        } catch { /* silent */ }
    }, []);

    const fetchAll = useCallback(async () => {
        setIsLoading(true);
        await Promise.all([fetchMarket(), fetchSeller()]);
        setIsLoading(false);
    }, [fetchMarket, fetchSeller]);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    const displayedListings = useMemo(() => {
        const source = tab === 'market' ? listings : myListings;
        const q = search.trim().toLowerCase();
        if (!q) return source;
        return source.filter((l) =>
            `${l.item_name ?? ''} ${l.item_brand ?? ''} ${l.item_category ?? ''} ${l.item_color ?? ''}`.toLowerCase().includes(q)
        );
    }, [tab, listings, myListings, search]);

    const buy = useCallback(async (id: string) => {
        const currentToken = getAuthToken();
        if (!currentToken) {
            toast({ title: 'Sign in required', description: 'Please log in to purchase.', variant: 'destructive' });
            return;
        }
        setIsBuying(id);
        try {
            const res = await apiFetch(`/api/resale/listings/${id}/purchase`, {
                method: 'POST',
                token: currentToken
            });
            if (!res.ok) throw new Error('Purchase failed');
            toast({ title: 'Purchased!', description: 'Purchase recorded successfully.' });
            fetchAll();
        } catch {
            toast({ title: 'Purchase failed', description: 'Please try again.', variant: 'destructive' });
        } finally {
            setIsBuying(null);
        }
    }, [toast, fetchAll]);

    return {
        tab,
        listings: displayedListings,
        impact,
        search,
        isBuying,
        isLoading,
        setTab,
        setSearch,
        buy,
        refresh: fetchAll,
    };
}
