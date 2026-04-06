import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { Product } from '@/types';

interface WishlistContextType {
    items: Product[];
    addToWishlist: (product: Product) => void;
    removeFromWishlist: (productId: string) => void;
    isInWishlist: (productId: string) => boolean;
    clearWishlist: () => void;
    getWishlistCount: () => number;
}

const WishlistContext = createContext<WishlistContextType | undefined>(undefined);

export function WishlistProvider({ children }: { children: ReactNode }) {
    const [items, setItems] = useState<Product[]>([]);
    const [storageReady, setStorageReady] = useState(false);

    useEffect(() => {
        try {
            const saved = localStorage.getItem('wishlistItems');
            if (saved) setItems(JSON.parse(saved) as Product[]);
        } catch {
            try {
                localStorage.removeItem('wishlistItems');
            } catch {
                /* ignore */
            }
        }
        setStorageReady(true);
    }, []);

    useEffect(() => {
        if (!storageReady || typeof window === 'undefined') return;
        try {
            localStorage.setItem('wishlistItems', JSON.stringify(items));
        } catch {
            /* ignore */
        }
    }, [items, storageReady]);

    const addToWishlist = useCallback((product: Product) => {
        setItems(prev => {
            if (prev.some(item => item.id === product.id)) {
                return prev; // Already in wishlist
            }
            return [...prev, product];
        });
    }, []);

    const removeFromWishlist = useCallback((productId: string) => {
        setItems(prev => prev.filter(item => item.id !== productId));
    }, []);

    const isInWishlist = useCallback((productId: string) => {
        return items.some(item => item.id === productId);
    }, [items]);

    const clearWishlist = useCallback(() => {
        setItems([]);
    }, []);

    const getWishlistCount = useCallback(() => {
        return items.length;
    }, [items]);

    return (
        <WishlistContext.Provider value={{
            items,
            addToWishlist,
            removeFromWishlist,
            isInWishlist,
            clearWishlist,
            getWishlistCount,
        }}>
            {children}
        </WishlistContext.Provider>
    );
}

export function useWishlist() {
    const context = useContext(WishlistContext);
    if (context === undefined) {
        throw new Error('useWishlist must be used within a WishlistProvider');
    }
    return context;
}
