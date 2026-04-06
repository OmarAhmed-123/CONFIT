'use client';

import dynamic from 'next/dynamic';

const AuthCallbackPage = dynamic(
  () => import('@/pages/AuthCallback').then((mod) => mod.default),
  { ssr: false }
);

export default function AuthCallbackRoutePage() {
  return <AuthCallbackPage />;
}
