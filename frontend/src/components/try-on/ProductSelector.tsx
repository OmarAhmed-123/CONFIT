import { ChevronLeft, ChevronRight, Shirt, Check } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import type { Product } from '@/types';
import {
    CATEGORY_IMAGE_FALLBACK,
    getPrimaryProductImageUrl,
} from '@/lib/productImages';
import { cn } from '@/lib/utils';

interface ProductSelectorProps {
    products: Product[];
    selectedIndex: number;
    onSelectProduct: (index: number) => void;
    onTryOn: () => void;
    canTryOn: boolean;
    isProcessing: boolean;
    selectedSize: string;
    onSizeChange: (size: string) => void;
}

export function ProductSelector({
    products,
    selectedIndex,
    onSelectProduct,
    onTryOn,
    canTryOn,
    isProcessing,
    selectedSize,
    onSizeChange,
}: ProductSelectorProps) {
    const selectedProduct = products[selectedIndex];

    if (!selectedProduct || products.length === 0) {
        return (
            <div className="space-y-6">
                <div>
                    <h2 className="heading-section mb-2">Select an Item</h2>
                    <p className="text-sm text-muted-foreground">Choose what you'd like to try on virtually</p>
                </div>
                <div className="bg-card rounded-xl border border-border p-8 text-center text-muted-foreground">
                    No products available. Check back later or browse Discover.
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-xl font-semibold tracking-tight md:text-2xl">Choose a piece</h2>
                <p className="mt-1 text-sm text-muted-foreground md:text-base">
                    Curated for your profile — tap an item, pick a size, then generate.
                </p>
            </div>

            {/* Selected Product Display */}
            <motion.div
                layout
                className="rounded-2xl border border-border/80 bg-card/60 p-5 shadow-sm backdrop-blur-md md:p-6"
            >
                <div className="flex flex-col gap-6 sm:flex-row sm:gap-8">
                    <motion.div
                        layoutId={`tryon-thumb-${selectedProduct.id}`}
                        className="mx-auto h-48 w-36 shrink-0 overflow-hidden rounded-2xl bg-muted ring-1 ring-border/60 sm:mx-0 sm:h-40 sm:w-32"
                    >
                        <img
                            src={getPrimaryProductImageUrl(selectedProduct)}
                            alt={selectedProduct.name}
                            className="h-full w-full object-cover"
                            onError={(e) => {
                                const fb =
                                    CATEGORY_IMAGE_FALLBACK[selectedProduct.category] ||
                                    CATEGORY_IMAGE_FALLBACK.tops;
                                if (e.currentTarget.src !== fb) e.currentTarget.src = fb;
                            }}
                        />
                    </motion.div>
                    <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                            {selectedProduct.brand}
                        </p>
                        <h3 className="mt-1 font-semibold leading-snug tracking-tight md:text-lg">
                            {selectedProduct.name}
                        </h3>
                        <div className="mt-3 flex flex-wrap items-baseline gap-2">
                            <span className="text-2xl font-semibold tabular-nums">
                                ${selectedProduct.price}
                            </span>
                            {selectedProduct.originalPrice != null && (
                                <span className="text-sm text-muted-foreground line-through tabular-nums">
                                    ${selectedProduct.originalPrice}
                                </span>
                            )}
                        </div>

                        <div className="mt-5">
                            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                Size
                            </p>
                            <div className="flex flex-wrap gap-2">
                                {(selectedProduct.sizes ?? []).slice(0, 8).map((size) => (
                                    <button
                                        key={size}
                                        type="button"
                                        onClick={() => onSizeChange(size)}
                                        className={cn(
                                            'min-h-10 min-w-10 rounded-xl border px-3 text-sm font-medium transition-all',
                                            selectedSize === size
                                                ? 'border-accent bg-accent/15 text-accent shadow-sm'
                                                : 'border-border hover:border-accent/50 hover:text-accent'
                                        )}
                                    >
                                        {size}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <Button
                            variant="hero"
                            className="mt-6 w-full rounded-xl py-6 text-base shadow-md"
                            onClick={onTryOn}
                            disabled={!canTryOn || isProcessing}
                        >
                            <Shirt className="mr-2 h-4 w-4" />
                            {isProcessing ? 'Generating preview…' : 'Apply to my photo'}
                        </Button>
                    </div>
                </div>
            </motion.div>

            {/* Product grid */}
            <div>
                <div className="mb-4 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold tracking-tight md:text-base">Also try</h3>
                    <div className="flex gap-1">
                        <button
                            type="button"
                            onClick={() => onSelectProduct(Math.max(0, selectedIndex - 1))}
                            disabled={selectedIndex === 0}
                            className="flex h-9 w-9 items-center justify-center rounded-full border border-border transition-colors hover:bg-muted disabled:opacity-40"
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </button>
                        <button
                            type="button"
                            onClick={() =>
                                onSelectProduct(Math.min(products.length - 1, selectedIndex + 1))
                            }
                            disabled={selectedIndex === products.length - 1}
                            className="flex h-9 w-9 items-center justify-center rounded-full border border-border transition-colors hover:bg-muted disabled:opacity-40"
                        >
                            <ChevronRight className="h-4 w-4" />
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-4 gap-2 sm:gap-3">
                    {products.map((product, index) => (
                        <motion.button
                            key={product.id}
                            type="button"
                            whileHover={{ y: -2 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => onSelectProduct(index)}
                            className={cn(
                                'aspect-[3/4] overflow-hidden rounded-xl border-2 transition-colors',
                                index === selectedIndex
                                    ? 'border-accent ring-2 ring-accent/25'
                                    : 'border-transparent hover:border-border'
                            )}
                        >
                            <img
                                src={getPrimaryProductImageUrl(product)}
                                alt={product.name}
                                className="h-full w-full object-cover"
                                onError={(e) => {
                                    const fb =
                                        CATEGORY_IMAGE_FALLBACK[product.category] ||
                                        CATEGORY_IMAGE_FALLBACK.tops;
                                    if (e.currentTarget.src !== fb) e.currentTarget.src = fb;
                                }}
                            />
                        </motion.button>
                    ))}
                </div>
            </div>

            <div className="rounded-2xl border border-accent/20 bg-accent/5 p-4 backdrop-blur-sm">
                <div className="mb-2 flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent/15">
                        <Check className="h-4 w-4 text-accent" />
                    </div>
                    <span className="font-medium tracking-tight">
                        Style match · {selectedProduct.styleCompatibility ?? 85}%
                    </span>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                    Aligned with your preferences — fine-tune with another garment anytime.
                </p>
            </div>
        </div>
    );
}
