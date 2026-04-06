/**
 * RatingStars Component
 * =====================
 * Interactive star rating component with smooth animations
 */

import { useState, useCallback } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RatingStarsProps {
  value?: number;
  onChange?: (rating: number) => void;
  readonly?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showValue?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
};

const gapClasses = {
  sm: 'gap-0.5',
  md: 'gap-1',
  lg: 'gap-1.5',
};

export function RatingStars({
  value = 0,
  onChange,
  readonly = false,
  size = 'md',
  showValue = false,
  className,
}: RatingStarsProps) {
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  const [isAnimating, setIsAnimating] = useState(false);

  const displayValue = hoverValue ?? value;

  const handleClick = useCallback(
    (rating: number) => {
      if (readonly || !onChange) return;

      setIsAnimating(true);
      onChange(rating);

      // Reset animation state after animation completes
      setTimeout(() => setIsAnimating(false), 300);
    },
    [readonly, onChange]
  );

  const handleMouseEnter = useCallback((rating: number) => {
    if (readonly) return;
    setHoverValue(rating);
  }, [readonly]);

  const handleMouseLeave = useCallback(() => {
    if (readonly) return;
    setHoverValue(null);
  }, [readonly]);

  return (
    <div className={cn('flex items-center', gapClasses[size], className)}>
      {[1, 2, 3, 4, 5].map((star) => {
        const isFilled = star <= displayValue;
        const isPartial = star === Math.ceil(displayValue) && displayValue % 1 !== 0;

        return (
          <button
            key={star}
            type="button"
            disabled={readonly}
            className={cn(
              'relative transition-transform duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-sm',
              !readonly && 'cursor-pointer hover:scale-110 active:scale-95',
              readonly && 'cursor-default',
              isAnimating && star === value && 'animate-bounce'
            )}
            onMouseEnter={() => handleMouseEnter(star)}
            onMouseLeave={handleMouseLeave}
            onClick={() => handleClick(star)}
            aria-label={`${star} star${star > 1 ? 's' : ''}`}
          >
            <Star
              className={cn(
                sizeClasses[size],
                'transition-all duration-200',
                isFilled
                  ? 'fill-yellow-400 text-yellow-400 drop-shadow-[0_0_4px_rgba(250,204,21,0.4)]'
                  : 'fill-transparent text-gray-300 dark:text-gray-600',
                !readonly && hoverValue !== null && star <= hoverValue && 'animate-pulse'
              )}
            />
            {isPartial && (
              <div
                className="absolute inset-0 overflow-hidden"
                data-fill-percent={Math.round((displayValue % 1) * 100)}
              >
                <Star
                  className={cn(
                    sizeClasses[size],
                    'fill-yellow-400 text-yellow-400'
                  )}
                />
              </div>
            )}
          </button>
        );
      })}
      {showValue && (
        <span className={cn(
          'ml-2 font-medium text-gray-700 dark:text-gray-300',
          size === 'sm' && 'text-sm',
          size === 'lg' && 'text-lg'
        )}>
          {value.toFixed(1)}
        </span>
      )}
    </div>
  );
}

/**
 * RatingDisplay Component
 * =======================
 * Read-only rating display with count
 */
interface RatingDisplayProps {
  rating: number;
  count?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function RatingDisplay({ rating, count, size = 'md', className }: RatingDisplayProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-center">
        <Star className={cn(sizeClasses[size], 'fill-yellow-400 text-yellow-400')} />
        <span className={cn(
          'ml-1 font-semibold',
          size === 'sm' && 'text-sm',
          size === 'lg' && 'text-lg'
        )}>
          {rating.toFixed(1)}
        </span>
      </div>
      {count !== undefined && (
        <span className="text-gray-500 dark:text-gray-400 text-sm">
          ({count} review{count !== 1 ? 's' : ''})
        </span>
      )}
    </div>
  );
}

export default RatingStars;
