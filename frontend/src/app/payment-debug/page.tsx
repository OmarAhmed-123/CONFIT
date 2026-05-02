'use client';

import dynamic from 'next/dynamic';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const PaymentDebugDashboardPage = dynamic(
  () => import('@/pages/PaymentDebugDashboard').then((mod) => mod.default),
  { ssr: false }
);

export default function PaymentDebugRoutePage() {
  return (
    <ProtectedRoute>
      <PaymentDebugDashboardPage />
    </ProtectedRoute>
  );
}
