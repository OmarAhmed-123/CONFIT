/**
 * PopularityIndicator Component
 * =============================
 * Visual indicator for outfit popularity metrics
 */

import { TrendingUp, Flame, Sparkles, Eye, Bookmark, Share2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PopularityIndicatorProps {
  trendingScore?: number;
  popularityScore?: number;
  styleRelevanceScore?: number;
  viewCount?: number;
  saveCount?: number;
  shareCount?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'full' | 'compact' | 'badge';
  className?: string;
}

const sizeClasses = {
  sm: { icon: 'w-3 h-3', text: 'text-xs', gap: 'gap-1' },
  md: { icon: 'w-4 h-4', text: 'text-sm', gap: 'gap-1.5' },
  lg: { icon: 'w-5 h-5', text: 'text-base', gap: 'gap-2' },
};

export function PopularityIndicator({
  trendingScore = 0,
  popularityScore = 0,
  styleRelevanceScore = 0,
  viewCount = 0,
  saveCount = 0,
  shareCount = 0,
  size = 'md',
  variant = 'full',
  className,
}: PopularityIndicatorProps) {
  const getTrendingLabel = (score: number): { label: string; color: string } => {
    if (score >= 80) return { label: 'Hot', color: 'text-orange-500' };
    if (score >= 60) return { label: 'Trending', color: 'text-yellow-500' };
    if (score >= 40) return { label: 'Rising', color: 'text-blue-500' };
    return { label: 'New', color: 'text-gray-500' };
  };

  const getPopularityLabel = (score: number): { label: string; color: string } => {
    if (score >= 80) return { label: 'Popular', color: 'text-green-500' };
    if (score >= 60) return { label: 'Well-liked', color: 'text-emerald-500' };
    if (score >= 40) return { label: 'Noticed', color: 'text-teal-500' };
    return { label: 'Emerging', color: 'text-gray-500' };
  };

  const getStyleLabel = (score: number): { label: string; color: string } => {
    if (score >= 80) return { label: 'Style Icon', color: 'text-purple-500' };
    if (score >= 60) return { label: 'Stylish', color: 'text-violet-500' };
    if (score >= 40) return { label: 'Curated', color: 'text-indigo-500' };
    return { label: 'Unique', color: 'text-gray-500' };
  };

  const trending = getTrendingLabel(trendingScore);
  const popularity = getPopularityLabel(popularityScore);
  const style = getStyleLabel(styleRelevanceScore);

  const formatCount = (count: number): string => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  if (variant === 'badge') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        {trendingScore >= 60 && (
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 font-medium',
              sizeClasses[size].text,
              trendingScore >= 80
                ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
            )}
          >
            <Flame className={cn(sizeClasses[size].icon, 'mr-1')} />
            {trending.label}
          </span>
        )}
        {popularityScore >= 60 && (
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 font-medium',
              sizeClasses[size].text,
              'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            )}
          >
            <TrendingUp className={cn(sizeClasses[size].icon, 'mr-1')} />
            {popularity.label}
          </span>
        )}
        {styleRelevanceScore >= 60 && (
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 font-medium',
              sizeClasses[size].text,
              'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
            )}
          >
            <Sparkles className={cn(sizeClasses[size].icon, 'mr-1')} />
            {style.label}
          </span>
        )}
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={cn('flex items-center gap-3', className)}>
        <div className={cn('flex items-center', sizeClasses[size].gap, trending.color)}>
          <Flame className={sizeClasses[size].icon} />
          <span className={cn(sizeClasses[size].text, 'font-medium')}>
            {trendingScore.toFixed(0)}
          </span>
        </div>
        <div className={cn('flex items-center', sizeClasses[size].gap, popularity.color)}>
          <TrendingUp className={sizeClasses[size].icon} />
          <span className={cn(sizeClasses[size].text, 'font-medium')}>
            {popularityScore.toFixed(0)}
          </span>
        </div>
        <div className={cn('flex items-center', sizeClasses[size].gap, style.color)}>
          <Sparkles className={sizeClasses[size].icon} />
          <span className={cn(sizeClasses[size].text, 'font-medium')}>
            {styleRelevanceScore.toFixed(0)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Scores */}
      <div className="flex items-center gap-4">
        {/* Trending Score */}
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'flex items-center justify-center rounded-lg p-1.5',
              trendingScore >= 60
                ? 'bg-orange-100 dark:bg-orange-900/30'
                : 'bg-gray-100 dark:bg-gray-800'
            )}
          >
            <Flame
              className={cn(
                sizeClasses[size].icon,
                trendingScore >= 60 ? 'text-orange-500' : 'text-gray-400'
              )}
            />
          </div>
          <div>
            <p className={cn(sizeClasses[size].text, 'font-semibold', trending.color)}>
              {trendingScore.toFixed(0)}
            </p>
            <p className={cn('text-xs text-gray-500 dark:text-gray-400')}>{trending.label}</p>
          </div>
        </div>

        {/* Popularity Score */}
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'flex items-center justify-center rounded-lg p-1.5',
              popularityScore >= 60
                ? 'bg-green-100 dark:bg-green-900/30'
                : 'bg-gray-100 dark:bg-gray-800'
            )}
          >
            <TrendingUp
              className={cn(
                sizeClasses[size].icon,
                popularityScore >= 60 ? 'text-green-500' : 'text-gray-400'
              )}
            />
          </div>
          <div>
            <p className={cn(sizeClasses[size].text, 'font-semibold', popularity.color)}>
              {popularityScore.toFixed(0)}
            </p>
            <p className={cn('text-xs text-gray-500 dark:text-gray-400')}>{popularity.label}</p>
          </div>
        </div>

        {/* Style Relevance Score */}
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'flex items-center justify-center rounded-lg p-1.5',
              styleRelevanceScore >= 60
                ? 'bg-purple-100 dark:bg-purple-900/30'
                : 'bg-gray-100 dark:bg-gray-800'
            )}
          >
            <Sparkles
              className={cn(
                sizeClasses[size].icon,
                styleRelevanceScore >= 60 ? 'text-purple-500' : 'text-gray-400'
              )}
            />
          </div>
          <div>
            <p className={cn(sizeClasses[size].text, 'font-semibold', style.color)}>
              {styleRelevanceScore.toFixed(0)}
            </p>
            <p className={cn('text-xs text-gray-500 dark:text-gray-400')}>{style.label}</p>
          </div>
        </div>
      </div>

      {/* Engagement Stats */}
      <div className="flex items-center gap-4 text-gray-500 dark:text-gray-400">
        <div className={cn('flex items-center', sizeClasses[size].gap)}>
          <Eye className={cn(sizeClasses[size].icon)} />
          <span className={sizeClasses[size].text}>{formatCount(viewCount)} views</span>
        </div>
        <div className={cn('flex items-center', sizeClasses[size].gap)}>
          <Bookmark className={cn(sizeClasses[size].icon)} />
          <span className={sizeClasses[size].text}>{formatCount(saveCount)} saves</span>
        </div>
        <div className={cn('flex items-center', sizeClasses[size].gap)}>
          <Share2 className={cn(sizeClasses[size].icon)} />
          <span className={sizeClasses[size].text}>{formatCount(shareCount)} shares</span>
        </div>
      </div>
    </div>
  );
}

export default PopularityIndicator;
