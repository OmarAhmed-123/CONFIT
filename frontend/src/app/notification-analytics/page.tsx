'use client';

import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const NotificationAnalyticsPage = dynamic(
  () => import('@/pages/NotificationAnalyticsDashboard').then((mod) => mod.default),
  { ssr: false }
);

export default function NotificationAnalyticsRoutePage() {
  return (
    <ProtectedRoute>
      <NotificationAnalyticsPage />
    </ProtectedRoute>
  );
}
