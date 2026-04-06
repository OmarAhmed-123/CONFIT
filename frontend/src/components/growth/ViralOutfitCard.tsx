import { motion } from 'framer-motion';
import Link from 'next/link';
import { ShoppingBag, Share2, Sparkles, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import type { ViralFeedPost } from '@/lib/api/growth';
import { createTransition } from '@/motion';

interface ViralOutfitCardProps {
  post: ViralFeedPost;
  onShare?: (post: ViralFeedPost) => void;
  className?: string;
}

/** Micro-animations: engagement pulse from predicted probability, trend tick. */
export function ViralOutfitCard({ post, onShare, className }: ViralOutfitCardProps) {
  const eng = post.engagement_probability ?? 0;
  const pulseScale = 1 + Math.min(0.08, eng * 0.1);

  const creatorPath = post.creator.influencer_id
    ? `/influencer/${post.creator.influencer_id}`
    : `/profile`;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={createTransition({ duration: 0.35 })}
      className={cn(
        'rounded-2xl border border-border/60 bg-card/80 overflow-hidden shadow-sm backdrop-blur-sm',
        className
      )}
    >
      <div className="relative aspect-[3/4] bg-muted">
        {post.outfit_image_url ? (
          <img
            src={post.outfit_image_url}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground text-sm">No image</div>
        )}

        {post.try_on_preview_url && (
          <motion.div
            className="absolute bottom-3 left-3 right-3 flex gap-2 rounded-xl bg-black/55 p-2 backdrop-blur-md"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <img
              src={post.try_on_preview_url}
              alt="Try-on preview"
              className="h-16 w-14 rounded-lg object-cover ring-2 ring-white/30"
            />
            <div className="flex flex-col justify-center text-[10px] uppercase tracking-wider text-white/90">
              <span className="font-semibold">Try-on</span>
              <span className="text-white/70">Live preview</span>
            </div>
          </motion.div>
        )}

        <motion.div
          className="absolute top-3 right-3 flex items-center gap-1 rounded-full bg-black/45 px-2 py-1 text-[10px] font-medium text-white backdrop-blur"
          animate={{ scale: [1, pulseScale, 1] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
        >
          <Sparkles className="h-3 w-3 text-amber-300" />
          {(eng * 100).toFixed(0)}%
        </motion.div>
      </div>

      <div className="space-y-3 p-4">
        <div className="flex items-center justify-between gap-2">
          <Link href={creatorPath} className="flex min-w-0 items-center gap-2 hover:opacity-90">
            <Avatar className="h-9 w-9 border border-border">
              <AvatarImage src={post.creator.avatar_url ?? undefined} />
              <AvatarFallback>{post.creator.display_name?.slice(0, 2) ?? 'CR'}</AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold leading-tight">{post.creator.display_name}</p>
              <p className="text-[11px] text-muted-foreground">Creator</p>
            </div>
          </Link>
          <motion.span
            className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground"
            animate={{ opacity: [0.65, 1, 0.65] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          >
            <TrendingUp className="h-3 w-3" />
            {(post.trend_momentum * 100).toFixed(0)} trend
          </motion.span>
        </div>

        {post.caption && <p className="text-sm text-muted-foreground line-clamp-2">{post.caption}</p>}

        <div className="flex flex-wrap gap-1.5">
          {post.style_tags.slice(0, 8).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-secondary/80 px-2 py-0.5 text-[11px] text-secondary-foreground"
            >
              #{tag}
            </span>
          ))}
        </div>

        <div className="flex gap-2 pt-1">
          {post.shop_url && (
            <Button asChild size="sm" className="flex-1 gap-2">
              <Link href={post.shop_url}>
                <ShoppingBag className="h-4 w-4" />
                Shop
              </Link>
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => onShare?.(post)}
          >
            <Share2 className="h-4 w-4" />
            Share
          </Button>
        </div>
      </div>
    </motion.article>
  );
}
