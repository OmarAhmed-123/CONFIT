import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import type { Product } from '@/types';
import { apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';

export interface CartItem {
    product: Product;
    quantity: number;
    size: string;
    color: string;
}

// Smart cart optimization types
export interface CartOptimization {
    suggestions: CartSuggestion[];
    savings: number;
    free_shipping_gap: number;
    bundle_opportunities: BundleOpportunity[];
    cross_sells: CrossSellItem[];
    confidence_boost: number;
}

export interface CartSuggestion {
    type: 'free_shipping' | 'bundle' | 'discount' | 'cross_sell';
    message: string;
    impact: string;
    priority: 'high' | 'medium' | 'low';
}

export interface BundleOpportunity {
    brand: string;
    item_count: number;
    potential_savings: number;
    discount_rate: number;
}

export interface CrossSellItem {
    category: string;
    reason: string;
    confidence: number;
}

export interface AbandonmentRisk {
    risk_score: number;
    risk_factors: string[];
    rescue_strategies: RescueStrategy[];
    should_intervene: boolean;
}

export interface RescueStrategy {
    type: 'discount' | 'free_shipping' | 'reminder' | 'support';
    value?: number;
    message: string;
}

interface CartContextType {
    items: CartItem[];
    addToCart: (product: Product, quantity: number, size: string, color: string) => void;
    removeFromCart: (productId: string, size: string, color: string) => void;
    updateQuantity: (productId: string, size: string, color: string, quantity: number) => void;
    clearCart: () => void;
    getCartTotal: () => number;
    getCartCount: () => number;
    // Smart cart features
    optimization: CartOptimization | null;
    abandonmentRisk: AbandonmentRisk | null;
    isLoadingOptimization: boolean;
    trackCartEvent: (eventType: string) => void;
    fetchOptimization: () => Promise<void>;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: ReactNode }) {
    const [items, setItems] = useState<CartItem[]>([]);
    const [storageReady, setStorageReady] = useState(false);

    // Hydrate from localStorage on client only (SSR has no localStorage).
    useEffect(() => {
        try {
            const saved = localStorage.getItem('cartItems');
            if (saved) setItems(JSON.parse(saved) as CartItem[]);
        } catch {
            try {
                localStorage.removeItem('cartItems');
            } catch {
                /* ignore */
            }
        }
        setStorageReady(true);
    }, []);

    // Smart cart state
    const [optimization, setOptimization] = useState<CartOptimization | null>(null);
    const [abandonmentRisk, setAbandonmentRisk] = useState<AbandonmentRisk | null>(null);
    const [isLoadingOptimization, setIsLoadingOptimization] = useState(false);
    
    // Track abandonment timer
    const abandonmentTimerRef = useRef<NodeJS.Timeout | null>(null);
    const lastEventRef = useRef<string>('');

    useEffect(() => {
        if (!storageReady || typeof window === 'undefined') return;
        try {
            localStorage.setItem('cartItems', JSON.stringify(items));
        } catch {
            /* quota / private mode */
        }
    }, [items, storageReady]);

    const addToCart = useCallback((product: Product, quantity: number, size: string, color: string) => {
        setItems(prev => {
            // Check if item already exists with same size and color
            const existingIndex = prev.findIndex(
                item => item.product.id === product.id && item.size === size && item.color === color
            );

            if (existingIndex >= 0) {
                // Update quantity
                const updated = [...prev];
                updated[existingIndex] = {
                    ...updated[existingIndex],
                    quantity: updated[existingIndex].quantity + quantity,
                };
                return updated;
            }

            // Add new item
            return [...prev, { product, quantity, size, color }];
        });
        
        // Track event for AI brain
        trackCartEvent('cart_add');
    }, []);

    const removeFromCart = useCallback((productId: string, size: string, color: string) => {
        setItems(prev => prev.filter(
            item => !(item.product.id === productId && item.size === size && item.color === color)
        ));
        trackCartEvent('cart_remove');
    }, []);

    const updateQuantity = useCallback((productId: string, size: string, color: string, quantity: number) => {
        if (quantity <= 0) {
            removeFromCart(productId, size, color);
            return;
        }

        setItems(prev => prev.map(item => {
            if (item.product.id === productId && item.size === size && item.color === color) {
                return { ...item, quantity };
            }
            return item;
        }));
    }, [removeFromCart]);

    const clearCart = useCallback(() => {
        setItems([]);
        setOptimization(null);
        setAbandonmentRisk(null);
    }, []);

    const getCartTotal = useCallback(() => {
        return items.reduce((total, item) => total + item.product.price * item.quantity, 0);
    }, [items]);

    const getCartCount = useCallback(() => {
        return items.reduce((count, item) => count + item.quantity, 0);
    }, [items]);
    
    // Track cart events for AI brain integration
    const trackCartEvent = useCallback((eventType: string) => {
        // Clear abandonment timer on activity
        if (abandonmentTimerRef.current) {
            clearTimeout(abandonmentTimerRef.current);
        }
        
        lastEventRef.current = eventType;
        
        // Set abandonment detection timer (30 seconds of inactivity)
        if (eventType !== 'checkout_start' && eventType !== 'purchase') {
            abandonmentTimerRef.current = setTimeout(() => {
                detectAbandonmentRisk();
            }, 30000);
        }
        
        // Send to backend (fire and forget)
        const token = getAuthToken();
        if (token) {
            fetch(apiUrl('/api/commerce/cart/track-event'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    event_type: eventType,
                    cart_state: {
                        total: getCartTotal(),
                        count: getCartCount(),
                        items: items.length,
                    },
                }),
            }).catch(() => {
                // Silently fail - tracking is non-critical
            });
        }
    }, [items, getCartTotal, getCartCount]);
    
    // Fetch cart optimization from backend
    const fetchOptimization = useCallback(async () => {
        if (items.length === 0) {
            setOptimization(null);
            return;
        }
        
        setIsLoadingOptimization(true);
        const token = getAuthToken();

        try {
            const response = await fetch(apiUrl('/api/commerce/cart/optimize'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    items: items.map(item => ({
                        productId: item.product.id,
                        name: item.product.name,
                        price: item.product.price,
                        quantity: item.quantity,
                        category: item.product.category,
                        brand: item.product.brand,
                        color: item.color,
                        size: item.size,
                    })),
                }),
            });
            
            if (response.ok) {
                const data = await response.json();
                setOptimization(data);
            }
        } catch (error) {
            console.error('Failed to fetch cart optimization:', error);
        } finally {
            setIsLoadingOptimization(false);
        }
    }, [items]);
    
    // Detect abandonment risk
    const detectAbandonmentRisk = useCallback(async () => {
        const token = getAuthToken();
        if (!token || items.length === 0) return;

        try {
            const response = await fetch(apiUrl('/api/commerce/cart/abandonment-risk'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    event_type: 'inactivity',
                    cart_state: {
                        total: getCartTotal(),
                        count: getCartCount(),
                        items: items.length,
                    },
                }),
            });
            
            if (response.ok) {
                const data = await response.json();
                setAbandonmentRisk(data);
            }
        } catch (error) {
            console.error('Failed to detect abandonment risk:', error);
        }
    }, [items, getCartTotal, getCartCount]);
    
    // Fetch optimization when items change
    useEffect(() => {
        if (items.length > 0) {
            fetchOptimization();
        }
    }, [items, fetchOptimization]);

    return (
        <CartContext.Provider value={{
            items,
            addToCart,
            removeFromCart,
            updateQuantity,
            clearCart,
            getCartTotal,
            getCartCount,
            // Smart cart features
            optimization,
            abandonmentRisk,
            isLoadingOptimization,
            trackCartEvent,
            fetchOptimization,
        }}>
            {children}
        </CartContext.Provider>
    );
}

export function useCart() {
    const context = useContext(CartContext);
    if (context === undefined) {
        throw new Error('useCart must be used within a CartProvider');
    }
    return context;
}
