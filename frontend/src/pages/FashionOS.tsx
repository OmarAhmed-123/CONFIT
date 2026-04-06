import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Sparkles, Shirt, Leaf, MessageCircle, Send, Loader2, Dna } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { StyleInsights } from '@/components/style-dna/StyleInsights';
import { EvolutionTimeline } from '@/components/style-dna/EvolutionTimeline';
import { getAuthToken } from '@/lib/auth';
import {
  fashionOsDailyOutfit,
  fashionOsClosetInsights,
  fashionOsStylistChat,
  type IdentityDNA,
} from '@/lib/api/fashion-os';
import { styleDNAApi, type StyleDNADashboardData } from '@/lib/api/style-dna';

const pulse = {
  rest: { scale: 1, boxShadow: '0 0 0 0 rgba(99, 102, 241, 0.35)' },
  pulse: {
    scale: [1, 1.01, 1],
    boxShadow: [
      '0 0 0 0 rgba(99, 102, 241, 0.35)',
      '0 0 0 12px rgba(99, 102, 241, 0)',
      '0 0 0 0 rgba(99, 102, 241, 0.35)',
    ],
    transition: { duration: 2.6, repeat: Infinity, ease: 'easeInOut' as const },
  },
};

function IdentityBars({ dna }: { dna: IdentityDNA | null }) {
  if (!dna) return null;
  const rows = [
    { label: 'Elegance', v: dna.elegance_score },
    { label: 'Minimalism', v: dna.minimalism_score },
    { label: 'Boldness', v: dna.boldness_score },
  ];
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.label}>
          <div className="mb-1 flex justify-between text-xs text-muted-foreground">
            <span>{r.label}</span>
            <span>{Math.round(r.v * 100)}%</span>
          </div>
          <Progress value={r.v * 100} className="h-0.5" />
        </div>
      ))}
    </div>
  );
}

export default function FashionOSPage() {
  const token = getAuthToken();
  const [dna, setDna] = useState<IdentityDNA | null>(null);
  const [dashboard, setDashboard] = useState<StyleDNADashboardData | null>(null);
  const [daily, setDaily] = useState<Record<string, unknown> | null>(null);
  const [closet, setCloset] = useState<Awaited<ReturnType<typeof fashionOsClosetInsights>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [chat, setChat] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [d, dash, c] = await Promise.all([
        fashionOsDailyOutfit(),
        styleDNAApi.getDashboard().catch(() => null),
        fashionOsClosetInsights().catch(() => null),
      ]);
      setDaily(d as unknown as Record<string, unknown>);
      setDna(d.identity_dna);
      if (dash) setDashboard(dash);
      setCloset(c);
    } catch {
      setDaily(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const sendChat = async () => {
    const t = input.trim();
    if (!t || !token) return;
    setSending(true);
    setInput('');
    setChat((c) => [...c, { role: 'user', content: t }]);
    try {
      const res = await fashionOsStylistChat({
        message: t,
        conversationHistory: chat.map((m) => ({ role: m.role, content: m.content })),
      });
      setChat((c) => [...c, { role: 'assistant', content: res.content }]);
    } catch {
      setChat((c) => [
        ...c,
        { role: 'assistant', content: 'Could not reach the stylist. Check that you are signed in and the backend is running.' },
      ]);
    } finally {
      setSending(false);
    }
  };

  if (!token) {
    return (
      <MainLayout>
        <div className="mx-auto max-w-lg px-4 py-24 text-center">
          <Dna className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
          <h1 className="font-serif text-2xl font-semibold">Fashion OS</h1>
          <p className="mt-2 text-muted-foreground">Sign in to load your Style DNA and identity layer.</p>
          <Button asChild className="mt-6">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </MainLayout>
    );
  }

  const todayOutfit = daily?.today_outfit as Record<string, unknown> | null | undefined;

  return (
    <MainLayout>
      <div className="mx-auto max-w-6xl px-4 py-8">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-6 flex flex-wrap items-end gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">CONFIT</p>
            <h1 className="font-serif text-3xl font-semibold tracking-tight md:text-4xl">Fashion OS</h1>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">
              Identity-first intelligence — not generic recommendations. Your Style DNA evolves with every interaction.
            </p>
          </div>
          <Sparkles className="hidden h-8 w-8 text-amber-500/90 sm:block" />
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-3">
          <motion.div
            className="lg:col-span-2 space-y-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.05 }}
          >
            <motion.div variants={pulse} initial="rest" animate="pulse">
              <Card className="overflow-hidden border-border/60 bg-gradient-to-br from-background to-muted/30">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Shirt className="h-5 w-5" />
                    Today&apos;s outfit
                  </CardTitle>
                  <CardDescription>Weather, calendar hooks, and past behavior — wired on the backend.</CardDescription>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" /> Generating…
                    </div>
                  ) : todayOutfit ? (
                    <div className="flex flex-wrap gap-3">
                      {(todayOutfit.items as { id?: string; name?: string; image_url?: string }[] | undefined)?.map(
                        (it, i) => (
                          <motion.div
                            key={it.id || i}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.06 }}
                            className="flex h-24 w-24 flex-col items-center justify-center rounded-lg border bg-muted/40 text-center text-xs"
                          >
                            {it.image_url ? (
                              <img src={it.image_url} alt="" className="h-14 w-14 rounded object-cover" />
                            ) : (
                              <Shirt className="h-8 w-8 text-muted-foreground" />
                            )}
                            <span className="mt-1 line-clamp-2">{it.name}</span>
                          </motion.div>
                        ),
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Add items to your wardrobe for owned-first outfit suggestions.</p>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Style insights</CardTitle>
                <CardDescription>Interpretable signals — embeddings never leave the server.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-6 md:grid-cols-2">
                <IdentityBars dna={dna} />
                {dashboard?.style_insights?.length ? (
                  <StyleInsights insights={dashboard.style_insights} />
                ) : (
                  <p className="text-sm text-muted-foreground">Complete your Style DNA quiz to unlock richer insights.</p>
                )}
              </CardContent>
            </Card>

            {dashboard?.evolution_timeline?.length ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Style evolution</CardTitle>
                </CardHeader>
                <CardContent>
                  <EvolutionTimeline events={dashboard.evolution_timeline} />
                </CardContent>
              </Card>
            ) : null}
          </motion.div>

          <div className="space-y-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Leaf className="h-5 w-5 text-emerald-600" />
                  Smart closet
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {closet ? (
                  <>
                    <p>
                      <span className="font-medium text-foreground">{closet.unused_items.length}</span> pieces haven&apos;t appeared
                      in recent outfits.
                    </p>
                    {closet.missing_essentials.length > 0 && (
                      <p className="text-muted-foreground">
                        Missing essentials: {closet.missing_essentials.join(', ')}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">{closet.sustainability_note}</p>
                  </>
                ) : (
                  <p className="text-muted-foreground">Closet insights load after your first wardrobe sync.</p>
                )}
              </CardContent>
            </Card>

            <Card className="flex flex-col border-border/80">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <MessageCircle className="h-5 w-5" />
                  AI stylist
                </CardTitle>
                <CardDescription>Grounded in your Style DNA context.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col gap-3">
                <div className="max-h-64 overflow-y-auto rounded-md border bg-muted/20 p-2 text-sm">
                  {chat.length === 0 ? (
                    <p className="p-2 text-muted-foreground">Ask for a mood, occasion, or budget — we reason from identity.</p>
                  ) : (
                    chat.map((m, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: m.role === 'user' ? 8 : -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`mb-2 rounded-md px-2 py-1.5 ${m.role === 'user' ? 'ml-4 bg-primary/10' : 'mr-4 bg-muted'}`}
                      >
                        {m.content}
                      </motion.div>
                    ))
                  )}
                </div>
                <div className="flex gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Message your stylist…"
                    onKeyDown={(e) => e.key === 'Enter' && sendChat()}
                  />
                  <Button type="button" size="icon" onClick={sendChat} disabled={sending}>
                    {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
