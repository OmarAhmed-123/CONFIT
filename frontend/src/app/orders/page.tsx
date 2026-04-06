/**
 * Orders Page
 */

'use client';

import dynamic from 'next/dynamic';
import { MainLayout } from '@/components/layout';

const OrderHistoryPage = dynamic(
  () => import('@/pages/OrderHistory').then((mod) => mod.default),
  { 
    ssr: false,
    loading: () => (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    ),
  }
);

export default function OrdersRoute() {
  return (
    <MainLayout>
      <OrderHistoryPage />
    </MainLayout>
  );
}
