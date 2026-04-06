'use client';

import dynamic from 'next/dynamic';

const StoreLocatorPage = dynamic(
  () => import('@/pages/StoreLocator').then((mod) => mod.default),
  { ssr: false }
);

export default function StoresRoutePage() {
  return <StoreLocatorPage />;
}
