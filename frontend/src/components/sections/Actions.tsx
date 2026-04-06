import { Sparkles, Camera, Wand2, ArrowRight } from "lucide-react";
import Link from 'next/link';
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { createTransition } from "@/motion";
import { MagneticButton } from "@/components/ui/MagneticButton";

const actions = [
  {
    id: "build",
    title: "Build an Outfit",
    description: "Mix pieces with AI guidance for a confident finish.",
    icon: Wand2,
    href: "/outfits",
  },
  {
    id: "tryon",
    title: "Try It On",
    description: "See the look before you buy—premium, photo-ready.",
    icon: Camera,
    href: "/try-on",
  },
  {
    id: "style",
    title: "Find My Style",
    description: "Tell us what you want—we'll curate options that fit you.",
    icon: Sparkles,
    href: null,
  },
];

export function Actions({ onFindMyStyle }: { onFindMyStyle: () => void }) {
  return (
    <section className="py-14 md:py-20 bg-secondary/20">
      <div className="container px-4 md:px-6">
        <div className="text-center mb-10">
          <h2 className="heading-section">Quick Actions</h2>
          <p className="mt-4 text-muted-foreground mx-auto max-w-xl text-body">
            Choose a path. Each one takes you closer to “this is exactly what I needed.”
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {actions.map((action, index) => {
            const Icon = action.icon;
            const href = action.href;

            const content = (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={createTransition({ duration: 0.35, delay: index * 0.06 })}
                whileHover={{ scale: 1.06 }}
                whileTap={{ scale: 0.98 }}
                className="group h-full"
              >
                <div className="glass-panel rounded-3xl p-6 md:p-7 h-full border-white/10 transition-shadow duration-300 group-hover:shadow-xl">
                  <div className="flex items-start justify-between gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-violet-500/18 to-blue-500/12 border border-white/10 flex items-center justify-center">
                      <Icon className="h-6 w-6 text-accent" />
                    </div>

                    <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
                      <span>CONFIT</span>
                      <span className="w-1 h-1 rounded-full bg-current/50" />
                      <span className="font-semibold">{index + 1}/3</span>
                    </div>
                  </div>

                  <h3 className="mt-5 text-xl font-semibold tracking-tight group-hover:text-accent transition-colors">
                    {action.title}
                  </h3>
                  <p className="mt-3 text-body-sm text-muted-foreground">{action.description}</p>

                  <div className="mt-6 flex items-center justify-between">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="rounded-full px-3 text-sm opacity-100 bg-transparent hover:bg-white/5 hover:text-accent"
                    >
                      <span className="font-semibold">Start</span>
                      <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </Button>

                    <span className="text-xs text-muted-foreground">Luxury flow</span>
                  </div>
                </div>
              </motion.div>
            );

            if (href) {
              return (
                <MagneticButton key={action.id} className="block h-full" strength={12}>
                  <Link href={href} className="block h-full">
                    {content}
                  </Link>
                </MagneticButton>
              );
            }

            return (
              <MagneticButton key={action.id} className="block w-full" strength={12}>
                <button type="button" className="text-left w-full" onClick={onFindMyStyle}>
                  {content}
                </button>
              </MagneticButton>
            );
          })}
        </div>
      </div>
    </section>
  );
}

