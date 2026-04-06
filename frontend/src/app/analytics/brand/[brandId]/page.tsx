'use client';

import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const BrandAnalyticsPage = dynamic(
  () => import('@/pages/analytics/BrandAnalyticsPage').then((mod) => mod.default),
  { ssr: false }
);

export default function BrandAnalyticsRoutePage() {
  return (
    <ProtectedRoute>
      <BrandAnalyticsPage />
    </ProtectedRoute>
  );
}
