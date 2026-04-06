import { useMemo } from "react";
import Link from 'next/link';
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createTransition } from "@/motion";
import { featuredOutfits } from "@/services/mockData";

type Look = {
  id: string;
  name: string;
  occasion: string;
  totalPrice: number;
  styleScore: number;
  image: string;
};

const LOOK_IMAGES = [
  "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=900&h=1100&fit=crop&q=80",
  "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=900&h=1100&fit=crop&q=80",
  "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=900&h=1100&fit=crop&q=80",
  "https://images.unsplash.com/photo-1550614000-4b9519879354?w=900&h=1100&fit=crop&q=80",
  "https://images.unsplash.com/photo-1520975916090-3105956dac38?w=900&h=1100&fit=crop&q=80",
  "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=900&h=1100&fit=crop&q=80",
];

function buildLooks(): Look[] {
  const base = (featuredOutfits ?? []) as any[];
  const results: Look[] = [];
  for (let i = 0; i < Math.min(base.length + 2, 6); i += 1) {
    const f = base[i] ?? base[i % base.length];
    results.push({
      id: f?.id || `trending-${i}`,
      name: f?.name || ["Velvet Confidence", "City Elegance", "Soft Power", "Gala Glow", "Modern Muse", "After Hours"][i]!,
      occasion: f?.occasion || ["work", "wedding", "party", "casual"][i % 4]!,
      totalPrice: Number(f?.totalPrice ?? 380 + i * 80),
      styleScore: Number(f?.styleScore ?? 88 + i * 2),
      image: LOOK_IMAGES[i]!,
    });
  }
  return results;
}

export function Trending() {
  const looks = useMemoLooks();

  return (
    <section className="py-14 md:py-20 bg-secondary/20">
      <div className="container px-4 md:px-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/20 backdrop-blur-md px-4 py-2 text-sm font-medium text-foreground">
              <Sparkles className="h-4 w-4 text-accent" />
              <span>Trending Looks</span>
            </div>
            <h2 className="mt-4 heading-section">What everyone is styling right now</h2>
            <p className="mt-3 text-body text-muted-foreground">
              Tap in and build your version—confidence included.
            </p>
          </div>

          <Button variant="outline" asChild className="rounded-full border-white/10 bg-card/20">
            <Link href="/discover">
              Explore all
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {looks.map((look, index) => (
            <motion.div
              key={`${look.id}-${index}`}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={createTransition({ duration: 0.35, delay: index * 0.06 })}
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.985 }}
              className="group"
            >
              <div className="glass-panel rounded-3xl border-white/10 overflow-hidden">
                <div className="relative aspect-[4/5]">
                  <img
                    src={look.image}
                    alt={look.name}
                    loading="lazy"
                    decoding="async"
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-80" />
                  <div className="absolute top-4 left-4">
                    <span className="inline-flex items-center rounded-full bg-white/10 border border-white/10 px-3 py-1 text-xs font-semibold text-white">
                      {look.styleScore}% match
                    </span>
                  </div>

                  {/* Hover expand content */}
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    whileHover={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, ease: "easeInOut" }}
                    className="absolute bottom-4 left-4 right-4"
                  >
                    <div className="bg-background/70 backdrop-blur-md border border-border/70 rounded-2xl p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs text-muted-foreground">For {look.occasion}</p>
                          <h3 className="mt-1 text-lg font-semibold text-foreground tracking-tight">
                            {look.name}
                          </h3>
                        </div>
                        <p className="text-sm font-semibold text-foreground whitespace-nowrap">
                          ${look.totalPrice}
                        </p>
                      </div>
                      <div className="mt-3">
                        <Button
                          variant="gold"
                          size="sm"
                          className="w-full rounded-full shadow-md"
                          asChild
                        >
                          <Link href="/outfits">
                            <ShoppingBag className="mr-2 h-4 w-4" />
                            Shop this look
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function useMemoLooks() {
  const looks = useMemo(() => buildLooks(), []);
  return looks;
}

