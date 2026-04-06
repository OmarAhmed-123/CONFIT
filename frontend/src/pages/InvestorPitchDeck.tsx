import React, { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Sparkles } from "lucide-react";

import { apiUrl } from "@/lib/api";
import { useABExperiment } from "@/lib/experiments/useABExperiment";
import { GlowCard } from "@/components/ui/GlowCard";
import { MagneticButton } from "@/components/ui/MagneticButton";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpotlightBackground } from "@/components/motion/SpotlightBackground";

type PitchDeckSlide = {
  id: string;
  title: string;
  bullets: string[];
};

type PitchDeckResponse = {
  deckTitle: string;
  variant: "A" | "B";
  slides: PitchDeckSlide[];
};

export default function InvestorPitchDeck() {
  const { variantValue: deckVariant, variantId, track } = useABExperiment<"A" | "B">({
    experimentId: "investor-pitch-deck",
    variants: [
      { id: "A", value: "A" },
      { id: "B", value: "B" },
    ],
    exposureEvent: "pitch_deck_exposure",
    weights: [0.5, 0.5],
  });

  const [deck, setDeck] = useState<PitchDeckResponse | null>(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const canPrev = activeIdx > 0;
  const canNext = deck ? activeIdx < deck.slides.length - 1 : false;

  const deckSlides = useMemo(() => deck?.slides ?? [], [deck]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        setIsLoading(true);
        const res = await fetch(apiUrl(`/api/pitch/deck?variant=${encodeURIComponent(deckVariant)}`), {
          headers: { Accept: "application/json" },
        });
        const data = (await res.json()) as PitchDeckResponse;
        if (cancelled) return;
        setDeck(data);
        setActiveIdx(0);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [deckVariant]);

  const onPrev = () => {
    track("slide_prev", { variantId, activeIdx });
    setActiveIdx((v) => Math.max(0, v - 1));
  };

  const onNext = () => {
    track("slide_next", { variantId, activeIdx });
    setActiveIdx((v) => Math.min((deck?.slides.length ?? 1) - 1, v + 1));
  };

  return (
    <SpotlightBackground className="min-h-screen bg-background" defaultSpotX="50%" defaultSpotY="20%">
      <div className="container px-4 md:px-6 py-10 md:py-14">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
          <GlowCard className="p-6 md:p-8 w-full md:max-w-xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-background/40 backdrop-blur-md border border-white/10 px-4 py-2 text-sm font-medium text-foreground">
              <Sparkles className="h-4 w-4 text-accent" />
              <span>{deck?.deckTitle ?? "CONFIT — Investor Pitch"}</span>
              <span className="text-muted-foreground">·</span>
              <span className="text-muted-foreground">Variant {variantId}</span>
            </div>

            <div className="mt-5">
              <div className="flex items-center gap-3">
                <div className="text-sm text-muted-foreground">
                  Slide {Math.min(activeIdx + 1, deckSlides.length || 1)} / {deckSlides.length || 1}
                </div>
              </div>

              <div className="mt-3 h-2 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-violet-500 to-blue-500"
                  initial={false}
                  animate={{
                    width:
                      deckSlides.length > 0
                        ? `${((activeIdx + 1) / deckSlides.length) * 100}%`
                        : "0%",
                  }}
                  transition={{ duration: 0.35, ease: "easeInOut" }}
                />
              </div>
            </div>
          </GlowCard>

          <GlowCard className="p-6 md:p-8 w-full md:max-w-md">
            <div className="font-display font-bold tracking-tight leading-tight text-xl text-foreground">
              Auto-generated deck
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Navigate slides to preview the story investors see.
            </p>

            <div className="mt-6 flex gap-3">
              <MagneticButton strength={8} maxTranslate={10}>
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-full border-white/10 bg-card/20 glass-card hover:bg-card/30 w-full"
                  onClick={onPrev}
                  disabled={!canPrev || isLoading}
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Prev
                </Button>
              </MagneticButton>
              <MagneticButton strength={10} maxTranslate={10}>
                <Button
                  type="button"
                  className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white shadow-lg hover:from-violet-400 hover:to-blue-400 transition w-full"
                  onClick={onNext}
                  disabled={!canNext || isLoading}
                >
                  Next
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </MagneticButton>
            </div>
          </GlowCard>
        </div>

        <div className="mt-6 md:mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GlowCard className="p-6 md:p-8">
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <Skeleton className="h-9 w-2/3" />
                  <div className="mt-4 space-y-3">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-4 w-4/6" />
                  </div>
                </motion.div>
              ) : deckSlides.length === 0 ? (
                <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <div className="text-sm text-muted-foreground">No slides available.</div>
                </motion.div>
              ) : (
                <motion.div
                  key={deckSlides[activeIdx]?.id ?? "slide"}
                  initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  exit={{ opacity: 0, y: -10, filter: "blur(8px)" }}
                  transition={{ duration: 0.35, ease: "easeInOut" }}
                >
                  <div className="font-display font-bold tracking-tight leading-tight text-3xl text-foreground">
                    {deckSlides[activeIdx]?.title}
                  </div>
                  <div className="mt-4 space-y-2">
                    {(deckSlides[activeIdx]?.bullets ?? []).map((b, idx) => (
                      <div key={`${deckSlides[activeIdx]?.id ?? "s"}-b-${idx}`} className="flex gap-3">
                        <div className="mt-1 h-1.5 w-1.5 rounded-full bg-accent" />
                        <div className="text-body text-foreground/90">{b}</div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </GlowCard>

          <GlowCard className="p-6 md:p-8">
            <div className="font-display font-bold tracking-tight leading-tight text-xl text-foreground">
              Slide list
            </div>
            <p className="mt-2 text-sm text-muted-foreground">Tap to jump. The story is sequential.</p>

            <div className="mt-5 space-y-3">
              {deckSlides.map((s, idx) => {
                const isActive = idx === activeIdx;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      track("slide_jump", { variantId, activeIdx: idx });
                      setActiveIdx(idx);
                    }}
                    className={[
                      "w-full text-left rounded-2xl border p-4 transition",
                      isActive
                        ? "border-white/15 bg-background/40 backdrop-blur-md shadow-lg"
                        : "border-white/10 bg-card/10 hover:bg-card/20",
                    ].join(" ")}
                    disabled={isLoading}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="font-semibold">{s.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {idx + 1}/{deckSlides.length}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </GlowCard>
        </div>
      </div>
    </SpotlightBackground>
  );
}

