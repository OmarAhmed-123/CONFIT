'use client';

import dynamic from 'next/dynamic';
import ProtectedRoute from '@/components/auth/ProtectedRoute';

const StoreDashboardPage = dynamic(
  () => import('@/pages/StoreDashboard').then((mod) => mod.default),
  { ssr: false }
);

export default function StoreDashboardRoutePage() {
  return (
    <ProtectedRoute>
      <StoreDashboardPage />
    </ProtectedRoute>
  );
}
