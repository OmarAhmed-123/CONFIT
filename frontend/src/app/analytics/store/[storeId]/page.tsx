'use client';

import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const StoreAnalyticsPage = dynamic(
  () => import('@/pages/analytics/StoreAnalyticsPage').then((mod) => mod.default),
  { ssr: false }
);

export default function StoreAnalyticsRoutePage() {
  return (
    <ProtectedRoute>
      <StoreAnalyticsPage />
    </ProtectedRoute>
  );
}
