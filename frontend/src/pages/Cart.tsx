import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { toast } from "sonner";
import {
    ShoppingBag,
    Trash2,
    Plus,
    Minus,
    ArrowLeft,
    Tag,
    Truck,
    Shield,
    ChevronRight
} from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { useCart } from '@/context/CartContext';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';
import { safeImageSrc } from '@/lib/imageFallback';

export default function Cart() {
    const router = useRouter();
    const { items, updateQuantity, removeFromCart, getCartTotal, getCartCount, clearCart } = useCart();

    // Promo Code State
    const [promoCode, setPromoCode] = useState('');
    const [discount, setDiscount] = useState(0);

    const subtotal = getCartTotal();
    const shipping = subtotal >= 100 ? 0 : 5.99;

    const calculateTax = () => {
        return (subtotal - discount) * 0.08;
    };

    const tax = calculateTax();
    const total = subtotal - discount + shipping + tax;


    // ...

    const handleApplyPromo = () => {
        if (promoCode.trim().toUpperCase() === 'CONFIT10') {
            // 10% discount
            const discAmount = subtotal * 0.10;
            setDiscount(discAmount);
            toast.success('Promo code applied!', {
                description: 'You saved 10% on your order.'
            });
        } else {
            toast.error('Invalid promo code', {
                description: 'Please try using "CONFIT10"'
            });
            setDiscount(0);
        }
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
                            <ShoppingBag className="h-12 w-12 text-muted-foreground" />
                        </div>
                        <h1 className="text-2xl font-display font-semibold mb-3">Your cart is empty</h1>
                        <p className="text-muted-foreground mb-8">
                            Looks like you haven't added any items to your cart yet. Start shopping to find your perfect style!
                        </p>
                        <Button variant="hero" size="lg" asChild>
                            <Link href="/discover">
                                Start Shopping
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
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" onClick={() => router.back()}>
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                        <div>
                            <h1 className="text-2xl md:text-3xl font-display font-semibold">Shopping Cart</h1>
                            <p className="text-muted-foreground">{getCartCount()} items in your cart</p>
                        </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={clearCart} className="text-destructive hover:text-destructive">
                        Clear Cart
                    </Button>
                </div>

                <div className="grid lg:grid-cols-3 gap-8">
                    {/* Cart Items */}
                    <div className="lg:col-span-2 space-y-4">
                        {items.map((item, index) => (
                            <motion.div
                                key={`${item.product.id}-${item.size}-${item.color}`}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={createTransition({ delay: index * 0.1 })}
                                className="flex gap-4 p-4 bg-card rounded-xl border border-border"
                            >
                                {/* Product Image */}
                                <Link
                                    href={`/product/${item.product.id}`}
                                    className="shrink-0 w-24 h-28 md:w-28 md:h-36 rounded-lg overflow-hidden bg-muted"
                                >
                                    <img
                                        src={safeImageSrc(item.product.images?.[0])}
                                        alt={item.product.name}
                                        className="w-full h-full object-cover hover:scale-105 transition-transform"
                                    />
                                </Link>

                                {/* Product Info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between gap-2 mb-2">
                                        <div>
                                            <p className="text-sm text-muted-foreground">{item.product.brand}</p>
                                            <Link
                                                href={`/product/${item.product.id}`}
                                                className="font-medium hover:text-accent transition-colors line-clamp-1"
                                            >
                                                {item.product.name}
                                            </Link>
                                        </div>
                                        <button
                                            onClick={() => removeFromCart(item.product.id, item.size, item.color)}
                                            className="shrink-0 w-8 h-8 rounded-full hover:bg-destructive/10 flex items-center justify-center text-muted-foreground hover:text-destructive transition-colors"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </div>

                                    <div className="flex flex-wrap gap-2 text-sm text-muted-foreground mb-3">
                                        <span className="px-2 py-0.5 bg-muted rounded">Size: {item.size}</span>
                                        <span className="px-2 py-0.5 bg-muted rounded">Color: {item.color}</span>
                                    </div>

                                    <div className="flex items-center justify-between">
                                        {/* Quantity Controls */}
                                        <div className="flex items-center border border-border rounded-lg overflow-hidden">
                                            <button
                                                onClick={() => updateQuantity(item.product.id, item.size, item.color, item.quantity - 1)}
                                                className="w-8 h-8 flex items-center justify-center hover:bg-muted transition-colors"
                                            >
                                                <Minus className="h-3 w-3" />
                                            </button>
                                            <span className="w-10 text-center text-sm font-medium">{item.quantity}</span>
                                            <button
                                                onClick={() => updateQuantity(item.product.id, item.size, item.color, item.quantity + 1)}
                                                className="w-8 h-8 flex items-center justify-center hover:bg-muted transition-colors"
                                            >
                                                <Plus className="h-3 w-3" />
                                            </button>
                                        </div>

                                        {/* Price */}
                                        <div className="text-right">
                                            <p className="font-semibold">${(item.product.price * item.quantity).toFixed(2)}</p>
                                            {item.quantity > 1 && (
                                                <p className="text-sm text-muted-foreground">${item.product.price} each</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    {/* Order Summary */}
                    <div className="lg:col-span-1">
                        <div className="sticky top-24 bg-card rounded-xl border border-border p-6 space-y-6">
                            <h2 className="text-lg font-semibold">Order Summary</h2>

                            {/* Promo Code */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Promo Code</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        placeholder="Enter code (Try CONFIT10)"
                                        value={promoCode}
                                        onChange={(e) => setPromoCode(e.target.value)}
                                        className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                                    />
                                    <Button variant="outline" size="sm" onClick={handleApplyPromo}>
                                        <Tag className="h-4 w-4 mr-2" />
                                        Apply
                                    </Button>
                                </div>
                                {discount > 0 && <p className="text-xs text-green-600">Discount Applied: -${discount.toFixed(2)}</p>}
                            </div>

                            {/* Summary */}
                            <div className="space-y-3 pt-4 border-t border-border">
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Subtotal</span>
                                    <span>${subtotal.toFixed(2)}</span>
                                </div>
                                {discount > 0 && (
                                    <div className="flex justify-between text-sm text-green-600">
                                        <span>Discount</span>
                                        <span>-${discount.toFixed(2)}</span>
                                    </div>
                                )}
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Shipping</span>
                                    <span className={shipping === 0 ? 'text-accent' : ''}>
                                        {shipping === 0 ? 'Free' : `$${shipping.toFixed(2)}`}
                                    </span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Tax (8%)</span>
                                    <span>${tax.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between pt-3 border-t border-border">
                                    <span className="font-semibold">Total</span>
                                    <span className="text-xl font-semibold">${total.toFixed(2)}</span>
                                </div>
                            </div>

                            {/* Free Shipping Notice */}
                            {subtotal < 100 && (
                                <div className="p-3 bg-accent/5 border border-accent/20 rounded-lg">
                                    <p className="text-sm text-center">
                                        Add <span className="font-semibold text-accent">${(100 - subtotal).toFixed(2)}</span> more for free shipping!
                                    </p>
                                </div>
                            )}

                            {/* Checkout Button */}
                            <Button
                                variant="hero"
                                size="lg"
                                className="w-full"
                                onClick={() => router.push('/checkout')}
                            >
                                Proceed to Checkout
                                <ChevronRight className="h-4 w-4 ml-2" />
                            </Button>

                            {/* Trust Badges */}
                            <div className="grid grid-cols-2 gap-3 pt-4">
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <Truck className="h-4 w-4 text-accent" />
                                    <span>Free shipping $100+</span>
                                </div>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <Shield className="h-4 w-4 text-accent" />
                                    <span>Secure checkout</span>
                                </div>
                            </div>

                            {/* Continue Shopping */}
                            <Button variant="ghost" className="w-full" asChild>
                                <Link href="/discover">
                                    <ArrowLeft className="h-4 w-4 mr-2" />
                                    Continue Shopping
                                </Link>
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </MainLayout>
    );
}
