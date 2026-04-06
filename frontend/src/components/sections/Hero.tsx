import { motion } from "framer-motion";
import Link from 'next/link';
import { ArrowRight, Sparkles, Camera } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createTransition } from "@/motion";
import { MagneticButton } from "@/components/ui/MagneticButton";
import { useParallax } from "@/motion";
import { SpotlightBackground } from "@/components/motion/SpotlightBackground";

export function Hero({
  onStartStyling,
  onTryItOn,
}: {
  onStartStyling: () => void;
  onTryItOn: () => void;
}) {
  const { ref: parallaxRef1, style: parallaxStyle1 } = useParallax({ speed: 0.18 });
  const { ref: parallaxRef2, style: parallaxStyle2 } = useParallax({ speed: 0.12 });

  return (
    <SpotlightBackground className="relative min-h-[92vh] overflow-hidden bg-background">
      {/* Animated luxury backdrop */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-hero opacity-45" />
        <div className="absolute inset-0 bg-gradient-to-r from-violet-500/10 via-blue-500/10 to-cyan-400/10 animate-gradient-shift" />

        <div
          ref={parallaxRef1}
          style={parallaxStyle1}
          className="absolute -top-28 left-1/3 w-[46rem] h-[46rem] rounded-full bg-gradient-to-r from-violet-500/25 to-blue-500/15 blur-3xl animate-pulse"
        />
        <div
          ref={parallaxRef2}
          style={parallaxStyle2}
          className="absolute -bottom-32 right-[-10rem] w-[42rem] h-[42rem] rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-400/10 blur-3xl animate-pulse [animation-delay:1.2s]"
        />

        <div
          className="absolute inset-0 opacity-[0.06] [background-image:radial-gradient(circle_at_10%_10%,white,transparent_35%),radial-gradient(circle_at_90%_20%,white,transparent_35%),radial-gradient(circle_at_20%_90%,white,transparent_35%),radial-gradient(circle_at_80%_80%,white,transparent_35%)]"
        />

        {/* Mouse-follow spotlight */}
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(800px circle at var(--spot-x) var(--spot-y), rgba(139,92,246,0.22), rgba(59,130,246,0.10) 26%, transparent 60%)",
            opacity: 0.9,
            transition: "opacity 200ms ease",
          }}
        />
      </div>

      <div className="relative z-10 container px-4 md:px-6 h-full mx-auto">
        <div className="min-h-[92vh] flex flex-col lg:flex-row items-center justify-between gap-10 py-16 lg:py-20">
          {/* Copy */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={createTransition({ duration: 0.35 })}
            className="w-full lg:max-w-xl"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/30 backdrop-blur-md px-4 py-2 text-sm font-medium text-foreground">
              <Sparkles className="h-4 w-4 text-accent" />
              <span>Confidence, Styled</span>
              <span className="text-muted-foreground">·</span>
              <span className="text-muted-foreground">AI fashion experience</span>
            </div>

            <h1 className="mt-6 text-gradient-gold font-bold tracking-tight leading-[1.02] text-5xl sm:text-6xl md:text-7xl lg:text-8xl">
              Wear Your Confidence
            </h1>

            <p className="mt-6 text-body text-muted-foreground max-w-xl">
              AI styling that matches your occasion—plus Try-On so you can see the look before you commit.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3 sm:gap-4">
              <MagneticButton className="rounded-full">
                <Button
                  size="lg"
                  className="rounded-full px-8 h-12 text-base shadow-lg bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400 active:scale-[0.98]"
                  onClick={onStartStyling}
                >
                  Start Styling
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </MagneticButton>

              <MagneticButton glow={false} className="rounded-full">
                <Button
                  size="lg"
                  variant="outline"
                  className="rounded-full px-8 h-12 text-base border-white/10 bg-card/20 glass-card hover:bg-card/30"
                  onClick={onTryItOn}
                >
                  <Camera className="mr-2 h-4 w-4" />
                  Try It On
                </Button>
              </MagneticButton>
            </div>

            <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="glass-panel rounded-2xl p-4">
                <p className="text-xs text-muted-foreground">Instant guidance</p>
                <p className="mt-1 text-sm font-semibold">Stylist-level suggestions</p>
              </div>
              <div className="glass-panel rounded-2xl p-4">
                <p className="text-xs text-muted-foreground">See the fit</p>
                <p className="mt-1 text-sm font-semibold">Try-On ready before buying</p>
              </div>
              <div className="glass-panel rounded-2xl p-4">
                <p className="text-xs text-muted-foreground">Build trust</p>
                <p className="mt-1 text-sm font-semibold">Clear steps, no guesswork</p>
              </div>
            </div>

            <div className="mt-7 text-xs text-muted-foreground">
              Already know your look?{" "}
              <Link className="text-accent hover:underline" href="/ai-stylist">
                Open the AI Stylist
              </Link>
            </div>
          </motion.div>

          {/* Visual */}
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 12 }}
            whileInView={{ opacity: 1, scale: 1, y: 0 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={createTransition({ duration: 0.4, delay: 0.1 })}
            className="w-full lg:w-[45%] max-w-[520px] mx-auto lg:mx-0"
          >
            <div className="relative">
              <div className="absolute -inset-5 bg-gradient-to-r from-violet-500/25 to-blue-500/20 blur-3xl rounded-[2.1rem]" />
              <div className="relative glass-panel rounded-[2.1rem] p-2 shadow-xl">
                <div className="relative overflow-hidden rounded-[1.8rem]">
                  <img
                    src="https://images.unsplash.com/photo-1520975916090-3105956dac38?w=1200&h=1400&fit=crop&q=80"
                    alt="Fashion model"
                    className="w-full h-[520px] object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />

                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={createTransition({ duration: 0.45 })}
                    className="absolute bottom-5 left-5 right-5"
                  >
                    <div className="glass-panel rounded-2xl p-4 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-full bg-black/30 ring-1 ring-white/10 flex items-center justify-center">
                          <span className="font-display text-xl font-bold tracking-wider text-white">C</span>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground">Outfit Match</p>
                          <p className="text-sm font-semibold text-foreground">92% confidence</p>
                        </div>
                      </div>
                      <div className="flex items-end gap-2">
                        <div className="w-24 h-2 rounded-full bg-white/10 overflow-hidden">
                          <div className="h-full w-[92%] bg-gradient-to-r from-violet-400 to-blue-400" />
                        </div>
                        <p className="text-xs font-semibold text-white/90">92%</p>
                      </div>
                    </div>
                  </motion.div>
                </div>

                {/* Floating chips */}
                <motion.div
                  initial={{ opacity: 0, x: -10, y: 10 }}
                  animate={{ opacity: 1, x: 0, y: 0 }}
                  transition={createTransition({ duration: 0.45, delay: 0.15 })}
                  className="absolute -top-3 left-5 glass-card rounded-2xl px-4 py-3 border-white/10"
                >
                  <p className="text-xs text-muted-foreground">Try-on suggestion</p>
                  <p className="mt-1 text-sm font-semibold">Confidence-fit, instantly</p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, x: 10, y: 10 }}
                  animate={{ opacity: 1, x: 0, y: 0 }}
                  transition={createTransition({ duration: 0.45, delay: 0.22 })}
                  className="absolute -bottom-4 right-5 glass-card rounded-2xl px-4 py-3 border-white/10"
                >
                  <p className="text-xs text-muted-foreground">AI styling</p>
                  <p className="mt-1 text-sm font-semibold">Occasion-aware curation</p>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </SpotlightBackground>
  );
}

