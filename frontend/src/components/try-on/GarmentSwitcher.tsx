/**
 * GarmentSwitcher — Quick garment selection strip
 *
 * Horizontal scrollable thumbnail strip for instant garment switching.
 * Integrates with useLivePreview for real-time updates.
 */

import { useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Product } from '@/types';
import {
    CATEGORY_IMAGE_FALLBACK,
    getPrimaryProductImageUrl,
} from '@/lib/productImages';

interface GarmentSwitcherProps {
    products: Product[];
    selectedIndex: number;
    onSelect: (index: number) => void;
    isProcessing?: boolean;
}

export function GarmentSwitcher({
    products,
    selectedIndex,
    onSelect,
    isProcessing = false,
}: GarmentSwitcherProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    const scroll = useCallback((direction: 'left' | 'right') => {
        if (!scrollRef.current) return;
        const amount = direction === 'left' ? -200 : 200;
        scrollRef.current.scrollBy({ left: amount, behavior: 'smooth' });
    }, []);

    if (products.length === 0) {
        return (
            <div className="text-center py-4 text-sm text-muted-foreground">
                No garments available
            </div>
        );
    }

    return (
        <div className="relative">
            {/* Scroll Controls */}
            {products.length > 4 && (
                <>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="absolute left-0 top-1/2 -translate-y-1/2 z-10 h-8 w-8 bg-background/80 backdrop-blur-sm shadow-sm"
                        onClick={() => scroll('left')}
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-1/2 -translate-y-1/2 z-10 h-8 w-8 bg-background/80 backdrop-blur-sm shadow-sm"
                        onClick={() => scroll('right')}
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </>
            )}

            {/* Thumbnails */}
            <div
                ref={scrollRef}
                className="flex gap-2 overflow-x-auto scrollbar-hide px-1 py-2"
                style={{ scrollSnapType: 'x mandatory' }}
            >
                {products.map((product, index) => {
                    const isSelected = index === selectedIndex;
                    return (
                        <motion.button
                            key={product.id}
                            onClick={() => onSelect(index)}
                            disabled={isProcessing}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            className={`
                                relative flex-shrink-0 w-16 h-20 rounded-lg overflow-hidden
                                border-2 transition-all duration-200
                                ${isSelected
                                    ? 'border-primary shadow-md shadow-primary/20'
                                    : 'border-transparent hover:border-muted-foreground/30'}
                                ${isProcessing ? 'opacity-60 cursor-wait' : 'cursor-pointer'}
                            `}
                            style={{ scrollSnapAlign: 'start' }}
                        >
                            <img
                                src={getPrimaryProductImageUrl(product)}
                                alt={product.name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                    const fb =
                                        CATEGORY_IMAGE_FALLBACK[product.category] ||
                                        CATEGORY_IMAGE_FALLBACK.tops;
                                    if (e.currentTarget.src !== fb) e.currentTarget.src = fb;
                                }}
                                loading="lazy"
                            />
                            {isSelected && (
                                <motion.div
                                    layoutId="garment-indicator"
                                    className="absolute inset-0 bg-primary/10 border-2 border-primary rounded-lg"
                                />
                            )}
                        </motion.button>
                    );
                })}
            </div>

            {/* Selected Name */}
            {products[selectedIndex] && (
                <p className="text-xs text-center text-muted-foreground mt-1 truncate px-4">
                    {products[selectedIndex].name}
                </p>
            )}
        </div>
    );
}
