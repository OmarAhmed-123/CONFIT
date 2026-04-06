/**
 * LikeButton Component
 * ====================
 * Animated like/dislike button with smooth transitions
 */

import { useState, useCallback } from 'react';
import { ThumbsUp, ThumbsDown, Heart } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LikeButtonProps {
  outfitId: string;
  initialLiked?: boolean | null;
  likeCount?: number;
  dislikeCount?: number;
  onLikeToggle?: (isLike: boolean) => Promise<void>;
  variant?: 'thumbs' | 'heart';
  size?: 'sm' | 'md' | 'lg';
  showCount?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: { button: 'w-8 h-8', icon: 'w-4 h-4', text: 'text-xs' },
  md: { button: 'w-10 h-10', icon: 'w-5 h-5', text: 'text-sm' },
  lg: { button: 'w-12 h-12', icon: 'w-6 h-6', text: 'text-base' },
};

export function LikeButton({
  outfitId,
  initialLiked = null,
  likeCount = 0,
  dislikeCount = 0,
  onLikeToggle,
  variant = 'thumbs',
  size = 'md',
  showCount = true,
  className,
}: LikeButtonProps) {
  const [isLiked, setIsLiked] = useState<boolean | null>(initialLiked);
  const [counts, setCounts] = useState({ like: likeCount, dislike: dislikeCount });
  const [isLoading, setIsLoading] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  const handleLike = useCallback(async () => {
    if (isLoading) return;

    setIsLoading(true);
    setIsAnimating(true);

    try {
      if (onLikeToggle) {
        await onLikeToggle(true);
      }

      setIsLiked((prev) => {
        if (prev === true) {
          // Toggle off
          setCounts((c) => ({ ...c, like: Math.max(0, c.like - 1) }));
          return null;
        } else {
          // Toggle on or switch
          setCounts((c) => ({
            like: c.like + 1,
            dislike: prev === false ? Math.max(0, c.dislike - 1) : c.dislike,
          }));
          return true;
        }
      });
    } finally {
      setIsLoading(false);
      setTimeout(() => setIsAnimating(false), 300);
    }
  }, [isLoading, onLikeToggle]);

  const handleDislike = useCallback(async () => {
    if (isLoading || variant === 'heart') return;

    setIsLoading(true);
    setIsAnimating(true);

    try {
      if (onLikeToggle) {
        await onLikeToggle(false);
      }

      setIsLiked((prev) => {
        if (prev === false) {
          // Toggle off
          setCounts((c) => ({ ...c, dislike: Math.max(0, c.dislike - 1) }));
          return null;
        } else {
          // Toggle on or switch
          setCounts((c) => ({
            dislike: c.dislike + 1,
            like: prev === true ? Math.max(0, c.like - 1) : c.like,
          }));
          return false;
        }
      });
    } finally {
      setIsLoading(false);
      setTimeout(() => setIsAnimating(false), 300);
    }
  }, [isLoading, onLikeToggle, variant]);

  if (variant === 'heart') {
    return (
      <button
        type="button"
        disabled={isLoading}
        onClick={handleLike}
        className={cn(
          'flex items-center gap-1.5 rounded-full transition-all duration-200',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          sizeClasses[size].button,
          isLiked === true
            ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
          isAnimating && isLiked === true && 'animate-pulse scale-110',
          className
        )}
        aria-label={isLiked === true ? 'Unlike' : 'Like'}
        aria-pressed={isLiked === true}
      >
        <Heart
          className={cn(
            sizeClasses[size].icon,
            'transition-all duration-200',
            isLiked === true && 'fill-current'
          )}
        />
        {showCount && (
          <span className={cn(sizeClasses[size].text, 'font-medium')}>
            {counts.like}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Like Button */}
      <button
        type="button"
        disabled={isLoading}
        onClick={handleLike}
        className={cn(
          'flex items-center gap-1.5 rounded-lg px-3 py-2 transition-all duration-200',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          isLiked === true
            ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-green-50 dark:hover:bg-green-900/20',
          isAnimating && isLiked === true && 'scale-110'
        )}
        aria-label="Like"
        aria-pressed={isLiked === true}
      >
        <ThumbsUp
          className={cn(
            sizeClasses[size].icon,
            'transition-transform duration-200',
            isLiked === true && 'scale-110'
          )}
        />
        {showCount && (
          <span className={cn(sizeClasses[size].text, 'font-medium')}>
            {counts.like}
          </span>
        )}
      </button>

      {/* Dislike Button */}
      <button
        type="button"
        disabled={isLoading}
        onClick={handleDislike}
        className={cn(
          'flex items-center gap-1.5 rounded-lg px-3 py-2 transition-all duration-200',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          isLiked === false
            ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-red-50 dark:hover:bg-red-900/20',
          isAnimating && isLiked === false && 'scale-110'
        )}
        aria-label="Dislike"
        aria-pressed={isLiked === false}
      >
        <ThumbsDown
          className={cn(
            sizeClasses[size].icon,
            'transition-transform duration-200',
            isLiked === false && 'scale-110'
          )}
        />
        {showCount && (
          <span className={cn(sizeClasses[size].text, 'font-medium')}>
            {counts.dislike}
          </span>
        )}
      </button>
    </div>
  );
}

export default LikeButton;
