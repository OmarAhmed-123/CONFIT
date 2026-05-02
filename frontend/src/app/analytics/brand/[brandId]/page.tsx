'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const BrandAnalyticsPage = dynamic(
  () => import('@/pages/analytics/BrandAnalyticsPage').then((mod) => mod.default),
  { ssr: false }
);

export default function BrandAnalyticsRoutePage() {
  const params = useParams<{ brandId?: string }>();
  const brandId = Array.isArray(params?.brandId) ? params.brandId[0] : params?.brandId;

  return (
    <ProtectedRoute>
      <BrandAnalyticsPage brandId={brandId} />
    </ProtectedRoute>
  );
}
