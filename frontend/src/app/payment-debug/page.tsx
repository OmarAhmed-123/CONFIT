'use client';

import dynamic from 'next/dynamic';

const PaymentDebugDashboardPage = dynamic(
  () => import('@/pages/PaymentDebugDashboard').then((mod) => mod.default),
  { ssr: false }
);

export default function PaymentDebugRoutePage() {
  return <PaymentDebugDashboardPage />;
}
