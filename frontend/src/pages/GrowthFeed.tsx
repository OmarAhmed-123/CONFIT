import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/context/AuthContext';
import { ViralOutfitCard } from '@/components/growth/ViralOutfitCard';
import {
  fetchViralFeed,
  shareOutfit,
  fetchGrowthCreators,
  fetchGrowthAnalytics,
  fetchGrowthPredict,
  type ViralFeedPost,
} from '@/lib/api/growth';
import { createTransition } from '@/motion';
import { Loader2, Radar, Users, BarChart3 } from 'lucide-react';

export default function GrowthFeedPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const [tab, setTab] = useState<'feed' | 'creators' | 'brain'>('feed');
  const [posts, setPosts] = useState<ViralFeedPost[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const nextOffsetRef = useRef(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const [creators, setCreators] = useState<Array<Record<string, unknown>>>([]);
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);
  const [predict, setPredict] = useState<Record<string, unknown> | null>(null);
  const [sideLoading, setSideLoading] = useState(false);

  const loadFeed = useCallback(async (append: boolean) => {
    if (append) setLoadingMore(true);
    else setLoading(true);
    try {
      const start = append ? nextOffsetRef.current : 0;
      const data = await fetchViralFeed(start, 12);
      nextOffsetRef.current = data.next_offset;
      setPosts((prev) => (append ? [...prev, ...data.posts] : data.posts));
      setHasMore(data.has_more);
    } catch {
      toast({ title: 'Feed unavailable', description: 'Could not load viral outfit feed.', variant: 'destructive' });
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [toast]);

  useEffect(() => {
    nextOffsetRef.current = 0;
    loadFeed(false);
  }, [loadFeed]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore && !loading && !loadingMore && tab === 'feed') {
          loadFeed(true);
        }
      },
      { rootMargin: '120px' }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [hasMore, loadFeed, loading, loadingMore, tab]);

  const handleShare = useCallback(
    async (post: ViralFeedPost) => {
      if (!user) {
        toast({ title: 'Sign in to share', description: 'Create an account to generate referral links.' });
        return;
      }
      try {
        const res = await shareOutfit(undefined, post.id);
        await navigator.clipboard.writeText(res.share_url);
        toast({
          title: 'Share link ready',
          description: 'Referral link copied. Growth engine is tracking this share.',
        });
      } catch (e) {
        toast({
          title: 'Share failed',
          description: e instanceof Error ? e.message : 'Try again later.',
          variant: 'destructive',
        });
      }
    },
    [toast, user]
  );

  useEffect(() => {
    if (tab === 'creators' && user) {
      setSideLoading(true);
      fetchGrowthCreators(10)
        .then((r) => setCreators(r.creators ?? []))
        .catch(() => toast({ title: 'Creators', description: 'Could not load matches.', variant: 'destructive' }))
        .finally(() => setSideLoading(false));
    }
    if (tab === 'brain' && user) {
      setSideLoading(true);
      Promise.all([fetchGrowthAnalytics(), fetchGrowthPredict()])
        .then(([a, p]) => {
          setAnalytics(a as Record<string, unknown>);
          setPredict(p as Record<string, unknown>);
        })
        .catch(() => toast({ title: 'Analytics', description: 'Could not load growth brain.', variant: 'destructive' }))
        .finally(() => setSideLoading(false));
    }
  }, [tab, user, toast]);

  return (
    <MainLayout>
      <div className="container py-8 max-w-2xl mx-auto space-y-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ duration: 0.4 })}
          className="space-y-2"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <Radar className="h-3.5 w-3.5" />
            Autonomous Growth Engine
          </div>
          <h1 className="text-3xl font-playfair font-semibold tracking-tight">Viral Outfit Feed</h1>
          <p className="text-muted-foreground text-sm max-w-lg">
            Product-led growth: every view is ranked by engagement probability, style fit, and trend momentum — tuned to
            you.
          </p>
        </motion.div>

        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="feed" className="gap-1.5 text-xs sm:text-sm">
              <SparklesTabIcon />
              Feed
            </TabsTrigger>
            <TabsTrigger value="creators" className="gap-1.5 text-xs sm:text-sm" disabled={!user}>
              <Users className="h-3.5 w-3.5" />
              Creators
            </TabsTrigger>
            <TabsTrigger value="brain" className="gap-1.5 text-xs sm:text-sm" disabled={!user}>
              <BarChart3 className="h-3.5 w-3.5" />
              Brain
            </TabsTrigger>
          </TabsList>

          <TabsContent value="feed" className="mt-6 space-y-6">
            {loading && posts.length === 0 ? (
              <div className="flex justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="flex flex-col gap-8">
                {posts.map((p) => (
                  <ViralOutfitCard key={p.id} post={p} onShare={handleShare} />
                ))}
                <div ref={sentinelRef} className="h-4 w-full" />
                {loadingMore && (
                  <div className="flex justify-center py-6">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                )}
                {!hasMore && posts.length > 0 && (
                  <p className="text-center text-xs text-muted-foreground pb-8">You&apos;re up to date</p>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="creators" className="mt-6">
            {!user ? (
              <p className="text-sm text-muted-foreground">
                <Link href="/login" className="text-primary underline">
                  Sign in
                </Link>{' '}
                for influencer matching (style DNA + engagement overlap).
              </p>
            ) : sideLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <ul className="space-y-3">
                {creators.map((c) => (
                  <li
                    key={String(c.influencer_id)}
                    className="flex items-center justify-between rounded-xl border border-border/60 p-3"
                  >
                    <div>
                      <p className="font-medium">{String(c.display_name)}</p>
                      <p className="text-[11px] text-muted-foreground">
                        Match {(Number(c.composite_score) * 100).toFixed(0)}% · DNA {String(c.style_dna_score)}
                      </p>
                    </div>
                    <Button asChild size="sm" variant="secondary">
                      <Link href={`/influencer/${String(c.influencer_id)}`}>Profile</Link>
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>

          <TabsContent value="brain" className="mt-6 space-y-4 text-sm">
            {!user ? (
              <p className="text-muted-foreground">Sign in to view growth analytics and predictions.</p>
            ) : sideLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <>
                {analytics && (
                  <div className="rounded-xl border border-border/60 p-4 space-y-2 bg-card/50">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Analytics brain</p>
                    <p>Viral K (est.): {String(analytics.viral_coefficient_estimate)}</p>
                    <p>Share rate: {String(analytics.outfit_share_rate)}</p>
                    <p>Conversion / outfit: {String(analytics.conversion_per_outfit)}</p>
                    <p>Try-on engagement proxy: {String(analytics.try_on_engagement_rate)}</p>
                    {(analytics.bottlenecks as string[])?.length ? (
                      <ul className="list-disc pl-4 text-amber-600 dark:text-amber-400">
                        {(analytics.bottlenecks as string[]).map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    ) : null}
                    {(analytics.optimizations as string[])?.map((o) => (
                      <p key={o} className="text-xs text-muted-foreground border-l-2 border-primary/40 pl-2">
                        {o}
                      </p>
                    ))}
                  </div>
                )}
                {predict && (
                  <div className="rounded-xl border border-border/60 p-4 space-y-1 bg-card/50">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Engagement prediction</p>
                    <p>Purchase: {String(predict.purchase_likelihood)}</p>
                    <p>Churn risk: {String(predict.churn_risk)}</p>
                    <p>Share prob.: {String(predict.share_probability)}</p>
                  </div>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}

function SparklesTabIcon() {
  return (
    <motion.span
      animate={{ rotate: [0, 8, -8, 0] }}
      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      className="inline-flex"
    >
      <Radar className="h-3.5 w-3.5" />
    </motion.span>
  );
}
