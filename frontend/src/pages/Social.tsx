import { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { Flame, Snowflake, Link as LinkIcon, Sparkles, Plus } from 'lucide-react';
import { useSocialViewModel, type Visibility, type VoteValue } from '@/viewmodels/useSocialViewModel';
import { createTransition } from '@/motion';
import { GlassCard } from '@/components/shared';
import { ScrollReveal } from '@/components/motion/ScrollReveal';

export default function SocialPage() {
  const { toast } = useToast();
  const {
    posts,
    lookbooks,
    isLoadingFeed,
    isLoadingLookbooks,
    isPosting,
    vote,
    createPost
  } = useSocialViewModel();

  const [tab, setTab] = useState<'feed' | 'lookbooks'>('feed');
  const [imageUrl, setImageUrl] = useState('');
  const [caption, setCaption] = useState('');
  const [visibility, setVisibility] = useState<Visibility>('public');

  const handleCreatePost = useCallback(async () => {
    const success = await createPost(imageUrl, caption, visibility);
    if (success) {
      setImageUrl('');
      setCaption('');
      setVisibility('public');
    }
  }, [createPost, imageUrl, caption, visibility]);

  const copyShareLink = useCallback(async (postId: string) => {
    const url = `${window.location.origin}/social?post=${encodeURIComponent(postId)}`;
    try {
      await navigator.clipboard.writeText(url);
      toast({ title: 'Link copied', description: 'Share it with friends to vote.' });
    } catch {
      toast({ title: 'Copy failed', description: 'Unable to copy link.' });
    }
  }, [toast]);

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-6xl mx-auto space-y-8">
          <ScrollReveal>
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full mb-3">
                <Sparkles className="h-4 w-4" />
                <span className="text-sm font-medium">Social Styling</span>
              </div>
              <h1 className="heading-hero mb-2">Community Co‑Creation</h1>
              <p className="text-muted-foreground max-w-2xl">
                Share your try‑on results, get confidence votes, and explore curated public lookbooks.
              </p>
            </div>

            <div className="inline-flex rounded-full border border-border bg-card p-1">
              <button
                type="button"
                onClick={() => setTab('feed')}
                className={`px-5 py-2 text-sm rounded-full transition-colors ${tab === 'feed' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Feed
              </button>
              <button
                type="button"
                onClick={() => setTab('lookbooks')}
                className={`px-5 py-2 text-sm rounded-full transition-colors ${tab === 'lookbooks' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Lookbooks
              </button>
            </div>
          </div>
          </ScrollReveal>

          {tab === 'feed' ? (
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.75fr)] items-start">
              {/* Feed */}
              <div className="space-y-6">
                {isLoadingFeed ? (
                  <div className="space-y-4">
                    {[1, 2].map(i => (
                      <div key={i} className="bg-card border border-border rounded-xl aspect-[3/4] animate-pulse" />
                    ))}
                  </div>
                ) : posts.length === 0 ? (
                  <div className="bg-card border border-border rounded-xl p-10 text-center">
                    <p className="text-muted-foreground">No posts yet. Be the first to share a look.</p>
                  </div>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-6">
                    {posts.map((p, idx) => (
                      <motion.article
                        key={p.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={createTransition({ duration: 0.25, delay: Math.min(idx * 0.03, 0.2) })}
                        className="bg-card border border-border rounded-xl overflow-hidden"
                      >
                        <div className="aspect-[3/4] bg-muted overflow-hidden">
                          <img
                            src={p.image_url}
                            alt="Try-on post"
                            className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
                            loading="lazy"
                          />
                        </div>
                        <div className="p-4 space-y-3">
                          {p.caption && <p className="text-sm">{p.caption}</p>}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Button
                                variant={p.user_vote === 'hot' ? 'hero' : 'outline'}
                                size="sm"
                                onClick={() => vote(p.id, 'hot')}
                                className="gap-2"
                              >
                                <Flame className="h-4 w-4" />
                                {p.hot_count}
                              </Button>
                              <Button
                                variant={p.user_vote === 'cold' ? 'hero' : 'outline'}
                                size="sm"
                                onClick={() => vote(p.id, 'cold')}
                                className="gap-2"
                              >
                                <Snowflake className="h-4 w-4" />
                                {p.cold_count}
                              </Button>
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => copyShareLink(p.id)} className="gap-2">
                              <LinkIcon className="h-4 w-4" />
                              Share
                            </Button>
                          </div>
                        </div>
                      </motion.article>
                    ))}
                  </div>
                )}
              </div>

              {/* Create post */}
              <motion.aside
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                className="sticky top-24"
              >
                <GlassCard className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="font-semibold">Share a Look</h2>
                    <span className="text-xs text-muted-foreground">🔥 / ❄️ votes</span>
                  </div>

                  <Input value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="Try-on image URL (https://...)" />
                  <Textarea value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Caption (optional)" />

                  <div className="grid grid-cols-3 gap-2">
                    {(['public', 'link', 'private'] as Visibility[]).map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => setVisibility(v)}
                        className={`px-3 py-2 rounded-lg border text-sm transition-colors ${visibility === v ? 'border-accent bg-accent/5 text-accent' : 'border-border hover:border-accent/40 text-muted-foreground'}`}
                      >
                        {v.charAt(0).toUpperCase() + v.slice(1)}
                      </button>
                    ))}
                  </div>

                  <Button variant="hero" onClick={handleCreatePost} disabled={isPosting} className="w-full gap-2">
                    <Plus className="h-4 w-4" />
                    {isPosting ? 'Posting...' : 'Post'}
                  </Button>
                </GlassCard>
              </motion.aside>
            </div>
          ) : (
            <div className="space-y-6">
              {isLoadingLookbooks ? (
                <div className="grid md:grid-cols-2 gap-6">
                  {[1, 2, 3, 4].map(i => (
                    <div key={i} className="bg-card border border-border rounded-xl h-48 animate-pulse" />
                  ))}
                </div>
              ) : lookbooks.length === 0 ? (
                <div className="bg-card border border-border rounded-xl p-10 text-center">
                  <p className="text-muted-foreground">No lookbooks yet.</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-6">
                  {lookbooks.map((lb, idx) => (
                    <motion.div
                      key={lb.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={createTransition({ duration: 0.25, delay: Math.min(idx * 0.03, 0.2) })}
                      className="bg-card border border-border rounded-xl p-6 hover:border-accent/50 transition-colors"
                    >
                      <h3 className="text-lg font-semibold">{lb.title}</h3>
                      {lb.description && <p className="text-sm text-muted-foreground mt-2">{lb.description}</p>}
                      <div className="mt-4 flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{lb.items.length} items</span>
                        <span className="px-2 py-1 bg-accent/10 text-accent rounded-full text-xs font-medium">Commission {Math.round(lb.commission_rate * 100)}%</span>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {lb.items.slice(0, 6).map((it) => (
                          <span key={it.product_id} className="text-xs px-3 py-1 rounded-full bg-muted text-muted-foreground border border-border">
                            Product {it.product_id.slice(0, 5)}...
                          </span>
                        ))}
                        {lb.items.length > 6 && (
                          <span className="text-xs px-3 py-1 rounded-full bg-muted text-muted-foreground">
                            +{lb.items.length - 6} more
                          </span>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
