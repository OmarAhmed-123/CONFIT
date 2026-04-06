'use client';

import Link from 'next/link';

export default function AuthErrorPage() {
  return (
    <main className="min-h-[70vh] flex items-center justify-center px-6">
      <div className="max-w-lg text-center space-y-4">
        <h1 className="text-3xl font-semibold">Authentication Error</h1>
        <p className="text-muted-foreground">
          We could not complete social sign-in. Please try again.
        </p>
        <Link href="/login" className="text-accent hover:underline font-medium">
          Back to Login
        </Link>
      </div>
    </main>
  );
}
