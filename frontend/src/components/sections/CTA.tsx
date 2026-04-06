import { Sparkles, Camera, ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { createTransition } from "@/motion";

export function CTA({
  onStartStyling,
  onTryItOn,
}: {
  onStartStyling: () => void;
  onTryItOn: () => void;
}) {
  return (
    <section className="py-16 md:py-24 bg-background">
      <div className="container px-4 md:px-6">
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={createTransition({ duration: 0.4 })}
          className="rounded-[2.2rem] overflow-hidden border border-white/10 glass-panel"
        >
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-violet-500/20 via-blue-500/10 to-cyan-400/10" />
            <div className="absolute inset-0 opacity-[0.10] [background-image:linear-gradient(rgba(255,255,255,0.6)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.6)_1px,transparent_1px)] [background-size:8px_8px] [mask-image:radial-gradient(circle_at_50%_40%,black_60%,transparent_100%)]" />

            <div className="relative px-6 md:px-10 py-12 md:py-16">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
                <div className="lg:col-span-2">
                  <div className="inline-flex items-center gap-2 rounded-full bg-background/40 backdrop-blur-md border border-white/10 px-4 py-2 text-sm font-medium text-foreground">
                    <Sparkles className="h-4 w-4 text-accent" />
                    <span>CONFIDENCE, STYLED</span>
                  </div>

                  <h2 className="mt-5 font-bold tracking-tight leading-[1.05] text-4xl sm:text-5xl md:text-6xl">
                    “I finally know what to wear.”
                  </h2>
                  <p className="mt-5 text-body text-muted-foreground max-w-2xl">
                    Start styling in seconds. Try on instantly. Edit until it feels like your signature.
                  </p>

                  <div className="mt-6 flex flex-wrap gap-3">
                    {[
                      { label: "Luxury clarity", icon: ShieldCheck },
                      { label: "No guesswork", icon: Sparkles },
                      { label: "Fast refinements", icon: Camera },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="inline-flex items-center gap-2 rounded-full bg-background/40 border border-white/10 px-4 py-2"
                      >
                        <item.icon className="h-4 w-4 text-accent" />
                        <span className="text-sm font-semibold">{item.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="lg:col-span-1 flex flex-col gap-3">
                  <Button
                    size="lg"
                    className="rounded-full h-12 bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400 shadow-lg"
                    onClick={onStartStyling}
                  >
                    Start Styling
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    className="rounded-full h-12 border-white/10 bg-card/20 glass-card hover:bg-card/30"
                    onClick={onTryItOn}
                  >
                    <Camera className="mr-2 h-4 w-4" />
                    Try It On
                  </Button>

                  <p className="text-xs text-muted-foreground mt-2">
                    Designed to build trust—so you can move with confidence.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

