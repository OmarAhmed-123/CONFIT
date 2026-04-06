import React, { useMemo } from "react";
import { useRouter } from 'next/navigation';
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, ShieldCheck, Camera, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlowCard } from "@/components/ui/GlowCard";
import { MagneticButton } from "@/components/ui/MagneticButton";
import { useABExperiment } from "@/lib/experiments/useABExperiment";
import { apiUrl } from "@/lib/api";
import { FloatingDecor } from "@/components/motion/FloatingDecor";
import { SpotlightBackground } from "@/components/motion/SpotlightBackground";

type HeroVariant = {
  headline: string;
  subhead: string;
  cta: string;
};

export default function InvestorLanding() {
  const router = useRouter();

  const heroVariants: HeroVariant[] = useMemo(
    () => [
      {
        headline: "Invest in Confidence, Styled.",
        subhead: "CONFIT turns natural language into premium, budget-aware outfit builds—then makes every refinement feel inevitable.",
        cta: "See the live demo",
      },
      {
        headline: "A billion-dollar AI closet experience.",
        subhead: "Stylish JSON-first AI + interactive try-on loops. Confidence, clarity, trust—designed to convert.",
        cta: "Start styling now",
      },
    ],
    []
  );

  const { variantValue: hero, variantId, track } = useABExperiment<HeroVariant>({
    experimentId: "investor-hero",
    variants: [
      { id: "A", value: heroVariants[0] },
      { id: "B", value: heroVariants[1] },
    ],
    exposureEvent: "hero_exposure",
    weights: [0.5, 0.5],
  });

  const onPrimaryCTA = async () => {
    track("cta_click", { variantId });
    // Best-effort: log a lightweight client-side event for debugging.
    void fetch(apiUrl("/api/experiments/track"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ experimentId: "investor-hero", variant: variantId, event: "cta_click_local", metadata: {} }),
    }).catch(() => undefined);

    router.push("/");
    const el = document.getElementById("confit-ai-experience");
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="min-h-screen bg-background">
      <SpotlightBackground className="relative overflow-hidden">
        <div
          aria-hidden
          className="absolute inset-0 opacity-90 animate-gradient-shift"
          style={{
            background:
              "linear-gradient(135deg, rgba(139,92,246,0.20) 0%, rgba(59,130,246,0.12) 55%, rgba(6,182,212,0.08) 100%)",
          }}
        />
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 10%, rgba(139,92,246,0.25), transparent 50%), radial-gradient(circle at 80% 20%, rgba(59,130,246,0.18), transparent 55%)",
            mixBlendMode: "screen",
          }}
        />

        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage:
              "radial-gradient(800px circle at var(--spot-x) var(--spot-y), rgba(139,92,246,0.22), rgba(59,130,246,0.10) 26%, transparent 60%)",
            opacity: 0.85,
            transition: "opacity 200ms ease",
          }}
        />

        <div className="container px-4 md:px-6 relative py-16 md:py-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
            className="max-w-3xl"
          >
            <div className="inline-flex items-center gap-2 rounded-full bg-background/40 backdrop-blur-md border border-white/10 px-4 py-2 text-sm font-medium text-foreground">
              <Sparkles className="h-4 w-4 text-accent" />
              <span>CONFIT · Investor Preview</span>
              <span className="text-muted-foreground">·</span>
              <span className="text-muted-foreground">Variant {variantId}</span>
            </div>

            <h1 className="mt-6 font-display font-bold tracking-tight leading-[1.05] text-4xl sm:text-5xl md:text-6xl">
              {hero.headline}
            </h1>

            <p className="mt-5 text-body text-muted-foreground max-w-2xl">{hero.subhead}</p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3 sm:items-center">
              <MagneticButton strength={10} maxTranslate={12}>
                <button
                  type="button"
                  onClick={onPrimaryCTA}
                  className="relative inline-flex items-center justify-center rounded-full h-12 px-6 text-white bg-gradient-to-r from-violet-500 to-blue-500 shadow-lg hover:from-violet-400 hover:to-blue-400 transition"
                >
                  <span className="font-semibold">{hero.cta}</span>
                  <ArrowRight className="ml-2 h-5 w-5" />
                </button>
              </MagneticButton>

              <Button
                variant="outline"
                className="rounded-full border-white/10 bg-card/20 glass-card hover:bg-card/30"
                onClick={() => router.push("/ai-stylist")}
              >
                <ShieldCheck className="mr-2 h-4 w-4 text-accent" />
                Try the stylist
              </Button>
            </div>

            <div className="mt-4">
              <Button
                variant="outline"
                className="rounded-full border-white/10 bg-card/20 glass-card hover:bg-card/30"
                onClick={() => router.push("/investor/pitch")}
              >
                <Sparkles className="mr-2 h-4 w-4 text-accent" />
                View investor pitch deck
              </Button>
            </div>

            <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <FloatingDecor delayMs={0}>
                <GlowCard className="p-5">
                  <Camera className="h-5 w-5 text-accent" />
                  <p className="mt-3 text-sm font-semibold">Try-on loop</p>
                  <p className="mt-1 text-xs text-muted-foreground">Edit until it feels like your signature.</p>
                </GlowCard>
              </FloatingDecor>
              <FloatingDecor delayMs={450}>
                <GlowCard className="p-5">
                  <Zap className="h-5 w-5 text-accent" />
                  <p className="mt-3 text-sm font-semibold">Fast confidence</p>
                  <p className="mt-1 text-xs text-muted-foreground">Instant clarity with progressive disclosure.</p>
                </GlowCard>
              </FloatingDecor>
              <FloatingDecor delayMs={900}>
                <GlowCard className="p-5">
                  <ShieldCheck className="h-5 w-5 text-accent" />
                  <p className="mt-3 text-sm font-semibold">Trust by design</p>
                  <p className="mt-1 text-xs text-muted-foreground">Budget-aware, color-harmonized builds.</p>
                </GlowCard>
              </FloatingDecor>
            </div>
          </motion.div>
        </div>
      <section className="container px-4 md:px-6 py-12 md:py-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-10">
          <GlowCard className="p-6">
            <h2 className="heading-card heading-card">Problem</h2>
            <p className="mt-3 text-body text-muted-foreground">
              Fashion discovery is noisy. Users bounce because it’s unclear, slow, and too many choices feel like risk.
            </p>
          </GlowCard>

          <GlowCard className="p-6">
            <h2 className="heading-card heading-card">Solution</h2>
            <p className="mt-3 text-body text-muted-foreground">
              CONFIT translates intent into structured outfit builds—then turns refinement into a confidence loop.
            </p>
          </GlowCard>
        </div>

        <div className="mt-8 md:mt-10 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
          {[
            { title: "Demo", desc: "Prompt → thinking → outfit → edit → try-on.", icon: Sparkles },
            { title: "Features", desc: "JSON-first AI, budget optimizer, smart alternatives, trust cues.", icon: ShieldCheck },
            { title: "Vision", desc: "From closet to community—social styling at scale.", icon: Camera },
          ].map((item) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.5, ease: "easeInOut" }}
            >
              <GlowCard className="p-6 h-full">
                <item.icon className="h-5 w-5 text-accent" />
                <p className="mt-3 text-sm font-semibold">{item.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{item.desc}</p>
              </GlowCard>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="relative overflow-hidden pb-16 md:pb-20">
        <div className="container px-4 md:px-6">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.6, ease: "easeInOut" }}
          >
            <GlowCard className="p-8 rounded-[2rem] border-white/10 animate-glow-pulse">
              <div className="flex flex-col lg:flex-row gap-6 lg:items-center lg:justify-between">
                <div className="max-w-2xl">
                  <div className="inline-flex items-center gap-2 rounded-full bg-background/40 backdrop-blur-md border border-white/10 px-4 py-2 text-sm font-medium text-foreground">
                    <Sparkles className="h-4 w-4 text-accent" />
                    <span>CONFIT · Growth Loop</span>
                  </div>
                  <h2 className="mt-5 font-display font-bold tracking-tight leading-[1.05] text-3xl sm:text-4xl">
                    Outfit sharing + referrals = viral AI looks.
                  </h2>
                  <p className="mt-3 text-body text-muted-foreground">
                    Users don’t just get an outfit—they want to keep exploring and proving their confidence.
                  </p>
                </div>

                <div className="flex gap-3 flex-wrap">
                  <Button className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400 shadow-lg h-12 px-6">
                    Fund CONFIT
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                  <Button
                    variant="outline"
                    className="rounded-full border-white/10 bg-card/20 glass-card hover:bg-card/30 h-12 px-6"
                    onClick={onPrimaryCTA}
                  >
                    {hero.cta}
                  </Button>
                </div>
              </div>
            </GlowCard>
          </motion.div>
        </div>
      </section>
      </SpotlightBackground>
    </div>
  );
}

