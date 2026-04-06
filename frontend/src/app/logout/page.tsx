'use client';

import { useEffect } from 'react';
import { signOut } from 'next-auth/react';

export default function LogoutPage() {
  useEffect(() => {
    void signOut({ callbackUrl: '/' });
  }, []);

  return (
    <main className="min-h-[60vh] flex items-center justify-center">
      <p className="text-muted-foreground">Signing you out...</p>
    </main>
  );
}
