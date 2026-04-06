/**
 * Checkout Cancel Page
 * Displayed when user cancels Stripe Checkout
 */

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { XCircle } from 'lucide-react';

export const metadata = {
  title: 'Payment Cancelled',
};

export default function CheckoutCancelPage() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-6">
          <XCircle className="h-8 w-8 text-red-600" />
        </div>
        <h1 className="text-3xl font-display font-semibold mb-4">
          Payment Cancelled
        </h1>
        <p className="text-[var(--color-gray-600)] mb-8">
          Your payment was cancelled. Your cart items are still saved if you&apos;d
          like to try again.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/cart">
            <Button variant="outline">Return to Cart</Button>
          </Link>
          <Link href="/discover">
            <Button>Continue Shopping</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
