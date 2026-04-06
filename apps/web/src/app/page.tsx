import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'CONFIT — Your Personal Fashion Platform',
  description: 'Discover, style, and shop fashion with AI-powered recommendations and virtual try-on.',
};

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-neutral-950 px-6 py-16 text-white">
      <div className="w-full max-w-2xl rounded-3xl border border-white/10 bg-white/5 p-10 backdrop-blur">
        <h1 className="text-3xl font-semibold tracking-tight">CONFIT</h1>
        <p className="mt-3 text-sm text-white/70">
          Your personal fashion platform — discover styles, try on virtually, and shop with confidence.
        </p>
        <div className="mt-7 flex gap-3">
          <Link
            className="rounded-xl bg-white px-4 py-2 text-sm font-medium text-black hover:bg-white/90"
            href="/login"
          >
            Sign in
          </Link>
          <Link
            className="rounded-xl border border-white/15 px-4 py-2 text-sm font-medium text-white hover:bg-white/5"
            href="/app"
          >
            Open app
          </Link>
        </div>
      </div>
    </div>
  );
}
