/**
 * Checkout Page
 */

'use client';

import dynamic from 'next/dynamic';

const CheckoutPage = dynamic(
  () => import('@/pages/Checkout').then((mod) => mod.default),
  { 
    ssr: false,
    loading: () => (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    ),
  }
);

export default function CheckoutRoute() {
  return <CheckoutPage />;
}
