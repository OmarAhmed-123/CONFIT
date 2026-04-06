import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/layout';
import { Loader2 } from 'lucide-react';

/** Landing for /join?ref= — stores referral and continues to registration. */
export default function JoinReferralPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const ref = searchParams.get('ref');
    if (ref) {
      try {
        sessionStorage.setItem('confit_referral_code', ref);
      } catch {
        /* ignore quota */
      }
    }
    const t = window.setTimeout(() => router.replace('/register'), 600);
    return () => window.clearTimeout(t);
  }, [searchParams, router]);

  return (
    <MainLayout>
      <div className="container flex min-h-[40vh] flex-col items-center justify-center gap-4 py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Applying your invite…</p>
      </div>
    </MainLayout>
  );
}
