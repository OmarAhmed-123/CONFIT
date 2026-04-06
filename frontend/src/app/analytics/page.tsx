'use client';

import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const AnalyticsIndexPage = dynamic(
  () => import('@/pages/analytics/AnalyticsIndexPage').then((mod) => mod.default),
  { ssr: false }
);

export default function AnalyticsRoutePage() {
  return (
    <ProtectedRoute>
      <AnalyticsIndexPage />
    </ProtectedRoute>
  );
}
