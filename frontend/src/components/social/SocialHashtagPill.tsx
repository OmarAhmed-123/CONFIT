/**
 * Social Hashtag Pill Component
 * Clickable hashtag with trending indicator
 */

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SocialHashtagPillProps {
  tag: string;
  postCount?: number;
  trendingScore?: number;
  isTrending?: boolean;
  onClick?: (tag: string) => void;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline' | 'filled';
  className?: string;
}

export function SocialHashtagPill({
  tag,
  postCount,
  trendingScore,
  isTrending = false,
  onClick,
  size = 'md',
  variant = 'default',
  className,
}: SocialHashtagPillProps) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };
  
  const variantClasses = {
    default: 'bg-primary/10 text-primary hover:bg-primary/20',
    outline: 'border border-primary/30 text-primary hover:bg-primary/10',
    filled: 'bg-primary text-primary-foreground hover:bg-primary/90',
  };
  
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick?.(tag)}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium transition-colors',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
    >
      <Hash className="h-3 w-3" />
      <span>{tag}</span>
      
      {isTrending && (
        <TrendingUp className="h-3 w-3 text-orange-500" />
      )}
      
      {postCount !== undefined && size !== 'sm' && (
        <span className="text-muted-foreground text-xs">
          {formatCount(postCount)}
        </span>
      )}
    </motion.button>
  );
}

// Hashtag group for displaying multiple hashtags
interface SocialHashtagGroupProps {
  hashtags: Array<{
    tag: string;
    post_count?: number;
    trending_score?: number;
    is_trending?: boolean;
  }>;
  onHashtagClick?: (tag: string) => void;
  maxVisible?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline' | 'filled';
  className?: string;
}

export function SocialHashtagGroup({
  hashtags,
  onHashtagClick,
  maxVisible = 5,
  size = 'md',
  variant = 'default',
  className,
}: SocialHashtagGroupProps) {
  const visible = hashtags.slice(0, maxVisible);
  const remaining = hashtags.length - maxVisible;
  
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {visible.map((hashtag) => (
        <SocialHashtagPill
          key={hashtag.tag}
          tag={hashtag.tag}
          postCount={hashtag.post_count}
          trendingScore={hashtag.trending_score}
          isTrending={hashtag.is_trending}
          onClick={onHashtagClick}
          size={size}
          variant={variant}
        />
      ))}
      
      {remaining > 0 && (
        <span className="text-sm text-muted-foreground self-center">
          +{remaining} more
        </span>
      )}
    </div>
  );
}

// Trending hashtags list
interface TrendingHashtagsListProps {
  hashtags: Array<{
    tag: string;
    post_count: number;
    trending_score: number;
  }>;
  onHashtagClick?: (tag: string) => void;
  className?: string;
}

export function TrendingHashtagsList({
  hashtags,
  onHashtagClick,
  className,
}: TrendingHashtagsListProps) {
  return (
    <div className={cn('space-y-2', className)}>
      <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
        Trending Now
      </h3>
      
      <div className="space-y-1">
        {hashtags.map((hashtag, index) => (
          <motion.button
            key={hashtag.tag}
            whileHover={{ x: 4 }}
            onClick={() => onHashtagClick?.(hashtag.tag)}
            className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors text-left"
          >
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground font-medium w-6">
                {index + 1}
              </span>
              <div>
                <p className="font-semibold">#{hashtag.tag}</p>
                <p className="text-xs text-muted-foreground">
                  {formatCount(hashtag.post_count)} posts
                </p>
              </div>
            </div>
            
            <TrendingUp className="h-4 w-4 text-orange-500" />
          </motion.button>
        ))}
      </div>
    </div>
  );
}

// Helper function
function formatCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`;
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
}
