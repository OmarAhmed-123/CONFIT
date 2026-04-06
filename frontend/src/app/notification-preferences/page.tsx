'use client';

import dynamic from 'next/dynamic';

const NotificationPreferencesPage = dynamic(
  () => import('@/pages/NotificationPreferencesPage').then((mod) => mod.default),
  { ssr: false }
);

export default function NotificationPreferencesRoutePage() {
  return <NotificationPreferencesPage />;
}
