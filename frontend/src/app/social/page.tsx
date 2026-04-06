'use client';

import dynamic from 'next/dynamic';

const SocialPage = dynamic(
  () => import('@/pages/Social').then((mod) => mod.default),
  { ssr: false }
);

export default function SocialRoutePage() {
  return <SocialPage />;
}
