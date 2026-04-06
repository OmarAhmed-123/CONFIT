'use client';

import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const UserAnalyticsPage = dynamic(
  () => import('@/pages/analytics/UserAnalyticsPage').then((mod) => mod.default),
  { ssr: false }
);

export default function UserAnalyticsRoutePage() {
  return (
    <ProtectedRoute>
      <UserAnalyticsPage />
    </ProtectedRoute>
  );
}
