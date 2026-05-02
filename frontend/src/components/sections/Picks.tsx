import { motion } from "framer-motion";
import Link from 'next/link';
import { Eye, Shirt, Sparkles, Plus } from "lucide-react";
import { getFeaturedProducts } from "@/services/mockData";
import { safeImageSrc } from "@/lib/imageFallback";
import { createTransition } from "@/motion";
import type { Product } from "@/types";

function ProductPickCard({ product, index }: { product: Product; index: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={createTransition({ duration: 0.35, delay: index * 0.03 })}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.985 }}
      className="snap-start w-[280px] sm:w-[320px] shrink-0"
    >
      <div className="group glass-panel rounded-3xl p-3 border-white/10 transition-shadow duration-300 relative overflow-hidden">
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{
            backgroundImage:
              "radial-gradient(700px circle at 15% 20%, rgba(139,92,246,0.25), transparent 58%), radial-gradient(600px circle at 90% 55%, rgba(59,130,246,0.16), transparent 55%)",
          }}
        />
        <div className="relative overflow-hidden rounded-2xl bg-muted">
          <Link href={`/product/${product.id}`} className="block">
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <img
              src={safeImageSrc(product.images?.[0])}
              alt={product.name}
              loading="lazy"
              decoding="async"
              className="w-full h-[360px] object-cover transition-transform duration-500 group-hover:scale-105"
            />
          </Link>

          {/* Hover reveal actions */}
          <div className="absolute bottom-3 left-3 right-3 opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 transition-all duration-300 flex gap-2">
            <Link
              href="/try-on"
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-full bg-background/90 text-foreground border border-border/70 px-4 py-2 text-xs font-semibold hover:bg-background transition-colors"
            >
              <Eye className="h-3.5 w-3.5" />
              Try On
            </Link>
            <Link
              href="/outfits"
              className="inline-flex items-center justify-center rounded-full bg-accent/20 text-accent-foreground border border-white/10 px-3 py-2 text-xs font-semibold hover:bg-accent/30 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        <div className="mt-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs text-muted-foreground">{product.brand}</p>
            <h3 className="mt-1 text-sm font-semibold tracking-tight group-hover:text-accent transition-colors line-clamp-1">
              {product.name}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 border border-white/10 px-3 py-1 text-xs font-semibold text-accent">
              <Sparkles className="h-3.5 w-3.5" />
              {product.styleCompatibility}%
            </span>
          </div>
        </div>
      </div>
    </motion.article>
  );
}

export function Picks() {
  const products = getFeaturedProducts(12);

  return (
    <section className="py-14 md:py-20 bg-background">
      <div className="container px-4 md:px-6">
        <div className="flex items-end justify-between gap-6 mb-6">
          <div className="max-w-xl">
            <h2 className="heading-section">Today’s Picks</h2>
            <p className="mt-3 text-body text-muted-foreground">
              Swipe curated pieces designed to make your “I know what to wear” feeling effortless.
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
            <Shirt className="h-4 w-4" />
            <span>Swipe to discover</span>
          </div>
        </div>

        <div className="relative">
          <div className="flex gap-3 overflow-x-auto no-scrollbar snap-x snap-mandatory pb-2">
            {products.map((product, index) => (
              <ProductPickCard key={product.id} product={product} index={index} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

