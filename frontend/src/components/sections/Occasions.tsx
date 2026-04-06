import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Sparkles, Briefcase, CalendarDays, PartyPopper, Coffee } from "lucide-react";
import { createTransition } from "@/motion";

type OccasionId = "work" | "wedding" | "party" | "casual";

const OCCASIONS: Array<{
  id: OccasionId;
  label: string;
  icon: ReactNode;
  prompt: string;
}> = [
  {
    id: "work",
    label: "Work",
    icon: <Briefcase className="h-5 w-5" />,
    prompt: "I need an outfit for work that feels polished, confident, and comfortable.",
  },
  {
    id: "wedding",
    label: "Wedding",
    icon: <CalendarDays className="h-5 w-5" />,
    prompt: "I need an outfit for a wedding under $150. Elevated, flattering, and photo-ready.",
  },
  {
    id: "party",
    label: "Party",
    icon: <PartyPopper className="h-5 w-5" />,
    prompt: "I need an outfit for a party—bold, elevated, and unforgettable.",
  },
  {
    id: "casual",
    label: "Casual",
    icon: <Coffee className="h-5 w-5" />,
    prompt: "I need a casual outfit that still looks premium—effortless and clean.",
  },
];

export function Occasions({
  onSelectOccasion,
}: {
  onSelectOccasion: (occasion: OccasionId, prompt: string) => void;
}) {
  return (
    <section className="py-14 md:py-20 bg-secondary/10">
      <div className="container px-4 md:px-6">
        <div className="text-center mb-10">
          <h2 className="heading-section">Occasions</h2>
          <p className="mt-4 text-body text-muted-foreground max-w-2xl mx-auto">
            Pick where you’re going. We’ll translate your moment into a look that feels like you.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {OCCASIONS.map((occasion, index) => (
            <motion.button
              key={occasion.id}
              type="button"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={createTransition({ duration: 0.35, delay: index * 0.05 })}
              whileHover={{ scale: 1.06, y: -4 }}
              whileTap={{ scale: 0.985 }}
              className="text-left group rounded-3xl glass-panel border-white/10 p-6 md:p-7 transition-shadow duration-300 cursor-pointer relative overflow-hidden"
              onClick={() => onSelectOccasion(occasion.id, occasion.prompt)}
            >
                <span
                  aria-hidden
                  className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  style={{
                    backgroundImage:
                      "radial-gradient(800px circle at 20% 10%, rgba(139,92,246,0.25), transparent 60%), radial-gradient(600px circle at 80% 70%, rgba(59,130,246,0.18), transparent 55%)",
                    filter: "blur(2px)",
                  }}
                />
              <div className="flex items-center justify-between gap-4">
                <div className="w-12 h-12 rounded-2xl border border-white/10 bg-gradient-to-r from-violet-500/20 to-blue-500/12 flex items-center justify-center">
                  {occasion.icon}
                </div>
                <div className="hidden sm:flex items-center gap-1 text-xs text-muted-foreground">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>AI</span>
                </div>
              </div>

              <h3 className="mt-6 text-xl font-semibold tracking-tight group-hover:text-accent transition-colors">
                {occasion.label}
              </h3>
              <p className="mt-3 text-body-sm text-muted-foreground">
                Tap to generate a confident look for this moment.
              </p>

              <div className="mt-6 flex items-center justify-between">
                <span className="text-xs font-semibold text-accent">Curate now</span>
                <span className="text-xs text-muted-foreground">Luxury lift</span>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </section>
  );
}

