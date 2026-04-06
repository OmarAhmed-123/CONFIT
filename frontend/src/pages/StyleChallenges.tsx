import { motion } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Trophy, CloudRain, Sparkles } from 'lucide-react';
import { useChallengesViewModel } from '@/viewmodels/useChallengesViewModel';
import { ChatbotWidget } from '@/components/ChatbotWidget';
import { createTransition } from '@/motion';

export default function StyleChallengesPage() {
  const {
    quest,
    leaderboard,
    isLoading,
    isSubmitting,
    submit
  } = useChallengesViewModel();

  return (
    <>
      <MainLayout>
        <div className="container py-8">
          <div className="max-w-6xl mx-auto grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] items-start">
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
              <div>
                <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full mb-3">
                  <Sparkles className="h-4 w-4" />
                  <span className="text-sm font-medium">Daily Style Quest</span>
                </div>
                <h1 className="heading-section">Style Challenges</h1>
                <p className="text-muted-foreground max-w-2xl">
                  Reduce decision fatigue with fun, daily quests and climb the leaderboard.
                </p>
              </div>

              <div className="bg-card border border-border rounded-xl p-6">
                {isLoading ? (
                  <div className="space-y-4 animate-pulse">
                    <div className="h-4 w-1/4 bg-muted rounded" />
                    <div className="h-8 w-3/4 bg-muted rounded" />
                    <div className="h-20 w-full bg-muted rounded" />
                  </div>
                ) : !quest ? (
                  <p className="text-muted-foreground">Loading today's quest…</p>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <CloudRain className="h-4 w-4" />
                          <span className="text-xs uppercase tracking-wide">Today</span>
                        </div>
                        <h2 className="text-xl font-semibold mt-2">{quest.title}</h2>
                        {quest.description && <p className="text-sm text-muted-foreground mt-2">{quest.description}</p>}
                      </div>
                      <Button variant="hero" onClick={submit} disabled={isSubmitting}>
                        {isSubmitting ? 'Submitting…' : 'Submit (Demo)'}
                      </Button>
                    </div>

                    <div className="grid md:grid-cols-3 gap-3">
                      {Object.entries(quest.constraint_json || {}).slice(0, 6).map(([k, v]) => (
                        <div key={k} className="rounded-lg border border-border bg-muted/30 p-3">
                          <p className="text-xs text-muted-foreground uppercase tracking-wide">{k}</p>
                          <p className="text-sm font-medium break-words">{String(v)}</p>
                        </div>
                      ))}
                    </div>

                    <div className="flex gap-3">
                      <Button variant="outline" asChild>
                        <a href="/outfits">Build outfit</a>
                      </Button>
                      <Button variant="outline" asChild>
                        <a href="/discover">Browse items</a>
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>

            <motion.aside initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
              <div className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-semibold flex items-center gap-2">
                    <Trophy className="h-4 w-4 text-accent" />
                    Leaderboard
                  </h2>
                  <span className="text-xs text-muted-foreground">{leaderboard.length} entries</span>
                </div>

                {leaderboard.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No submissions yet. Submit to become #1.</p>
                ) : (
                  <div className="space-y-2">
                    {leaderboard.slice(0, 10).map((e, i) => (
                      <motion.div
                        key={`${e.id}-${e.updated_at}`}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={createTransition({ delay: Math.min(i * 0.03, 0.2) })}
                        className="flex items-center justify-between rounded-lg border border-border bg-muted/30 p-3"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                            {i + 1}
                          </div>
                        <div>
                          <p className="text-sm font-medium">User {e.id.slice(-6)}</p>
                          <p className="text-xs text-muted-foreground">Level {e.level} • {e.total_points} points</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold">{e.total_points}</p>
                        <p className="text-xs text-muted-foreground">points</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.aside>
        </div>
      </div>
    </MainLayout>
    <ChatbotWidget />
  </>
  );
}
