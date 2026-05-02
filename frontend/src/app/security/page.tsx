'use client';

import dynamic from 'next/dynamic';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const SecurityDashboardPage = dynamic(
  () => import('@/pages/SecurityDashboard').then((mod) => mod.default),
  { ssr: false }
);

export default function SecurityRoutePage() {
  return (
    <ProtectedRoute>
      <SecurityDashboardPage />
    </ProtectedRoute>
  );
}
