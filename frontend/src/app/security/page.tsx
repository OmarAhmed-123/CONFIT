'use client';

import dynamic from 'next/dynamic';

const SecurityDashboardPage = dynamic(
  () => import('@/pages/SecurityDashboard').then((mod) => mod.default),
  { ssr: false }
);

export default function SecurityRoutePage() {
  return <SecurityDashboardPage />;
}
