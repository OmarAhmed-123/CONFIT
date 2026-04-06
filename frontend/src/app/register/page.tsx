'use client';

import dynamic from 'next/dynamic';

const RegisterPage = dynamic(
  () => import('@/pages/Register').then((mod) => mod.default),
  { ssr: false }
);

export default function RegisterRoutePage() {
  return <RegisterPage />;
}
