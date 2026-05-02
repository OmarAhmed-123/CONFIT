'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const StoreAnalyticsPage = dynamic(
  () => import('@/pages/analytics/StoreAnalyticsPage').then((mod) => mod.default),
  { ssr: false }
);

export default function StoreAnalyticsRoutePage() {
  const params = useParams<{ storeId?: string }>();
  const storeId = Array.isArray(params?.storeId) ? params.storeId[0] : params?.storeId;

  return (
    <ProtectedRoute>
      <StoreAnalyticsPage storeId={storeId} />
    </ProtectedRoute>
  );
}
