'use client';

import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const AdminAnalyticsPage = dynamic(
  () => import('@/pages/analytics/AdminAnalyticsPage').then((mod) => mod.default),
  { ssr: false }
);

export default function AdminAnalyticsRoutePage() {
  return (
    <ProtectedRoute>
      <AdminAnalyticsPage />
    </ProtectedRoute>
  );
}
