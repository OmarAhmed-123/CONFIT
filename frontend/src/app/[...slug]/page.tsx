import Link from 'next/link';
import { Button } from '@/components/ui/button';

interface MissingRoutePageProps {
  params: Promise<{ slug: string[] }>;
}

export default async function MissingRoutePage({ params }: MissingRoutePageProps) {
  const { slug } = await params;
  const requestedPath = `/${slug.join('/')}`;

  return (
    <main className="min-h-[70vh] flex items-center justify-center px-4 py-12">
      <section className="w-full max-w-2xl rounded-2xl border border-border bg-card p-8 text-center shadow-sm">
        <p className="text-sm uppercase tracking-[0.18em] text-muted-foreground">CONFIT</p>
        <h1 className="mt-3 text-3xl font-semibold">This page is not available yet</h1>
        <p className="mt-4 text-muted-foreground">
          The route <span className="font-medium text-foreground">{requestedPath}</span> is not published yet.
          You can continue browsing from one of the ready sections below.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button asChild>
            <Link href="/">Home</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/discover">Discover</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/products">Products</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/profile">Profile</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
