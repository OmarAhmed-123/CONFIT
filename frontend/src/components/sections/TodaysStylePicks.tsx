/**
 * CONFIT — Today's Style Picks
 * =============================
 * Personalized style recommendations based on user preferences,
 * style vector, and trending items.
 */

import { useState, useEffect, useMemo, useRef } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Heart,
  Eye,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  TrendingUp,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { getFeaturedProducts } from '@/services/mockData';
import { safeImageSrc } from '@/lib/imageFallback';
import { createTransition } from '@/motion';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Product } from '@/types';

interface StylePick {
  id: string;
  product: Product;
  matchScore: number;
  reason: string;
  tags: string[];
}

// Simulated AI-powered style matching
function generateStylePicks(products: Product[], userName?: string): StylePick[] {
  const reasons = [
    'Matches your minimalist aesthetic',
    'Perfect for your upcoming events',
    'Trending in your size',
    'Complements your wardrobe',
    'Highly rated by similar shoppers',
    'New arrival in your favorite brand',
    'Fits your budget preferences',
    'Popular for this season',
  ];

  const tags = [
    ['Minimalist', 'Versatile'],
    ['Occasion-Ready', 'Elegant'],
    ['Trending', 'Statement'],
    ['Wardrobe Essential', 'Classic'],
    ['New Arrival', 'Fresh'],
    ['Bestseller', 'Loved'],
  ];

  return products.slice(0, 8).map((product, index) => ({
    id: `pick-${product.id}`,
    product,
    matchScore: Math.floor(Math.random() * 15) + 85, // 85-99%
    reason: reasons[index % reasons.length],
    tags: tags[index % tags.length],
  }));
}

function StylePickCard({
  pick,
  index,
  onRefresh,
}: {
  pick: StylePick;
  index: number;
  onRefresh?: () => void;
}) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={createTransition({ duration: 0.4, delay: index * 0.08 })}
      className="relative group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="glass-panel rounded-3xl overflow-hidden border border-white/10 transition-all duration-300 group-hover:shadow-xl group-hover:border-white/20">
        {/* Image */}
        <Link href={`/product/${pick.product.id}`} className="block relative">
          <div className="relative overflow-hidden aspect-[3/4]">
            <img
              src={safeImageSrc(pick.product.images?.[0])}
              alt={pick.product.name}
              loading="lazy"
              decoding="async"
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

            {/* Match Score Badge */}
            <div className="absolute top-3 left-3">
              <Badge className="bg-gradient-to-r from-violet-500 to-blue-500 text-white border-0 px-3 py-1 rounded-full">
                <Sparkles className="h-3 w-3 mr-1" />
                {pick.matchScore}% Match
              </Badge>
            </div>

            {/* Hover Actions */}
            <AnimatePresence>
              {isHovered && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={createTransition({ duration: 0.2 })}
                  className="absolute bottom-3 left-3 right-3 flex gap-2"
                >
                  <Link
                    href="/try-on"
                    className="flex-1 inline-flex items-center justify-center gap-2 rounded-full bg-background/90 text-foreground border border-border/70 px-4 py-2.5 text-sm font-semibold hover:bg-background transition-colors backdrop-blur-sm"
                  >
                    <Eye className="h-4 w-4" />
                    Try On
                  </Link>
                  <button
                    className="inline-flex items-center justify-center rounded-full bg-white/20 text-white border border-white/20 p-2.5 hover:bg-white/30 transition-colors backdrop-blur-sm"
                    title="Add to wishlist"
                    aria-label="Add to wishlist"
                  >
                    <Heart className="h-4 w-4" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </Link>

        {/* Content */}
        <div className="p-4">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <p className="text-xs text-muted-foreground">{pick.product.brand}</p>
              <Link href={`/product/${pick.product.id}`}>
                <h3 className="font-semibold text-sm group-hover:text-accent transition-colors line-clamp-1">
                  {pick.product.name}
                </h3>
              </Link>
            </div>
            <p className="font-bold text-sm">${pick.product.price}</p>
          </div>

          {/* AI Reason */}
          <p className="text-xs text-muted-foreground mb-3 flex items-center gap-1">
            <Sparkles className="h-3 w-3 text-accent" />
            {pick.reason}
          </p>

          {/* Tags */}
          <div className="flex flex-wrap gap-1.5">
            {pick.tags.map((tag) => (
              <span
                key={tag}
                className="text-[10px] px-2 py-0.5 rounded-full bg-muted/50 text-muted-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.article>
  );
}

export function TodaysStylePicks() {
  const { user } = useAuth();
  const [picks, setPicks] = useState<StylePick[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [scrollPosition, setScrollPosition] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const userName = user?.name || 'there';

  // Generate picks on mount
  useEffect(() => {
    const products = getFeaturedProducts(12);
    setPicks(generateStylePicks(products, userName));
  }, [userName]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate AI refresh
    await new Promise((resolve) => setTimeout(resolve, 800));
    const products = getFeaturedProducts(12);
    setPicks(generateStylePicks(products, userName));
    setIsRefreshing(false);
  };

  const handleScroll = (direction: 'left' | 'right') => {
    if (!containerRef.current) return;
    const scrollAmount = 320;
    const newPosition = direction === 'left'
      ? scrollPosition - scrollAmount
      : scrollPosition + scrollAmount;
    containerRef.current.scrollTo({ left: newPosition, behavior: 'smooth' });
    setScrollPosition(newPosition);
  };

  return (
    <section className="py-14 md:py-20 bg-background">
      <div className="container px-4 md:px-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <Badge variant="secondary" className="text-xs">
                <TrendingUp className="h-3 w-3 mr-1" />
                AI Curated
              </Badge>
            </div>
            <h2 className="heading-section">
              {user ? `${userName}'s Style Picks` : "Today's Style Picks"}
            </h2>
            <p className="mt-2 text-body text-muted-foreground max-w-xl">
              Personalized recommendations based on your style preferences and what's trending now.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              className="rounded-full gap-2"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
              Refresh
            </Button>
            <div className="hidden md:flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                className="rounded-full h-9 w-9"
                onClick={() => handleScroll('left')}
                disabled={scrollPosition <= 0}
                title="Scroll left"
                aria-label="Scroll left"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="rounded-full h-9 w-9"
                onClick={() => handleScroll('right')}
                title="Scroll right"
                aria-label="Scroll right"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Picks Grid */}
        <div
          ref={containerRef}
          className="flex gap-4 overflow-x-auto no-scrollbar snap-x snap-mandatory pb-4 -mx-4 px-4"
          onScroll={(e) => setScrollPosition((e.target as HTMLDivElement).scrollLeft)}
        >
          {picks.map((pick, index) => (
            <div key={pick.id} className="snap-start w-[260px] md:w-[280px] shrink-0">
              <StylePickCard pick={pick} index={index} />
            </div>
          ))}
        </div>

        {/* Empty State */}
        {picks.length === 0 && (
          <div className="text-center py-12">
            <Sparkles className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">
              Sign in to get personalized style recommendations
            </p>
            <Link href="/login">
              <Button className="mt-4 rounded-full">Sign In</Button>
            </Link>
          </div>
        )}

        {/* Footer CTA */}
        <div className="mt-8 flex items-center justify-between">
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Updated {new Date().toLocaleDateString()}
          </p>
          <Link
            href="/products"
            className="text-sm font-medium text-accent hover:underline flex items-center gap-1"
          >
            View all recommendations
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

export default TodaysStylePicks;
