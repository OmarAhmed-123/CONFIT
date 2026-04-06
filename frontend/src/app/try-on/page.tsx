/**
 * Virtual Try-On Page
 */

'use client';

import dynamic from 'next/dynamic';
// Dynamically import the try-on component to avoid SSR issues
const VirtualTryOnContent = dynamic(
  () => import('@/components/try-on/VirtualTryOnContent').then((mod) => mod.default),
  { 
    ssr: false,
    loading: () => (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    ),
  }
);

export default function VirtualTryOnPage() {
  /* VirtualTryOn page already includes MainLayout */
  return <VirtualTryOnContent />;
}
