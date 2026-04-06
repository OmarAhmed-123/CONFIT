/**
 * CONFIT — useProductViewModel
 * Encapsulates product detail page logic: fetching, size/color selection, add-to-cart, wishlist, and size calculation.
 * Used by: ProductDetail page.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useCart } from '@/context/CartContext';
import { useWishlist } from '@/context/WishlistContext';
import { mockProducts, getFeaturedProducts } from '@/services/mockData';
import { apiUrl } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import type { Product } from '@/types';

interface Store {
    id: string;
    name: string;
    address: string;
    distance: string;
    stock: 'High Stock' | 'Low Stock' | 'Out of Stock';
}

const MOCK_STORES: Store[] = [
    { id: 'store-1', name: 'CONFIT Flagship', address: '123 Fashion Ave, New York, NY', distance: '0.8 miles', stock: 'High Stock' },
    { id: 'store-2', name: 'CONFIT Downtown', address: '456 Market St, New York, NY', distance: '2.3 miles', stock: 'Low Stock' },
    { id: 'store-3', name: 'CONFIT Mall', address: '789 Shopping Ctr, Hoboken, NJ', distance: '5.1 miles', stock: 'Out of Stock' },
];

export function useProductViewModel(productId: string) {
    const router = useRouter();
    const { addToCart } = useCart();
    const { addToWishlist, removeFromWishlist, isInWishlist } = useWishlist();
    const { toast } = useToast();

    // ── Product Data ───────────────────────────────────────────────
    const [product, setProduct] = useState<Product | null>(null);
    const [relatedProducts, setRelatedProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);

    // ── Selection State ────────────────────────────────────────────
    const [selectedSize, setSelectedSize] = useState('');
    const [selectedColor, setSelectedColor] = useState('');
    const [quantity, setQuantity] = useState(1);
    const [activeImageIndex, setActiveImageIndex] = useState(0);
    const [isAddingToCart, setIsAddingToCart] = useState(false);

    // ── Size Calculator State ──────────────────────────────────────
    const [height, setHeight] = useState('');
    const [weight, setWeight] = useState('');

    // ── Load product & related items ───────────────────────────────
    useEffect(() => {
        if (!productId) return;

        setIsLoading(true);
        setNotFound(false);
        setActiveImageIndex(0);
        setQuantity(1);
        setSelectedSize('');

        // Mock data logic remains for immediate feedback
        const mock = mockProducts.find((p) => p.id === productId);
        if (mock) {
            setProduct(mock);
            setSelectedColor(mock.colors?.[0] ?? '');
            setRelatedProducts(getFeaturedProducts(4));
        }

        const controller = new AbortController();
        fetch(apiUrl(`/api/products/${productId}`), { signal: controller.signal })
            .then(async (res) => {
                if (res.status === 404) {
                    if (!mock) setNotFound(true);
                    return;
                }
                if (!res.ok) throw new Error('Failed to load');
                const data: Product = await res.json();
                setProduct(data);
                setSelectedColor(data.colors?.[0] ?? '');
                setNotFound(false);
                setRelatedProducts(getFeaturedProducts(4));
            })
            .catch(() => {
                if (!mock) setNotFound(true);
            })
            .finally(() => setIsLoading(false));

        return () => controller.abort();
    }, [productId]);

    // ── Derived State ──────────────────────────────────────────────
    const isWishlisted = product ? isInWishlist(product.id) : false;

    const fitRec = useMemo(() => {
        if (!product) return { text: 'Unknown Fit', color: 'text-muted-foreground' };
        if (product.styleCompatibility >= 90) return { text: 'Perfect Fit', color: 'text-success' };
        if (product.styleCompatibility >= 75) return { text: 'Great Fit', color: 'text-accent' };
        return { text: 'Good Fit', color: 'text-muted-foreground' };
    }, [product]);

    // ── Actions ────────────────────────────────────────────────────
    const handleAddToCart = useCallback(() => {
        if (!product) return;

        // Only require size if product HAS sizes defined
        const hasSizes = product.sizes && product.sizes.length > 0;
        if (hasSizes && !selectedSize) {
            toast({ title: 'Select a size', description: 'Please choose a size before adding to cart.', variant: 'destructive' });
            return;
        }

        setIsAddingToCart(true);
        // Add small delay to show loading state
        setTimeout(() => {
            try {
                addToCart(product, quantity, selectedSize || 'One Size', selectedColor || product.colors?.[0] || 'Default');
                toast({ title: 'Added to cart', description: `${product.name}${hasSizes ? ` — ${selectedSize}` : ''} added.` });
            } finally {
                setIsAddingToCart(false);
            }
        }, 300);
    }, [product, selectedSize, selectedColor, quantity, addToCart, toast]);

    const toggleWishlist = useCallback(() => {
        if (!product) return;
        if (isWishlisted) {
            removeFromWishlist(product.id);
            toast({ title: 'Removed from wishlist', description: 'Product removed from your favorites.' });
        } else {
            addToWishlist(product);
            toast({ title: 'Added to wishlist', description: 'Product saved to your favorites.' });
        }
    }, [product, isWishlisted, addToWishlist, removeFromWishlist, toast]);

    const calculateSize = useCallback(() => {
        if (!height || !weight) {
            toast({ title: 'Missing Info', description: "Please enter height and weight", variant: 'destructive' });
            return;
        }
        // Mock logic
        toast({ title: "We found your perfect size!", description: "Based on your measurements, we recommend size Medium." });
        setSelectedSize('M');
    }, [height, weight, toast]);

    const incrementQuantity = useCallback(() => setQuantity((q) => Math.min(q + 1, 10)), []);
    const decrementQuantity = useCallback(() => setQuantity((q) => Math.max(q - 1, 1)), []);

    return {
        // State
        product,
        relatedProducts,
        isLoading,
        notFound,
        selectedSize,
        selectedColor,
        quantity,
        activeImageIndex,
        isAddingToCart,
        isWishlisted,
        fitRec,
        stores: MOCK_STORES,
        // Size Calc State
        height,
        weight,

        // Setters
        setSelectedSize,
        setSelectedColor,
        setActiveImageIndex,
        setHeight,
        setWeight,

        // Actions
        incrementQuantity,
        decrementQuantity,
        handleAddToCart,
        toggleWishlist,
        calculateSize,
    };
}
