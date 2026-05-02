'use client';

import dynamic from 'next/dynamic';
import type { ComponentType } from 'react';

type Loader = () => Promise<{ default: ComponentType }>;

export function createClientPage(loader: Loader) {
  const Page = dynamic(loader, {
    ssr: false,
    loading: () => (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-accent border-t-transparent" />
      </div>
    ),
  });

  return function ClientPageRoute() {
    return <Page />;
  };
}
