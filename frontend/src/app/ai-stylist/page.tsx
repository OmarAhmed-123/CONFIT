/**
 * /ai-stylist — same experience as legacy Vite route (nav links use this path).
 * Page component already includes MainLayout.
 */

'use client';

import dynamic from 'next/dynamic';

const AIStylistChat = dynamic(
  () => import('@/pages/AIStylistChat').then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    ),
  }
);

export default function AIStylistRoutePage() {
  return <AIStylistChat />;
}
