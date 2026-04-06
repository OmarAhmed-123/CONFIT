import { motion } from 'framer-motion';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
    ArrowLeft,
    CreditCard,
    Truck,
    MapPin,
    Check,
    Lock,
    ChevronRight,
    Package
} from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { StripePaymentModal } from '@/components/checkout/StripePaymentModal';
import { LottieStatus } from '@/components/checkout/LottieStatus';
import { useToast } from '@/hooks/use-toast';
import { useCheckoutViewModel } from '@/viewmodels/useCheckoutViewModel';

export default function Checkout() {
    const router = useRouter();
    const { toast } = useToast();

    const {
        // State
        currentStep,
        orderPlaced,
        isPlacing,
        shippingInfo,
        paymentInfo,
        deliveryMethod,
        selectedStore,
        shippingMethod,
        paymentMethod,
        bnplPlan,
        stores,
        subtotal,
        finalShipping,
        freeShipping,
        tax,
        total,
        items,

        // Setters
        setCurrentStep,
        setShippingInfo,
        setPaymentInfo,
        setDeliveryMethod,
        setSelectedStore,
        setShippingMethod,
        setPaymentMethod,

        // Actions
        submitShipping,
        submitPayment,
        editShipping,
        editPayment,
        placeOrder,

        stripeCheckout,
        setStripeCheckout,
        stripeModalOpen,
        setStripeModalOpen,
        completeStripeModalPayment,
        lastOrderNumber,
        stripeEnabled,
        paymobEnabled,
        paymobIframeReady,
        paypalEnabled,
        cardGateway,
        setCardGateway,
        paymobIframeUrl,
        dismissPaymobOverlay,
        paymentProviderError,
        clearPaymentProviderError,
    } = useCheckoutViewModel();

    const paymobOption = paymobEnabled && paymobIframeReady;
    const showGatewayPicker =
        paymentMethod === 'card' &&
        [stripeEnabled, paymobOption, paypalEnabled].filter(Boolean).length > 1;
    
    // Check if ANY payment provider is available
    const hasPaymentProvider = stripeEnabled || paymobOption || paypalEnabled;

    if (items.length === 0 && !orderPlaced) {
        return (
            <MainLayout>
                <div className="container py-16 flex flex-col items-center justify-center min-h-[50vh]">
                    <Package className="h-16 w-16 text-muted-foreground/50 mb-4" />
                    <h2 className="text-xl font-semibold mb-2">Your cart is empty</h2>
                    <p className="text-muted-foreground text-center mb-6 max-w-sm">
                        Add items from Discover or the product pages, then return here to checkout.
                    </p>
                    <div className="flex gap-3">
                        <Button variant="hero" asChild>
                            <Link href="/cart">View Cart</Link>
                        </Button>
                        <Button variant="outline" asChild>
                            <Link href="/discover">Continue Shopping</Link>
                        </Button>
                    </div>
                </div>
            </MainLayout>
        );
    }

    if (orderPlaced) {
        return (
            <MainLayout>
                <div className="min-h-[70vh] flex items-center justify-center">
                    <motion.div
                        className="text-center max-w-md"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                    >
                        <div className="mx-auto mb-4 flex justify-center">
                            <LottieStatus variant="success" className="h-28 w-28" loop={false} />
                        </div>
                        <h1 className="text-3xl font-display font-semibold mb-3">Order Confirmed!</h1>
                        <p className="text-muted-foreground mb-2">
                            Thank you for your order. Your order number is:
                        </p>
                        <p className="text-xl font-mono font-semibold text-accent mb-6">
                            #{(lastOrderNumber || '').replace(/^#/, '') || 'CONF'}
                        </p>
                        <p className="text-sm text-muted-foreground mb-8">
                            We'll send you shipping confirmation when your items are on the way.
                        </p>
                        <div className="flex gap-4 justify-center">
                            <Button variant="hero" asChild>
                                <Link href="/discover">Continue Shopping</Link>
                            </Button>
                            <Button variant="outline" asChild>
                                <Link href="/profile">View Orders</Link>
                            </Button>
                        </div>
                    </motion.div>
                </div>
            </MainLayout>
        );
    }

    const steps = [
        { id: 'shipping', label: deliveryMethod === 'pickup' ? 'Pickup' : 'Shipping', icon: deliveryMethod === 'pickup' ? MapPin : Truck },
        { id: 'payment', label: 'Payment', icon: CreditCard },
        { id: 'review', label: 'Review', icon: Package },
    ];

    return (
        <MainLayout>
            <div className="container py-8">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <Button variant="ghost" size="icon" onClick={() => router.push('/cart')}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <h1 className="text-2xl md:text-3xl font-display font-semibold">Checkout</h1>
                </div>

                {/* Progress Steps */}
                <div className="flex items-center justify-center mb-12">
                    {steps.map((step, index) => {
                        const isActive = step.id === currentStep;
                        const isCompleted = steps.findIndex(s => s.id === currentStep) > index;
                        const Icon = step.icon;
                        return (
                            <div key={step.id} className="flex items-center">
                                <div className="flex flex-col items-center">
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${isActive ? 'bg-accent text-accent-foreground' :
                                        isCompleted ? 'bg-accent/20 text-accent' :
                                            'bg-muted text-muted-foreground'
                                        }`}>
                                        {isCompleted ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                                    </div>
                                    <span className={`text-xs mt-2 ${isActive ? 'text-accent font-medium' : 'text-muted-foreground'}`}>
                                        {step.label}
                                    </span>
                                </div>
                                {index < steps.length - 1 && (
                                    <div className={`w-16 md:w-24 h-0.5 mx-2 ${isCompleted ? 'bg-accent' : 'bg-muted'}`} />
                                )}
                            </div>
                        );
                    })}
                </div>

                {paymentProviderError ? (
                    <div
                        className="mb-6 flex items-start justify-between gap-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm"
                        role="alert"
                    >
                        <span className="text-foreground/90">{paymentProviderError}</span>
                        <button
                            type="button"
                            className="shrink-0 underline text-destructive font-medium"
                            onClick={clearPaymentProviderError}
                        >
                            Dismiss
                        </button>
                    </div>
                ) : null}

                <div className="grid lg:grid-cols-3 gap-8">
                    {/* Main Form Area */}
                    <div className="lg:col-span-2">
                        {/* Shipping Form */}
                        {currentStep === 'shipping' && (
                            <motion.form
                                onSubmit={submitShipping}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="space-y-6"
                            >
                                <div className="bg-card rounded-xl border border-border p-6">
                                    <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                                        <MapPin className="h-5 w-5 text-accent" />
                                        Delivery Method
                                    </h2>

                                    {/* Delivery Toggle */}
                                    <div className="flex p-1 bg-muted rounded-lg mb-6">
                                        <button
                                            type="button"
                                            onClick={() => setDeliveryMethod('shipping')}
                                            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${deliveryMethod === 'shipping' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                                        >
                                            Ship to Home
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setDeliveryMethod('pickup')}
                                            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${deliveryMethod === 'pickup' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                                        >
                                            Pick Up In Store
                                        </button>
                                    </div>

                                    {deliveryMethod === 'pickup' ? (
                                        <div className="space-y-4">
                                            <h3 className="font-medium">Select a Store</h3>
                                            <div className="grid gap-3">
                                                {stores.map(store => (
                                                    <label key={store.id} className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer ${selectedStore === store.id ? 'border-accent bg-accent/5' : 'border-border hover:border-muted-foreground'}`}>
                                                        <input
                                                            type="radio"
                                                            name="store"
                                                            value={store.id}
                                                            checked={selectedStore === store.id}
                                                            onChange={(e) => setSelectedStore(e.target.value)}
                                                            className="mt-1 w-4 h-4 text-accent focus:ring-accent"
                                                            required
                                                        />
                                                        <div>
                                                            <p className="font-medium">{store.name}</p>
                                                            <p className="text-sm text-muted-foreground">{store.address}</p>
                                                            {store.distance ? (
                                                                <p className="text-xs text-accent mt-1">{store.distance}</p>
                                                            ) : null}
                                                            {selectedStore === store.id && (
                                                                <div className="mt-2 text-xs bg-green-100 text-green-700 px-2 py-1 rounded inline-block">
                                                                    Available for pickup today
                                                                </div>
                                                            )}
                                                        </div>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="grid md:grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-sm font-medium mb-2">First Name *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    value={shippingInfo.firstName}
                                                    onChange={e => setShippingInfo({ ...shippingInfo, firstName: e.target.value })}
                                                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                    placeholder="John"
                                                    autoComplete="given-name"
                                                    name="firstName"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-2">Last Name *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    value={shippingInfo.lastName}
                                                    onChange={e => setShippingInfo({ ...shippingInfo, lastName: e.target.value })}
                                                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                    placeholder="Doe"
                                                    autoComplete="family-name"
                                                    name="lastName"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-2">Email *</label>
                                                <input
                                                    type="email"
                                                    required
                                                    value={shippingInfo.email}
                                                    onChange={e => setShippingInfo({ ...shippingInfo, email: e.target.value })}
                                                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                    placeholder="john@example.com"
                                                    autoComplete="email"
                                                    name="email"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-2">Phone</label>
                                                <input
                                                    type="tel"
                                                    value={shippingInfo.phone}
                                                    onChange={e => setShippingInfo({ ...shippingInfo, phone: e.target.value })}
                                                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                    placeholder="+1 (555) 123-4567"
                                                    autoComplete="tel"
                                                    name="phone"
                                                />
                                            </div>
                                            <div className="md:col-span-2">
                                                <label className="block text-sm font-medium mb-2">Address *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    value={shippingInfo.address}
                                                    onChange={e => setShippingInfo({ ...shippingInfo, address: e.target.value })}
                                                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                    placeholder="Street address"
                                                    autoComplete="street-address"
                                                    name="address"
                                                />
                                            </div>
                                            <div className="md:col-span-2">
                                                <label className="block text-sm font-medium mb-2">Apartment, suite, etc.</label>
                                                <input
                                                    type="text"
                                                    value={shippingInfo.apartment}
                                                    onChange={e => setShippingInfo({ ...shippingInfo, apartment: e.target.value })}
                                                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                    placeholder="Apt 4B"
                                                    autoComplete="address-line2"
                                                    name="apartment"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-sm font-medium mb-2">City *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    value={shippingInfo.city}
                                                    onChange={e => setShippingInfo({ ...shippingInfo, city: e.target.value })}
                                                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                    placeholder="New York"
                                                    autoComplete="address-level2"
                                                    name="city"
                                                />
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium mb-2">State *</label>
                                                    <input
                                                        type="text"
                                                        required
                                                        value={shippingInfo.state}
                                                        onChange={e => setShippingInfo({ ...shippingInfo, state: e.target.value })}
                                                        className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                        placeholder="NY"
                                                        autoComplete="address-level1"
                                                        name="state"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium mb-2">ZIP *</label>
                                                    <input
                                                        type="text"
                                                        required
                                                        value={shippingInfo.zip}
                                                        onChange={e => setShippingInfo({ ...shippingInfo, zip: e.target.value })}
                                                        className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                        placeholder="10001"
                                                        autoComplete="postal-code"
                                                        name="zip"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    <label className="flex items-center gap-2 mt-4 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={shippingInfo.saveAddress}
                                            onChange={e => setShippingInfo({ ...shippingInfo, saveAddress: e.target.checked })}
                                            className="w-4 h-4 rounded border-border text-accent focus:ring-accent"
                                        />
                                        <span className="text-sm">Save this address for future orders</span>
                                    </label>
                                </div>

                                {/* Shipping Method - Only show if shipping */}
                                {deliveryMethod === 'shipping' && (
                                    <div className="bg-card rounded-xl border border-border p-6">
                                        <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                                            <Truck className="h-5 w-5 text-accent" />
                                            Shipping Method
                                        </h2>

                                        <div className="space-y-3">
                                            {[
                                                { id: 'standard', label: 'Standard Shipping', time: '5-7 business days', price: freeShipping ? 'Free' : '$5.99' },
                                                { id: 'express', label: 'Express Shipping', time: '2-3 business days', price: '$12.99' },
                                                { id: 'overnight', label: 'Overnight Shipping', time: 'Next business day', price: '$24.99' },
                                            ].map(method => (
                                                <label
                                                    key={method.id}
                                                    className={`flex items-center justify-between p-4 rounded-lg border cursor-pointer transition-colors ${shippingMethod === method.id
                                                        ? 'border-accent bg-accent/5'
                                                        : 'border-border hover:border-muted-foreground'
                                                        }`}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <input
                                                            type="radio"
                                                            name="shipping"
                                                            value={method.id}
                                                            checked={shippingMethod === method.id}
                                                            onChange={e => setShippingMethod(e.target.value)}
                                                            className="w-4 h-4 text-accent focus:ring-accent"
                                                        />
                                                        <div>
                                                            <p className="font-medium">{method.label}</p>
                                                            <p className="text-sm text-muted-foreground">{method.time}</p>
                                                        </div>
                                                    </div>
                                                    <span className={method.price === 'Free' ? 'text-accent font-medium' : 'font-medium'}>
                                                        {method.price}
                                                    </span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <Button type="submit" variant="hero" size="lg" className="w-full">
                                    Continue to Payment
                                    <ChevronRight className="h-4 w-4 ml-2" />
                                </Button>
                            </motion.form>
                        )}

                        {/* Payment Form */}
                        {currentStep === 'payment' && (
                            <motion.form
                                onSubmit={submitPayment}
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="space-y-6"
                            >
                                <div className="bg-card rounded-xl border border-border p-6">
                                    <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                                        <CreditCard className="h-5 w-5 text-accent" />
                                        Payment Details
                                    </h2>

                                    {/* Payment Method Toggle */}
                                    <div className="flex gap-4 mb-6">
                                        <label className={`flex-1 flex flex-col items-center gap-2 p-4 border rounded-xl cursor-pointer transition-all ${paymentMethod === 'card' ? 'border-accent bg-accent/5' : 'border-border hover:border-muted-foreground'}`}>
                                            <input type="radio" name="paymentMethod" value="card" checked={paymentMethod === 'card'} onChange={() => setPaymentMethod('card')} className="hidden" />
                                            <CreditCard className={`h-6 w-6 ${paymentMethod === 'card' ? 'text-accent' : 'text-muted-foreground'}`} />
                                            <span className="font-medium text-sm">Credit Card</span>
                                        </label>
                                        <label className={`flex-1 flex flex-col items-center gap-2 p-4 border rounded-xl cursor-pointer transition-all ${paymentMethod === 'bnpl' ? 'border-accent bg-accent/5' : 'border-border hover:border-muted-foreground'}`}>
                                            <input type="radio" name="paymentMethod" value="bnpl" checked={paymentMethod === 'bnpl'} onChange={() => setPaymentMethod('bnpl')} className="hidden" />
                                            <span className="font-bold text-lg leading-none">Klarna.</span>
                                            <span className="font-medium text-sm">Pay in 4</span>
                                        </label>
                                    </div>

                                    {paymentMethod === 'bnpl' ? (
                                        <div className="bg-muted/30 p-4 rounded-lg border border-border text-center">
                                            <p className="font-medium mb-2">Buy Now, Pay Later</p>
                                            {bnplPlan?.installments?.length ? (
                                                <>
                                                    <p className="text-sm text-muted-foreground mb-4">
                                                        4 interest-free payments of <span className="text-foreground font-semibold">${bnplPlan.installments[0]?.total?.toFixed(2) ?? (total / 4).toFixed(2)}</span>
                                                    </p>
                                                    <div className="flex justify-center gap-1 mb-4">
                                                        {bnplPlan.installments.slice(0, 4).map((inst, i) => (
                                                            <div key={i} className="w-16 py-2 bg-background border border-border rounded text-center">
                                                                <div className="text-[10px] text-muted-foreground">Due {i === 0 ? 'Now' : `in ${2 * i} wks`}</div>
                                                                <div className="font-medium text-xs">${(inst.total ?? total / 4).toFixed(2)}</div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </>
                                            ) : (
                                                <p className="text-sm text-muted-foreground mb-4">
                                                    Split your purchase into 4 interest-free payments of <span className="text-foreground font-semibold">${(total / 4).toFixed(2)}</span>.
                                                </p>
                                            )}
                                            <p className="text-xs text-muted-foreground">Preview only. With Stripe enabled, Klarna can be chosen in the secure payment step.</p>
                                        </div>
                                    ) : (
                                        <>
                                            {showGatewayPicker && (
                                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-6">
                                                    {stripeEnabled ? (
                                                        <button
                                                            type="button"
                                                            onClick={() => setCardGateway('stripe')}
                                                            className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${cardGateway === 'stripe' ? 'border-accent bg-accent/10' : 'border-border hover:border-muted-foreground'}`}
                                                        >
                                                            Stripe
                                                        </button>
                                                    ) : null}
                                                    {paymobOption ? (
                                                        <button
                                                            type="button"
                                                            onClick={() => setCardGateway('paymob')}
                                                            className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${cardGateway === 'paymob' ? 'border-accent bg-accent/10' : 'border-border hover:border-muted-foreground'}`}
                                                        >
                                                            Paymob
                                                        </button>
                                                    ) : null}
                                                    {paypalEnabled ? (
                                                        <button
                                                            type="button"
                                                            onClick={() => setCardGateway('paypal')}
                                                            className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${cardGateway === 'paypal' ? 'border-accent bg-accent/10' : 'border-border hover:border-muted-foreground'}`}
                                                        >
                                                            PayPal
                                                        </button>
                                                    ) : null}
                                                </div>
                                            )}

                                            {cardGateway === 'stripe' && stripeEnabled ? (
                                                <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2">
                                                    <p className="font-medium text-foreground">Stripe secure checkout</p>
                                                    <p className="text-sm text-muted-foreground leading-relaxed">
                                                        After you place the order, a secure payment form opens here in the app.
                                                        Major cards, digital wallets, and Klarna (where supported) — your card data stays with Stripe.
                                                    </p>
                                                </div>
                                            ) : null}

                                            {cardGateway === 'paymob' && paymobOption ? (
                                                <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2">
                                                    <p className="font-medium text-foreground">Paymob</p>
                                                    <p className="text-sm text-muted-foreground leading-relaxed">
                                                        After you place the order, complete payment in the secure Paymob window. We confirm your order when the payment clears.
                                                    </p>
                                                </div>
                                            ) : null}

                                            {cardGateway === 'paypal' && paypalEnabled ? (
                                                <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2">
                                                    <p className="font-medium text-foreground">PayPal</p>
                                                    <p className="text-sm text-muted-foreground leading-relaxed">
                                                        After you place the order, you’ll approve payment on PayPal and return here to finish.
                                                    </p>
                                                </div>
                                            ) : null}

                                            {/* NO PAYMENT PROVIDER CONFIGURED - Show clear message instead of fake UI */}
                                            {!hasPaymentProvider && paymentMethod === 'card' ? (
                                                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 space-y-3">
                                                    <p className="font-medium text-foreground">Payment Not Configured</p>
                                                    <p className="text-sm text-muted-foreground leading-relaxed">
                                                        No payment providers are enabled. To process real payments, configure one of:
                                                    </p>
                                                    <ul className="text-xs text-muted-foreground list-disc list-inside space-y-1">
                                                        <li><strong>Stripe:</strong> Set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY</li>
                                                        <li><strong>Paymob:</strong> Set PAYMOB_API_KEY and PAYMOB_IFRAME_ID</li>
                                                        <li><strong>PayPal:</strong> Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET</li>
                                                    </ul>
                                                    <p className="text-xs text-amber-600">
                                                        Orders can still be placed but payment will need to be arranged separately.
                                                    </p>
                                                </div>
                                            ) : null}


                                        </>
                                    )}

                                    <div className="flex items-center gap-2 mt-4 p-3 bg-muted rounded-lg">
                                        <Lock className="h-4 w-4 text-accent" />
                                        <span className="text-xs text-muted-foreground">
                                            {paymentMethod === 'card' && cardGateway === 'stripe' && stripeEnabled
                                                ? 'Payments processed by Stripe; we never store your full card details.'
                                                : paymentMethod === 'card' && cardGateway === 'paymob'
                                                  ? 'Paymob processes card data in their secure iframe.'
                                                  : paymentMethod === 'card' && cardGateway === 'paypal'
                                                    ? 'You’ll pay on PayPal’s secure site.'
                                                    : 'Your payment information is encrypted and secure'}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="lg"
                                        onClick={() => setCurrentStep('shipping')}
                                    >
                                        <ArrowLeft className="h-4 w-4 mr-2" />
                                        Back
                                    </Button>
                                    <Button type="submit" variant="hero" size="lg" className="flex-1">
                                        Review Order
                                        <ChevronRight className="h-4 w-4 ml-2" />
                                    </Button>
                                </div>
                            </motion.form>
                        )}

                        {/* Review */}
                        {currentStep === 'review' && (
                            <motion.div
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="space-y-6"
                            >
                                {/* Shipping Summary */}
                                <div className="bg-card rounded-xl border border-border p-6">
                                    <div className="flex items-center justify-between mb-4">
                                        <h2 className="text-lg font-semibold flex items-center gap-2">
                                            <MapPin className="h-5 w-5 text-accent" />
                                            {deliveryMethod === 'pickup' ? 'Pickup Location' : 'Shipping Address'}
                                        </h2>
                                        <button
                                            onClick={() => setCurrentStep('shipping')}
                                            className="text-sm text-accent hover:underline"
                                        >
                                            Edit
                                        </button>
                                    </div>
                                    {deliveryMethod === 'pickup' ? (
                                        <div className="text-muted-foreground">
                                            {selectedStore ? stores.find(s => s.id === selectedStore)?.name : 'No store selected'}
                                            <p className="text-sm">{selectedStore ? stores.find(s => s.id === selectedStore)?.address : ''}</p>
                                        </div>
                                    ) : (
                                        <p className="text-muted-foreground">
                                            {shippingInfo.firstName} {shippingInfo.lastName}<br />
                                            {shippingInfo.address}{shippingInfo.apartment && `, ${shippingInfo.apartment}`}<br />
                                            {shippingInfo.city}, {shippingInfo.state} {shippingInfo.zip}
                                        </p>
                                    )}
                                </div>

                                {/* Payment Summary */}
                                <div className="bg-card rounded-xl border border-border p-6">
                                    <div className="flex items-center justify-between mb-4">
                                        <h2 className="text-lg font-semibold flex items-center gap-2">
                                            <CreditCard className="h-5 w-5 text-accent" />
                                            Payment Method
                                        </h2>
                                        <button
                                            onClick={() => setCurrentStep('payment')}
                                            className="text-sm text-accent hover:underline"
                                        >
                                            Edit
                                        </button>
                                    </div>
                                    <p className="text-muted-foreground">
                                        {deliveryMethod === 'pickup' && stripeEnabled
                                            ? 'Stripe (card, wallets, Klarna where available)'
                                            : paymentMethod === 'bnpl'
                                              ? 'Klarna Pay in 4'
                                              : `Card ending in ${paymentInfo.cardNumber.slice(-4) || '****'}`}
                                    </p>
                                </div>

                                {/* Order Items */}
                                <div className="bg-card rounded-xl border border-border p-6">
                                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                        <Package className="h-5 w-5 text-accent" />
                                        Order Items ({items.length})
                                    </h2>
                                    <div className="space-y-4">
                                        {items.map(item => (
                                            <div key={`${item.product.id}-${item.size}-${item.color}`} className="flex gap-4">
                                                <div className="w-16 h-20 rounded-lg overflow-hidden bg-muted">
                                                    <img src={item.product.images?.[0]} alt="" className="w-full h-full object-cover" />
                                                </div>
                                                <div className="flex-1">
                                                    <p className="font-medium">{item.product.name}</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        {item.size} • {item.color} • Qty: {item.quantity}
                                                    </p>
                                                </div>
                                                <p className="font-medium">${(item.product.price * item.quantity).toFixed(2)}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="lg"
                                        onClick={() => setCurrentStep('payment')}
                                    >
                                        <ArrowLeft className="h-4 w-4 mr-2" />
                                        Back
                                    </Button>
                                    <Button
                                        variant="hero"
                                        size="lg"
                                        className="flex-1"
                                        onClick={placeOrder}
                                        disabled={
                                            isPlacing ||
                                            (deliveryMethod === 'pickup' && !selectedStore) ||
                                            Boolean(paymobIframeUrl)
                                        }
                                    >
                                        {isPlacing ? 'Placing Order…' : `Place Order • $${total.toFixed(2)}`}
                                    </Button>
                                </div>
                            </motion.div>
                        )}
                    </div>

                    {/* Order Summary Sidebar */}
                    <div className="lg:col-span-1">
                        <div className="sticky top-24 bg-card rounded-xl border border-border p-6 space-y-4">
                            <h2 className="text-lg font-semibold">Order Summary</h2>

                            {/* Items Preview */}
                            <div className="space-y-3 pb-4 border-b border-border">
                                {items.slice(0, 3).map(item => (
                                    <div key={`${item.product.id}-${item.size}`} className="flex items-center gap-3">
                                        <div className="w-12 h-14 rounded overflow-hidden bg-muted">
                                            <img src={item.product.images?.[0]} alt="" className="w-full h-full object-cover" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">{item.product.name}</p>
                                            <p className="text-xs text-muted-foreground">Qty: {item.quantity}</p>
                                        </div>
                                        <p className="text-sm font-medium">${(item.product.price * item.quantity).toFixed(2)}</p>
                                    </div>
                                ))}
                                {items.length > 3 && (
                                    <p className="text-sm text-muted-foreground text-center">
                                        +{items.length - 3} more items
                                    </p>
                                )}
                            </div>

                            {/* Totals */}
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Subtotal</span>
                                    <span>${subtotal.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Shipping</span>
                                    <span className={finalShipping === 0 ? 'text-accent' : ''}>
                                        {finalShipping === 0 ? 'Free' : `$${finalShipping.toFixed(2)}`}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Tax</span>
                                    <span>${tax.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between pt-2 border-t border-border text-base">
                                    <span className="font-semibold">Total</span>
                                    <span className="font-semibold">${total.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {paymobIframeUrl ? (
                <div className="fixed inset-0 z-50 flex flex-col bg-background/95 p-4 backdrop-blur-sm md:p-8">
                    <div className="mx-auto mb-4 flex w-full max-w-4xl items-center justify-between gap-4">
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                            <LottieStatus variant="loading" className="h-12 w-12 shrink-0" />
                            <span>Complete payment below. We’ll confirm when Paymob reports success.</span>
                        </div>
                        <Button type="button" variant="outline" size="sm" onClick={dismissPaymobOverlay}>
                            Hide window
                        </Button>
                    </div>
                    <iframe
                        title="Paymob checkout"
                        src={paymobIframeUrl}
                        className="mx-auto min-h-[min(70vh,560px)] w-full max-w-4xl flex-1 rounded-lg border border-border bg-white"
                        allow="payment *"
                    />
                </div>
            ) : null}

            <StripePaymentModal
                open={stripeModalOpen}
                onOpenChange={(o) => {
                    setStripeModalOpen(o);
                    if (!o) setStripeCheckout(null);
                }}
                payload={stripeCheckout}
                onPaid={completeStripeModalPayment}
                onError={(m) =>
                    toast({ title: 'Payment', description: m, variant: 'destructive' })
                }
            />
        </MainLayout>
    );
}
