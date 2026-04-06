/**
 * TrendingOutfitsSection Component
 * ================================
 * Displays trending/popular outfits with filtering options
 */

import { useState, useEffect, useCallback } from 'react';
import { Flame, TrendingUp, Clock, ChevronRight, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getTrendingOutfits, getPopularOutfits, type TrendingOutfitItem, type TrendingFilters } from '@/lib/api/outfit-ratings';
import { RatingDisplay } from './RatingStars';
import { PopularityIndicator } from './PopularityIndicator';

interface TrendingOutfitsSectionProps {
  title?: string;
  defaultTab?: 'trending' | 'popular';
  timeWindow?: TrendingFilters['time_window'];
  pageSize?: number;
  showFilters?: boolean;
  onItemClick?: (outfitId: string) => void;
  className?: string;
}

export function TrendingOutfitsSection({
  title = 'Trending Outfits',
  defaultTab = 'trending',
  timeWindow = '7d',
  pageSize = 6,
  showFilters = true,
  onItemClick,
  className,
}: TrendingOutfitsSectionProps) {
  const [activeTab, setActiveTab] = useState<'trending' | 'popular'>(defaultTab);
  const [activeTimeWindow, setActiveTimeWindow] = useState<TrendingFilters['time_window']>(timeWindow);
  const [outfits, setOutfits] = useState<TrendingOutfitItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);

  const fetchOutfits = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const filters: TrendingFilters = {
        time_window: activeTimeWindow,
        page,
        page_size: pageSize,
      };

      const response = activeTab === 'trending'
        ? await getTrendingOutfits(filters)
        : await getPopularOutfits(filters);

      setOutfits(response.outfits);
      setTotalCount(response.total_count);
    } catch (err) {
      setError('Failed to load outfits. Please try again.');
      console.error('Error fetching outfits:', err);
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, activeTimeWindow, page, pageSize]);

  useEffect(() => {
    fetchOutfits();
  }, [fetchOutfits]);

  const timeWindowLabels: Record<string, string> = {
    '24h': 'Last 24h',
    '7d': 'Last 7 days',
    '30d': 'Last 30 days',
    'all': 'All time',
  };

  return (
    <section className={cn('flex flex-col gap-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {activeTab === 'trending' ? (
            <Flame className="w-5 h-5 text-orange-500" />
          ) : (
            <TrendingUp className="w-5 h-5 text-green-500" />
          )}
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {title}
          </h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {totalCount} outfits
          </span>
        </div>

        {showFilters && (
          <div className="flex items-center gap-2">
            {/* Tab Toggle */}
            <div className="flex rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5">
              <button
                type="button"
                onClick={() => setActiveTab('trending')}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
                  activeTab === 'trending'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
                )}
              >
                <Flame className="w-4 h-4 inline mr-1" />
                Trending
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('popular')}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
                  activeTab === 'popular'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
                )}
              >
                <TrendingUp className="w-4 h-4 inline mr-1" />
                Popular
              </button>
            </div>

            {/* Time Window Filter */}
            <div className="flex rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5">
              {(['24h', '7d', '30d', 'all'] as const).map((tw) => (
                <button
                  key={tw}
                  type="button"
                  onClick={() => setActiveTimeWindow(tw)}
                  className={cn(
                    'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
                    activeTimeWindow === tw
                      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
                  )}
                >
                  {timeWindowLabels[tw]}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <p className="text-red-500 dark:text-red-400">{error}</p>
          <button
            type="button"
            onClick={fetchOutfits}
            className="mt-4 px-4 py-2 text-sm font-medium text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      ) : outfits.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Clock className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            No outfits found for this time period
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {outfits.map((outfit, index) => (
            <TrendingOutfitCard
              key={outfit.outfit_id}
              outfit={outfit}
              rank={index + 1 + (page - 1) * pageSize}
              onClick={() => onItemClick?.(outfit.outfit_id)}
            />
          ))}
        </div>
      )}

      {/* Load More */}
      {totalCount > pageSize * page && (
        <button
          type="button"
          onClick={() => setPage((p) => p + 1)}
          className="flex items-center justify-center gap-2 py-3 text-sm font-medium text-primary hover:underline"
        >
          Load more
          <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </section>
  );
}

// Sub-component for individual outfit card
interface TrendingOutfitCardProps {
  outfit: TrendingOutfitItem;
  rank: number;
  onClick?: () => void;
}

function TrendingOutfitCard({ outfit, rank, onClick }: TrendingOutfitCardProps) {
  const getRankBadge = (rank: number) => {
    if (rank <= 3) {
      return (
        <span
          className={cn(
            'absolute top-2 left-2 flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold',
            rank === 1 && 'bg-yellow-400 text-yellow-900',
            rank === 2 && 'bg-gray-300 text-gray-700',
            rank === 3 && 'bg-amber-600 text-white'
          )}
        >
          {rank}
        </span>
      );
    }
    return (
      <span className="absolute top-2 left-2 flex h-6 w-6 items-center justify-center rounded-full bg-gray-800/60 text-xs font-bold text-white">
        {rank}
      </span>
    );
  };

  return (
    <article
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700',
        'bg-white dark:bg-gray-800 transition-all duration-200',
        'hover:shadow-lg hover:border-primary/30 cursor-pointer'
      )}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      tabIndex={0}
      role="button"
      aria-label={`View outfit: ${outfit.title}`}
    >
      {/* Rank Badge */}
      {getRankBadge(rank)}

      {/* Outfit Preview (placeholder for now) */}
      <div className="relative aspect-[4/3] bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex gap-2">
            {outfit.items.slice(0, 3).map((item, i) => (
              <div
                key={i}
                className="w-16 h-20 rounded-lg bg-white dark:bg-gray-600 shadow-sm flex items-center justify-center text-xs text-gray-400"
              >
                {item.category?.slice(0, 3).toUpperCase() || 'ITEM'}
              </div>
            ))}
            {outfit.items.length > 3 && (
              <div className="w-16 h-20 rounded-lg bg-gray-300 dark:bg-gray-600 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
                +{outfit.items.length - 3}
              </div>
            )}
          </div>
        </div>

        {/* Trending Score Badge */}
        {outfit.trending_score >= 60 && (
          <div className="absolute top-2 right-2">
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                outfit.trending_score >= 80
                  ? 'bg-orange-500 text-white'
                  : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
              )}
            >
              <Flame className="w-3 h-3 mr-1" />
              {outfit.trending_score.toFixed(0)}
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col gap-2 p-4">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate group-hover:text-primary">
          {outfit.title}
        </h3>

        <div className="flex items-center justify-between">
          <RatingDisplay rating={outfit.avg_rating} count={outfit.total_ratings} size="sm" />
          {outfit.total_price && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              ${outfit.total_price.toFixed(2)}
            </span>
          )}
        </div>

        <PopularityIndicator
          trendingScore={outfit.trending_score}
          popularityScore={outfit.popularity_score}
          variant="compact"
          size="sm"
        />
      </div>
    </article>
  );
}

export default TrendingOutfitsSection;
