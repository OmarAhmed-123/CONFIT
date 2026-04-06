import { motion } from 'framer-motion';
import Link from 'next/link';
import { Heart, Trash2, ShoppingBag, ChevronRight } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { useWishlist } from '@/context/WishlistContext';
import { useCart } from '@/context/CartContext';
import { createStaggerTransition } from '@/motion';
import { safeImageSrc } from '@/lib/imageFallback';

export default function Wishlist() {
    const { items, removeFromWishlist, clearWishlist } = useWishlist();
    const { addToCart } = useCart();

    const handleAddToCart = (product: typeof items[0]) => {
        addToCart(product, 1, product.sizes[0], product.colors[0]);
        removeFromWishlist(product.id);
    };

    if (items.length === 0) {
        return (
            <MainLayout>
                <div className="min-h-[70vh] flex items-center justify-center">
                    <motion.div
                        className="text-center max-w-md"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-muted flex items-center justify-center">
                            <Heart className="h-12 w-12 text-muted-foreground" />
                        </div>
                        <h1 className="text-2xl font-display font-semibold mb-3">Your wishlist is empty</h1>
                        <p className="text-muted-foreground mb-8">
                            Save items you love by clicking the heart icon on any product. They'll appear here for easy access.
                        </p>
                        <Button variant="hero" size="lg" asChild>
                            <Link href="/discover">
                                Explore Products
                                <ChevronRight className="h-4 w-4 ml-2" />
                            </Link>
                        </Button>
                    </motion.div>
                </div>
            </MainLayout>
        );
    }

    return (
        <MainLayout>
            <div className="container py-8">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-2xl md:text-3xl font-display font-semibold">My Wishlist</h1>
                        <p className="text-muted-foreground">{items.length} saved items</p>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={clearWishlist}
                        className="text-destructive hover:text-destructive"
                    >
                        Clear All
                    </Button>
                </div>

                {/* Wishlist Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                    {items.map((product, index) => (
                        <motion.div
                            key={product.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={createStaggerTransition(index)}
                            className="group"
                        >
                            {/* Product Image */}
                            <Link href={`/product/${product.id}`} className="block relative aspect-[3/4] mb-4 overflow-hidden rounded-lg bg-muted">
                                <img
                                    src={safeImageSrc(product.images?.[0])}
                                    alt={product.name}
                                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                                    onError={(e) => {
                                        e.currentTarget.src = safeImageSrc('');
                                    }}
                                    loading="lazy"
                                />

                                {/* Overlay Actions */}
                                <div className="absolute inset-0 bg-charcoal/0 group-hover:bg-charcoal/20 transition-colors duration-300" />

                                {/* Remove Button */}
                                <button
                                    className="absolute top-3 right-3 w-9 h-9 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:scale-110"
                                    aria-label="Remove from wishlist"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        removeFromWishlist(product.id);
                                    }}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>

                                {/* Sale Badge */}
                                {product.originalPrice && (
                                    <span className="absolute top-3 left-3 bg-destructive text-destructive-foreground text-xs font-semibold px-2 py-1 rounded">
                                        SALE
                                    </span>
                                )}

                                {/* Quick Add to Cart */}
                                <div className="absolute bottom-3 left-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Button
                                        variant="gold"
                                        size="sm"
                                        className="w-full text-xs"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            handleAddToCart(product);
                                        }}
                                    >
                                        <ShoppingBag className="h-3 w-3 mr-1" />
                                        Add to Cart
                                    </Button>
                                </div>
                            </Link>

                            {/* Product Info */}
                            <Link href={`/product/${product.id}`} className="block space-y-1">
                                <p className="text-label text-muted-foreground">{product.brand}</p>
                                <h3 className="font-medium text-foreground group-hover:text-accent transition-colors line-clamp-1">
                                    {product.name}
                                </h3>
                                <div className="flex items-center gap-2">
                                    <span className="font-semibold text-foreground">
                                        ${product.price}
                                    </span>
                                    {product.originalPrice && (
                                        <span className="text-sm text-muted-foreground line-through">
                                            ${product.originalPrice}
                                        </span>
                                    )}
                                </div>

                                {/* Style Score */}
                                <div className="flex items-center gap-1 pt-1">
                                    <progress
                                        className="style-score"
                                        value={product.styleCompatibility}
                                        max={100}
                                        aria-label={`${product.styleCompatibility}% style match`}
                                    />
                                    <span className="text-xs text-muted-foreground">
                                        {product.styleCompatibility}% match
                                    </span>
                                </div>
                            </Link>
                        </motion.div>
                    ))}
                </div>

                {/* Continue Shopping */}
                <div className="mt-12 text-center">
                    <Button variant="outline" size="lg" asChild>
                        <Link href="/discover">
                            Continue Shopping
                            <ChevronRight className="h-4 w-4 ml-2" />
                        </Link>
                    </Button>
                </div>
            </div>
        </MainLayout>
    );
}
