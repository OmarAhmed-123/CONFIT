/**
 * AI Stylist Page
 */

'use client';

import dynamic from 'next/dynamic';

/** `AIStylistChat` already wraps content in MainLayout — avoid double layout. */
const AIStylistChat = dynamic(
  () => import('@/pages/AIStylistChat').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    ),
  }
);

export default function StylistPage() {
  return <AIStylistChat />;
}
