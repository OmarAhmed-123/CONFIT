/**
 * Stripe Payment Element — real card + wallets + Klarna (where Stripe enables them).
 * No raw card fields; PCI scope stays with Stripe.
 */
import { useMemo, useState } from 'react';
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js';
import { loadStripe, type StripeElementsOptions } from '@stripe/stripe-js';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

function InnerPay({
    onSuccess,
    onError,
}: {
    onSuccess: (paymentIntentId: string) => void;
    onError: (message: string) => void;
}) {
    const stripe = useStripe();
    const elements = useElements();
    const [busy, setBusy] = useState(false);

    const pay = async () => {
        if (!stripe || !elements) return;
        setBusy(true);
        try {
            const { error, paymentIntent } = await stripe.confirmPayment({
                elements,
                confirmParams: {
                    return_url: `${window.location.origin}${window.location.pathname}`,
                },
                redirect: 'if_required',
            });
            if (error) {
                onError(error.message || 'Payment failed');
                setBusy(false);
                return;
            }
            if (paymentIntent?.status === 'succeeded' && paymentIntent.id) {
                onSuccess(paymentIntent.id);
                return;
            }
            onError(`Payment status: ${paymentIntent?.status ?? 'unknown'}`);
        } catch (e: unknown) {
            onError(e instanceof Error ? e.message : 'Payment failed');
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="space-y-4">
            <PaymentElement />
            <Button type="button" className="w-full" onClick={pay} disabled={busy || !stripe}>
                {busy ? 'Processing…' : 'Pay securely'}
            </Button>
        </div>
    );
}

export type StripePaymentPayload = {
    orderId: string;
    clientSecret: string;
    publishableKey: string;
    /** Shown above the Payment Element (order total). */
    orderNumber?: string;
    totalFormatted?: string;
};

export function StripePaymentModal(props: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    payload: StripePaymentPayload | null;
    onPaid: (paymentIntentId: string) => Promise<void>;
    onError: (message: string) => void;
}) {
    const stripePromise = useMemo(
        () => (props.payload ? loadStripe(props.payload.publishableKey) : null),
        [props.payload?.publishableKey],
    );

    const options: StripeElementsOptions | undefined = props.payload
        ? {
              clientSecret: props.payload.clientSecret,
              appearance: {
                  theme: 'stripe',
                  variables: {
                      colorPrimary: '#0f172a',
                      borderRadius: '8px',
                  },
              },
              loader: 'auto',
          }
        : undefined;

    if (!props.payload || !stripePromise || !options) return null;

    return (
        <Dialog open={props.open} onOpenChange={props.onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Complete payment</DialogTitle>
                    <DialogDescription className="space-y-1">
                        <span className="block text-foreground font-medium tabular-nums">
                            {props.payload.totalFormatted
                                ? `Total ${props.payload.totalFormatted}`
                                : props.payload.orderNumber
                                  ? `Order ${props.payload.orderNumber}`
                                  : 'Secure checkout'}
                        </span>
                        <span className="block text-muted-foreground text-sm">
                            Cards, Apple Pay, Google Pay, and Klarna (where Stripe enables them). Card data stays with
                            Stripe — not stored on our servers.
                        </span>
                    </DialogDescription>
                </DialogHeader>
                <Elements key={props.payload.clientSecret} stripe={stripePromise} options={options}>
                    <InnerPay
                        onSuccess={async (id) => {
                            await props.onPaid(id);
                        }}
                        onError={props.onError}
                    />
                </Elements>
            </DialogContent>
        </Dialog>
    );
}
