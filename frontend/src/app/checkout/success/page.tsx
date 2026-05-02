'use client';

import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { apiUrl } from '@/lib/api';

export default function CheckoutSuccessPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <SuccessContent />
    </Suspense>
  );
}

function LoadingState() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="animate-spin h-8 w-8 border-4 border-[var(--color-gold-400)] border-t-transparent rounded-full" />
    </div>
  );
}

function SuccessContent() {
  const searchParams = useSearchParams();
  const orderId = searchParams?.get('order_id') || searchParams?.get('orderId');
  const [status, setStatus] = useState<'verified' | 'pending' | 'failed'>(orderId ? 'pending' : 'verified');
  const [message, setMessage] = useState('Thank you for your purchase. Your order has been confirmed and you will receive an email confirmation shortly.');

  useEffect(() => {
    if (!orderId) return;
    let cancelled = false;
    fetch(apiUrl(`/api/orders/${encodeURIComponent(orderId)}`), { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok || payload?.success === false) {
          throw new Error(payload?.detail || 'Could not verify order.');
        }
        return payload?.order ?? payload;
      })
      .then((order) => {
        if (cancelled) return;
        const paymentStatus = String(order?.payment_status || order?.paymentStatus || '').toLowerCase();
        if (paymentStatus && !['success', 'paid', 'confirmed'].includes(paymentStatus)) {
          setStatus('pending');
          setMessage('Your order was created and payment is still being confirmed. You can track the latest status from Orders.');
          return;
        }
        setStatus('verified');
        setMessage('Payment and order status were verified successfully.');
      })
      .catch((error) => {
        if (cancelled) return;
        setStatus('failed');
        setMessage(error instanceof Error ? error.message : 'Could not verify this payment yet.');
      });

    return () => {
      cancelled = true;
    };
  }, [orderId]);

  const isFailed = status === 'failed';

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6 ${isFailed ? 'bg-amber-100' : 'bg-green-100'}`}>
          {isFailed ? <AlertCircle className="h-8 w-8 text-amber-600" /> : <CheckCircle className="h-8 w-8 text-green-600" />}
        </div>
        <h1 className="text-3xl font-display font-semibold mb-4">
          {isFailed ? 'Payment Verification Pending' : status === 'pending' ? 'Confirming Payment' : 'Payment Successful!'}
        </h1>
        <p className="text-[var(--color-gray-600)] mb-8">
          {message}
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/orders">
            <Button variant="outline">View Orders</Button>
          </Link>
          <Link href="/discover">
            <Button>Continue Shopping</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
