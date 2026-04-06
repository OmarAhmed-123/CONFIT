/**
 * CONFIT — useCheckoutViewModel
 * Encapsulates all checkout flow state: steps (shipping -> payment -> review), forms, BNPL, and order placement.
 * Used by: Checkout page.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useCart } from '@/context/CartContext';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';
import type { StripePaymentPayload } from '@/components/checkout/StripePaymentModal';
import { loadStripe } from '@stripe/stripe-js';
import { NotificationService, type TransactionData, type TransactionItem } from '@/services/NotificationService';

export type CheckoutStep = 'shipping' | 'payment' | 'review';

/** Card checkout processor (unified session + legacy Stripe Element). */
export type CardGateway = 'stripe' | 'paymob' | 'paypal';

export interface ShippingInfo {
    firstName: string;
    lastName: string;
    email: string;
    phone: string;
    address: string;
    apartment: string;
    city: string;
    state: string;
    zip: string;
    country: string;
    saveAddress: boolean;
}

export interface PaymentInfo {
    cardNumber: string;
    cardName: string;
    expiry: string;
    cvc: string;
    saveCard: boolean;
}

export interface BnplInstallment {
    total: number;
}

export interface BnplPlan {
    installments: BnplInstallment[];
}

// Commerce intelligence types
export interface PurchaseConfidence {
    overall_score: number;
    dimensions: {
        style_alignment: number;
        budget_fit: number;
        size_confidence: number;
        brand_affinity: number;
        occasion_match: number;
        return_risk: number;
    };
    recommendations: string[];
    confidence_level: 'high' | 'medium' | 'low' | 'very_low';
}

export interface DeliveryRecommendation {
    recommended_method: string;
    alternatives: Array<{
        method: string;
        cost: number;
        days: string;
        eco_impact: number;
        score_diff: number;
    }>;
    estimated_arrival: string;
    cost: number;
    eco_impact: number;
    reason: string;
}

export interface FraudAssessment {
    risk_score: number;
    risk_level: 'low' | 'medium' | 'high' | 'critical';
    factors: Array<{ type: string; score: number; detail: string }>;
    recommendations: string[];
    requires_3ds: boolean;
    requires_review: boolean;
    block_transaction: boolean;
}

export interface BnplEligibility {
    eligible: boolean;
    review_required: boolean;
    confidence_score: number;
    risk_score: number;
    order_value_ok: boolean;
    max_installments: number;
    reason: string;
}

const DEFAULT_SHIPPING: ShippingInfo = {
    firstName: '', lastName: '', email: '', phone: '',
    address: '', apartment: '', city: '', state: '', zip: '',
    country: 'United States', saveAddress: true,
};

const DEFAULT_PAYMENT: PaymentInfo = {
    cardNumber: '', cardName: '', expiry: '', cvc: '', saveCard: false,
};

export interface PickupStoreOption {
    id: string;
    name: string;
    address: string;
    city?: string;
    state?: string;
    zip_code?: string;
    distance?: string; // derived from backend distance_km (or undefined when backend doesn't provide it)
}

export function useCheckoutViewModel() {
    const router = useRouter();
    const { items, getCartTotal, clearCart, trackCartEvent } = useCart();
    const { user } = useAuth();
    const { toast } = useToast();

    // ── State ──────────────────────────────────────────────────────
    const [currentStep, setCurrentStep] = useState<CheckoutStep>('shipping');
    const [orderPlaced, setOrderPlaced] = useState(false);
    const [isPlacing, setIsPlacing] = useState(false);

    const [shippingInfo, setShippingInfo] = useState<ShippingInfo>(DEFAULT_SHIPPING);
    const [paymentInfo, setPaymentInfo] = useState<PaymentInfo>(DEFAULT_PAYMENT);

    const [deliveryMethod, setDeliveryMethod] = useState<'shipping' | 'pickup'>('shipping');
    const [selectedStore, setSelectedStore] = useState('');
    const [shippingMethod, setShippingMethod] = useState('standard');

    const [stores, setStores] = useState<PickupStoreOption[]>([]);

    const [paymentMethod, setPaymentMethod] = useState<'card' | 'bnpl'>('card');
    const [bnplPlan, setBnplPlan] = useState<BnplPlan | null>(null);

    /** Pickup + Stripe: show Payment Element modal after order is created */
    const [stripeCheckout, setStripeCheckout] = useState<StripePaymentPayload | null>(null);
    const [stripeModalOpen, setStripeModalOpen] = useState(false);
    const [lastOrderNumber, setLastOrderNumber] = useState<string | null>(null);
    const [stripeEnabled, setStripeEnabled] = useState(false);
    const [paymobEnabled, setPaymobEnabled] = useState(false);
    const [paymobIframeReady, setPaymobIframeReady] = useState(false);
    const [paypalEnabled, setPaypalEnabled] = useState(false);
    const [cardGateway, setCardGateway] = useState<CardGateway>('stripe');
    const [paymobIframeUrl, setPaymobIframeUrl] = useState<string | null>(null);
    const [paymobPollingOrderId, setPaymobPollingOrderId] = useState<string | null>(null);
    const [paymentProviderError, setPaymentProviderError] = useState<string | null>(null);
    const stripeHandledRedirect = useRef(false);
    const paypalHandledRef = useRef(false);
    
    // Commerce intelligence state
    const [purchaseConfidence, setPurchaseConfidence] = useState<PurchaseConfidence | null>(null);
    const [deliveryRecommendation, setDeliveryRecommendation] = useState<DeliveryRecommendation | null>(null);
    const [bnplEligibility, setBnplEligibility] = useState<BnplEligibility | null>(null);
    const [isLoadingIntelligence, setIsLoadingIntelligence] = useState(false);

    // ── Derived totals ─────────────────────────────────────────────
    const subtotal = getCartTotal();
    const shippingCost =
        shippingMethod === 'express' ? 12.99 :
            shippingMethod === 'overnight' ? 24.99 : 5.99;
    const freeShipping = subtotal >= 100;
    const finalShipping =
        deliveryMethod === 'pickup' ? 0 :
            (freeShipping && shippingMethod === 'standard' ? 0 : shippingCost);
    const tax = subtotal * 0.08;
    const total = subtotal + finalShipping + tax;

    // ── Fetch BNPL plan when needed ────────────────────────────────
    useEffect(() => {
        if (paymentMethod !== 'bnpl' || total <= 0) {
            setBnplPlan(null);
            return;
        }
        fetch(apiUrl('/api/payments/bnpl/plan'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ total_amount: total, installments: 4, annual_interest_rate: 0, currency: 'USD' }),
        })
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => setBnplPlan(data))
            .catch(() => setBnplPlan(null));
    }, [paymentMethod, total]);

    const confirmPickupPayment = useCallback(
        async (orderId: string, paymentIntentId: string | undefined, token: string) => {
            const confirmRes = await fetch(apiUrl('/api/payments/confirm'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Idempotency-Key': `confirm-${orderId}-${Date.now()}`,
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    order_id: orderId,
                    orderId,
                    payment_success: true,
                    ...(paymentIntentId ? { payment_intent_id: paymentIntentId } : {}),
                }),
            });
            if (!confirmRes.ok) {
                const confirmBody = await confirmRes.json().catch(() => ({}));
                throw new Error(
                    typeof confirmBody?.detail === 'string'
                        ? confirmBody.detail
                        : `Confirm failed (${confirmRes.status})`,
                );
            }
            const confirmBodyRaw: Record<string, unknown> = await confirmRes.json().catch(() => ({}));
            const confirmOk =
                confirmBodyRaw?.success === true ||
                (confirmBodyRaw?.ok === true &&
                    (confirmBodyRaw?.paymentStatus === 'CONFIRMED' ||
                        confirmBodyRaw?.payment_status === 'CONFIRMED'));
            const confirmedOrderId =
                (confirmBodyRaw?.order_id as string | undefined) ??
                (confirmBodyRaw?.orderId as string | undefined) ??
                (confirmBodyRaw?.order as { id?: string } | undefined)?.id;
            if (!confirmOk || String(confirmedOrderId ?? '') !== String(orderId)) {
                throw new Error('Payment confirmation failed.');
            }
        },
        [],
    );

    // ── Stripe redirect return (Klarna / 3DS) ───────────────────────
    useEffect(() => {
        if (stripeHandledRedirect.current) return;
        const params = new URLSearchParams(window.location.search);
        const clientSecret = params.get('payment_intent_client_secret');
        if (!clientSecret || !params.get('payment_intent')) return;

        stripeHandledRedirect.current = true;
        const token = getAuthToken() || '';
        const raw = sessionStorage.getItem('stripe_checkout');
        if (!raw) return;

        void (async () => {
            try {
                const { publishableKey, orderId, orderNumber } = JSON.parse(raw) as {
                    publishableKey: string;
                    orderId: string;
                    orderNumber?: string;
                };
                const stripe = await loadStripe(publishableKey);
                if (!stripe) return;
                const { paymentIntent } = await stripe.retrievePaymentIntent(clientSecret);
                if (paymentIntent?.status === 'succeeded' && paymentIntent.id) {
                    window.history.replaceState({}, '', `${window.location.pathname}${window.location.hash}`);
                    await confirmPickupPayment(orderId, paymentIntent.id, token);
                    setLastOrderNumber(String(orderNumber ?? orderId));
                    setOrderPlaced(true);
                    sessionStorage.removeItem('stripe_checkout');
                    clearCart();
                }
            } catch (e) {
                console.error('Stripe redirect handling failed:', e);
            }
        })();
    }, [clearCart, confirmPickupPayment]);

    // PayPal Orders v2 return: ?paypal_done=1&token=<paypal_order_id>
    useEffect(() => {
        if (paypalHandledRef.current) return;
        const q = new URLSearchParams(window.location.search);
        if (q.get('paypal_cancel') === '1') {
            paypalHandledRef.current = true;
            window.history.replaceState({}, '', `${window.location.pathname}${window.location.hash}`);
            toast({
                title: 'Checkout cancelled',
                description: 'You cancelled the PayPal payment.',
                variant: 'destructive',
            });
            return;
        }
        if (q.get('paypal_done') !== '1') return;
        const paypalOrderId = q.get('token');
        if (!paypalOrderId) return;
        paypalHandledRef.current = true;
        const raw = sessionStorage.getItem('paypal_checkout');
        sessionStorage.removeItem('paypal_checkout');
        window.history.replaceState({}, '', `${window.location.pathname}${window.location.hash}`);

        void (async () => {
            let orderNum: string | undefined;
            if (raw) {
                try {
                    const p = JSON.parse(raw) as { orderNumber?: string };
                    orderNum = p.orderNumber;
                } catch {
                    /* ignore */
                }
            }
            const token = getAuthToken() || '';
            if (!token) {
                toast({
                    title: 'Sign in required',
                    description: 'Log in to complete PayPal capture.',
                    variant: 'destructive',
                });
                return;
            }
            try {
                const r = await fetch(apiUrl('/api/payments/unified/paypal/capture'), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ paypal_order_id: paypalOrderId }),
                });
                const body = await r.json().catch(() => ({}));
                if (!r.ok) {
                    throw new Error(
                        typeof body?.detail === 'string' ? body.detail : `Capture failed (${r.status})`,
                    );
                }
                if (body?.success === true) {
                    setLastOrderNumber(String(orderNum ?? ''));
                    setOrderPlaced(true);
                    clearCart();
                } else {
                    toast({
                        title: 'PayPal not completed',
                        description: String(body?.status ?? 'Try again.'),
                        variant: 'destructive',
                    });
                }
            } catch (e) {
                toast({
                    title: 'PayPal capture failed',
                    description: e instanceof Error ? e.message : 'Try again.',
                    variant: 'destructive',
                });
            }
        })();
    }, [clearCart, toast]);

    // Paymob: poll order until webhook marks payment success/failed
    useEffect(() => {
        if (!paymobPollingOrderId) return;
        const token = getAuthToken() || '';
        let cancelled = false;
        const started = Date.now();

        const tick = async () => {
            if (cancelled) return;
            try {
                const r = await fetch(apiUrl(`/api/orders/${paymobPollingOrderId}`), {
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                if (!r.ok || cancelled) return;
                const j = await r.json().catch(() => ({}));
                const st = (j?.order?.payment_status ?? j?.order?.paymentStatus) as string | undefined;
                if (st === 'success') {
                    setOrderPlaced(true);
                    setPaymobIframeUrl(null);
                    setPaymobPollingOrderId(null);
                    setPaymentProviderError(null);
                    clearCart();
                    return;
                }
                if (st === 'failed') {
                    setPaymentProviderError('Payment was declined or failed.');
                    setPaymobPollingOrderId(null);
                    setPaymobIframeUrl(null);
                }
            } catch {
                /* transient */
            }
        };

        const id = setInterval(() => void tick(), 2500);
        void tick();
        const maxTimer = window.setTimeout(() => {
            if (cancelled) return;
            if (Date.now() - started >= 180000) {
                setPaymentProviderError(
                    'Payment is still processing. Check your orders page or try again.',
                );
            }
        }, 180000);

        return () => {
            cancelled = true;
            clearInterval(id);
            window.clearTimeout(maxTimer);
        };
    }, [paymobPollingOrderId, clearCart]);

    useEffect(() => {
        fetch(apiUrl('/api/payments/config'))
            .then((r) => (r.ok ? r.json() : null))
            .then((c) => {
                const se = Boolean(c?.stripe_enabled && c?.publishable_key);
                setStripeEnabled(se);
                const pe = Boolean(c?.paypal_enabled);
                const pme = Boolean(c?.paymob_enabled);
                const pmifr = Boolean(c?.paymob_iframe_ready);
                setPaypalEnabled(pe);
                setPaymobEnabled(pme);
                setPaymobIframeReady(pmifr);
                if (se) setCardGateway('stripe');
                else if (pe) setCardGateway('paypal');
                else if (pme) setCardGateway('paymob');
            })
            .catch(() => {
                setStripeEnabled(false);
                setPaymobEnabled(false);
                setPaymobIframeReady(false);
                setPaypalEnabled(false);
            });
    }, []);

    // ── Fetch pickup stores (real DB data) ─────────────────────────
    useEffect(() => {
        let cancelled = false;
        const controller = new AbortController();

        const fetchStores = async () => {
            try {
                const res = await fetch(apiUrl('/api/stores'), { signal: controller.signal });
                if (!res.ok) return;
                const data = await res.json();
                if (cancelled) return;

                const mapped: PickupStoreOption[] = (Array.isArray(data) ? data : []).map((s: any) => {
                    const distanceKm = typeof s?.distance_km === 'number' ? s.distance_km : undefined;
                    return {
                        id: String(s.id),
                        name: String(s.name ?? ''),
                        address: String(s.address ?? ''),
                        city: s.city != null ? String(s.city) : undefined,
                        state: s.state != null ? String(s.state) : undefined,
                        zip_code: s.postal_code != null ? String(s.postal_code) : (s.zip_code != null ? String(s.zip_code) : undefined),
                        distance: typeof distanceKm === 'number'
                            ? `${(distanceKm * 0.621371).toFixed(1)} miles`
                            : (typeof s?.distance === 'string' ? s.distance : undefined),
                    };
                });

                setStores(mapped);
            } catch {
                // Keep UX resilient: if stores fail to load, pickup selection UI will simply be empty/disabled.
                if (!cancelled) setStores([]);
            }
        };

        fetchStores();
        return () => {
            cancelled = true;
            controller.abort();
        };
    }, []);
    
    // ── Fetch commerce intelligence (once per dependency change; avoid isLoading in deps → infinite loop) ──
    useEffect(() => {
        if (items.length === 0) return;

        const token = getAuthToken();
        if (!token) return;

        let cancelled = false;
        setIsLoadingIntelligence(true);

        const fetchIntelligence = async () => {
            try {
                const orderItems = items.map(item => ({
                    productId: item.product.id,
                    name: item.product.name,
                    price: item.product.price,
                    quantity: item.quantity,
                    category: item.product.category,
                    brand: item.product.brand,
                    color: item.color,
                    size: item.size,
                }));

                const [confidenceRes, deliveryRes, bnplRes] = await Promise.all([
                    fetch(apiUrl('/api/commerce/confidence/calculate'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`,
                        },
                        body: JSON.stringify({ items: orderItems }),
                    }),
                    fetch(apiUrl('/api/commerce/delivery/recommend'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`,
                        },
                        body: JSON.stringify({
                            order_total: subtotal,
                            items: orderItems,
                            user_context: { shipping_address: shippingInfo },
                        }),
                    }),
                    fetch(apiUrl('/api/commerce/bnpl/check-eligibility'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`,
                        },
                        body: JSON.stringify({ order_total: total }),
                    }),
                ]);

                if (cancelled) return;

                if (confidenceRes.ok) {
                    const data = await confidenceRes.json();
                    setPurchaseConfidence(data);
                }

                if (deliveryRes.ok) {
                    const data = await deliveryRes.json();
                    setDeliveryRecommendation(data);
                }

                if (bnplRes.ok) {
                    const data = await bnplRes.json();
                    setBnplEligibility(data);
                }
            } catch (error) {
                console.error('Failed to fetch commerce intelligence:', error);
            } finally {
                if (!cancelled) setIsLoadingIntelligence(false);
            }
        };

        fetchIntelligence();
        return () => {
            cancelled = true;
        };
    }, [items]);
    
    // Track checkout start event
    useEffect(() => {
        trackCartEvent('checkout_start');
    }, [trackCartEvent]);

    // ── Guard: redirect to cart when empty ────────────────────────
    useEffect(() => {
        if (items.length === 0 && !orderPlaced) {
            router.replace('/cart');
        }
    }, [items, orderPlaced, router]);

    // ── Step navigation ────────────────────────────────────────────
    const submitShipping = useCallback((e: React.FormEvent) => {
        e.preventDefault();
        setCurrentStep('payment');
    }, []);

    const submitPayment = useCallback((e: React.FormEvent) => {
        e.preventDefault();
        setCurrentStep('review');
    }, []);

    const editShipping = useCallback(() => setCurrentStep('shipping'), []);
    const editPayment = useCallback(() => setCurrentStep('payment'), []);

    const completeStripeModalPayment = useCallback(
        async (paymentIntentId: string) => {
            const token = getAuthToken() || '';
            if (!stripeCheckout) return;
            try {
                await confirmPickupPayment(stripeCheckout.orderId, paymentIntentId, token);
                setOrderPlaced(true);
                setStripeModalOpen(false);
                setStripeCheckout(null);
                sessionStorage.removeItem('stripe_checkout');
                clearCart();
            } catch (e) {
                toast({
                    title: 'Payment confirmation failed',
                    description: e instanceof Error ? e.message : 'Try again.',
                    variant: 'destructive',
                });
            }
        },
        [stripeCheckout, clearCart, confirmPickupPayment, toast],
    );

    // ── Place order ────────────────────────────────────────────────
    const placeOrder = useCallback(async () => {
        setIsPlacing(true);
        try {
            const token = getAuthToken() || '';
            const isPickup = deliveryMethod === 'pickup';
            const pickupStore = isPickup ? stores.find((s) => s.id === selectedStore) : null;

            // Backend requires shippingAddress.name/address/city to be non-empty
            // (ShippingAddressRequest has min_length=1 for those fields).
            const shippingName = isPickup
                ? `${(shippingInfo.firstName || '').trim()} ${(shippingInfo.lastName || '').trim()}`.trim() || 'Pickup Customer'
                : `${(shippingInfo.firstName || '').trim()} ${(shippingInfo.lastName || '').trim()}`.trim();

            const shippingAddressLine = isPickup
                ? (pickupStore?.address || '').trim() || 'Pickup Address'
                : `${shippingInfo.address || ''}${shippingInfo.apartment ? `, ${shippingInfo.apartment}` : ''}`.trim();

            const shippingCity = isPickup
                ? (pickupStore?.city || shippingInfo.city || '').trim() || 'Pickup City'
                : (shippingInfo.city || '').trim();

            const shippingState = isPickup
                ? (pickupStore?.state || shippingInfo.state || '').trim()
                : (shippingInfo.state || '').trim();

            const shippingZip = isPickup
                ? (pickupStore?.zip_code || shippingInfo.zip || '').trim()
                : (shippingInfo.zip || '').trim();

            const orderItems = items.map((item) => ({
                productId: String(item.product.id ?? ''),
                name: String(item.product.name ?? ''),
                // Backend expects a string; sanitize to avoid Pydantic 422 errors.
                brand: item.product.brand == null ? "" : String(item.product.brand),
                price: Number(item.product.price ?? 0),
                quantity:
                    Number.isFinite(item.quantity) && Math.round(item.quantity) > 0 ? Math.round(item.quantity) : 1,
                size: String(item.size ?? ''),
                image: String(item.product.images?.[0] ?? ''),
            }));

            // Small retry for transient dev-server/proxy drops.
            let response: Response | null = null;
            for (let attempt = 0; attempt < 3; attempt++) {
                try {
                    response = await fetch(apiUrl('/api/orders'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(token ? { Authorization: `Bearer ${token}` } : {}),
                        },
                        body: JSON.stringify({
                            items: orderItems,
                            shippingAddress: {
                            name: shippingName,
                            address: shippingAddressLine,
                            city: shippingCity,
                            state: shippingState,
                            zip: shippingZip,
                                country: shippingInfo.country?.trim() || 'US',
                            },
                            paymentMethod,
                            deliveryMethod,
                            pickupStoreId: isPickup ? selectedStore : undefined,
                            pickupTime: isPickup
                                ? new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString()
                                : undefined,
                        }),
                    });
                    break;
                } catch (e) {
                    if (attempt === 2) throw e;
                    await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
                }
            }

            if (!response) {
                throw new Error('Order request failed with no response');
            }

            if (response.ok) {
                const orderBody: any = await response.json().catch(() => ({}));
                const orderId: string | undefined = orderBody?.order?.id;
                const orderNumberStr = String(
                    orderBody?.order?.order_number ?? orderBody?.order?.id ?? '',
                );

                const cfgRes = await fetch(apiUrl('/api/payments/config'));
                const cfg = cfgRes.ok ? await cfgRes.json().catch(() => ({})) : {};
                const stripeReady = Boolean(cfg?.stripe_enabled && cfg?.publishable_key);
                const paymobOk = Boolean(cfg?.paymob_enabled && cfg?.paymob_iframe_ready);
                const paypalOk = Boolean(cfg?.paypal_enabled);
                const payWithCard = paymentMethod === 'card';

                if (payWithCard && orderId && cardGateway === 'paymob') {
                    if (!paymobOk) {
                        toast({
                            title: 'Paymob unavailable',
                            description: 'Paymob is not configured or iframe id is missing on the server.',
                            variant: 'destructive',
                        });
                        return;
                    }
                    if (!token) {
                        toast({
                            title: 'Sign in required',
                            description: 'Log in to pay with Paymob.',
                            variant: 'destructive',
                        });
                        return;
                    }
                    setPaymentProviderError(null);
                    const country = (shippingInfo.country || '').trim();
                    const billingCurrency =
                        country.toLowerCase().includes('egypt') || country === 'EG' ? 'EGP' : 'USD';
                    const unifiedRes = await fetch(apiUrl('/api/payments/unified/session'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`,
                            'X-Idempotency-Key': `paymob-${orderId}`,
                        },
                        body: JSON.stringify({
                            order_id: orderId,
                            provider: 'paymob',
                            billing: {
                                email: shippingInfo.email || 'na@confit.local',
                                first_name: shippingInfo.firstName || 'Customer',
                                last_name: shippingInfo.lastName || 'CONFIT',
                                phone_number: shippingInfo.phone || '+10000000000',
                                street: shippingAddressLine,
                                city: shippingCity,
                                state: shippingState || 'NA',
                                postal_code: shippingZip || '00000',
                                country: country.length === 2 ? country : 'US',
                                apartment: shippingInfo.apartment || 'NA',
                                floor: 'NA',
                                building: 'NA',
                                currency: billingCurrency,
                            },
                        }),
                    });
                    if (!unifiedRes.ok) {
                        const errBody = await unifiedRes.json().catch(() => ({}));
                        toast({
                            title: 'Paymob session failed',
                            description:
                                typeof errBody?.detail === 'string'
                                    ? errBody.detail
                                    : `Request failed (${unifiedRes.status})`,
                            variant: 'destructive',
                        });
                        return;
                    }
                    const sess = await unifiedRes.json();
                    const iframeUrl = sess.iframe_url as string | undefined | null;
                    if (!iframeUrl) {
                        toast({
                            title: 'Paymob iframe not configured',
                            description: 'Set PAYMOB_IFRAME_ID in server environment.',
                            variant: 'destructive',
                        });
                        return;
                    }
                    setPaymobIframeUrl(iframeUrl);
                    setPaymobPollingOrderId(orderId);
                    setLastOrderNumber(orderNumberStr);
                    return;
                }

                if (payWithCard && orderId && cardGateway === 'paypal') {
                    if (!paypalOk) {
                        toast({
                            title: 'PayPal unavailable',
                            description: 'PayPal client credentials are not configured on the server.',
                            variant: 'destructive',
                        });
                        return;
                    }
                    if (!token) {
                        toast({
                            title: 'Sign in required',
                            description: 'Log in to pay with PayPal.',
                            variant: 'destructive',
                        });
                        return;
                    }
                    const base = `${window.location.origin}${window.location.pathname}`;
                    const unifiedRes = await fetch(apiUrl('/api/payments/unified/session'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`,
                            'X-Idempotency-Key': `paypal-${orderId}`,
                        },
                        body: JSON.stringify({
                            order_id: orderId,
                            provider: 'paypal',
                            paypal_return_url: `${base}?paypal_done=1`,
                            paypal_cancel_url: `${base}?paypal_cancel=1`,
                        }),
                    });
                    if (!unifiedRes.ok) {
                        const errBody = await unifiedRes.json().catch(() => ({}));
                        toast({
                            title: 'PayPal session failed',
                            description:
                                typeof errBody?.detail === 'string'
                                    ? errBody.detail
                                    : `Request failed (${unifiedRes.status})`,
                            variant: 'destructive',
                        });
                        return;
                    }
                    const sess = await unifiedRes.json();
                    const approve = sess.approve_url as string | undefined | null;
                    if (!approve) {
                        toast({
                            title: 'PayPal',
                            description: 'No approval URL returned.',
                            variant: 'destructive',
                        });
                        return;
                    }
                    sessionStorage.setItem(
                        'paypal_checkout',
                        JSON.stringify({
                            orderId,
                            orderNumber: orderBody?.order?.order_number,
                        }),
                    );
                    window.location.href = approve;
                    return;
                }

                const needsStripeModal =
                    stripeReady && payWithCard && cardGateway === 'stripe' && Boolean(orderId);

                if (needsStripeModal && orderId) {
                    const intentRes = await fetch(apiUrl('/api/payments/intent'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(token ? { Authorization: `Bearer ${token}` } : {}),
                        },
                        body: JSON.stringify({ order_id: orderId, orderId }),
                    });
                    if (!intentRes.ok) {
                        const errBody = await intentRes.json().catch(() => ({}));
                        toast({
                            title: 'Payment setup failed',
                            description:
                                typeof errBody?.detail === 'string'
                                    ? errBody.detail
                                    : `Intent failed (${intentRes.status})`,
                            variant: 'destructive',
                        });
                        return;
                    }
                    const intent = await intentRes.json();
                    const clientSecret = (intent.client_secret ?? intent.clientSecret) as string;
                    const publishableKey = (intent.publishable_key ?? intent.publishableKey) as string;
                    const totalNum = Number(orderBody?.order?.total ?? total);
                    const totalFormatted = Number.isFinite(totalNum)
                        ? new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(totalNum)
                        : undefined;
                    sessionStorage.setItem(
                        'stripe_checkout',
                        JSON.stringify({
                            orderId,
                            publishableKey,
                            orderNumber: orderBody?.order?.order_number,
                        }),
                    );
                    setStripeCheckout({
                        orderId,
                        clientSecret,
                        publishableKey,
                        orderNumber: orderBody?.order?.order_number,
                        totalFormatted,
                    });
                    setStripeModalOpen(true);
                    setLastOrderNumber(orderNumberStr);
                    return;
                }

                if (
                    payWithCard &&
                    orderId &&
                    cardGateway === 'stripe' &&
                    !stripeReady
                ) {
                    toast({
                        title: 'Payment unavailable',
                        description: 'Stripe is not configured. Please configure STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY on the server.',
                        variant: 'destructive',
                    });
                    return;
                }

                // ── Dispatch notifications synchronously ──
                try {
                  const txItems: TransactionItem[] = items.map((item) => ({
                    productId: String(item.product.id ?? ''),
                    productName: String(item.product.name ?? ''),
                    productSku: String(item.product.id ?? ''),
                    productCategory: String(item.product.category ?? ''),
                    price: Number(item.product.price ?? 0),
                    quantity: item.quantity,
                    imageUrl: item.product.images?.[0] ?? '',
                    brandName: item.product.brand != null ? String(item.product.brand) : undefined,
                  }));

                  const storeName = isPickup && pickupStore ? pickupStore.name : 'CONFIT Store';
                  const storeAddr = isPickup && pickupStore ? pickupStore.address : '';

                  const txData: TransactionData = {
                    orderId: orderId || orderNumberStr,
                    orderNumber: orderNumberStr,
                    orderStatus: 'confirmed',
                    transactionTime: new Date().toISOString(),
                    customerName: `${shippingInfo.firstName} ${shippingInfo.lastName}`.trim() || user?.name || 'Customer',
                    customerEmail: shippingInfo.email || user?.email || '',
                    customerPhone: shippingInfo.phone,
                    items: txItems,
                    storeName,
                    storeAddress: storeAddr,
                    storeId: isPickup ? selectedStore : undefined,
                    totalPaid: total,
                    currency: '$',
                    paymentMethod: paymentMethod === 'bnpl' ? 'Buy Now Pay Later' : `Card (${cardGateway})`,
                  };

                  NotificationService.dispatchPurchaseNotifications(
                    txData,
                    user?.id || 'anonymous',
                    isPickup ? selectedStore : undefined
                  );
                } catch (notifErr) {
                  console.warn('[Checkout] Notification dispatch failed (non-blocking):', notifErr);
                }

                setOrderPlaced(true);
                setLastOrderNumber(orderNumberStr);
                clearCart();
            } else {
                const body = await response.json().catch(() => ({}));
                // Handle Pydantic validation errors which come as arrays of error objects
                let message = `Request failed (${response.status})`;
                if (Array.isArray(body.detail) && body.detail[0]?.msg) {
                    message = body.detail[0].msg;
                } else if (typeof body.detail === 'string') {
                    message = body.detail;
                }
                toast({ title: 'Order failed', description: message, variant: 'destructive' });
            }
        } catch (error) {
            console.error('Order placement failed:', error);
            toast({
                title: 'Connection Failed',
                description: 'Could not reach the server. Please check your internet connection and try again.',
                variant: 'destructive',
            });
        } finally {
            setIsPlacing(false);
        }
    }, [
        items,
        shippingInfo,
        paymentMethod,
        deliveryMethod,
        selectedStore,
        stores,
        clearCart,
        toast,
        confirmPickupPayment,
        total,
        cardGateway,
    ]);

    const dismissPaymobOverlay = useCallback(() => {
        setPaymobIframeUrl(null);
    }, []);

    const clearPaymentProviderError = useCallback(() => setPaymentProviderError(null), []);

    return {
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
        // Commerce intelligence
        purchaseConfidence,
        deliveryRecommendation,
        bnplEligibility,
        isLoadingIntelligence,

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
    };
}
