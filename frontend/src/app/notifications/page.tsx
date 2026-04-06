'use client';

import dynamic from 'next/dynamic';

const NotificationsPage = dynamic(
  () => import('@/pages/NotificationsPage').then((mod) => mod.default),
  { ssr: false }
);

export default function NotificationsRoutePage() {
  return <NotificationsPage />;
}
