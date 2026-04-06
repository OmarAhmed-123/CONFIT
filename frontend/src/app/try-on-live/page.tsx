'use client';

import dynamic from 'next/dynamic';

const TryOnLivePage = dynamic(
  () => import('@/pages/TryOnLive').then((mod) => mod.default),
  { ssr: false }
);

export default function TryOnLiveRoutePage() {
  return <TryOnLivePage />;
}
