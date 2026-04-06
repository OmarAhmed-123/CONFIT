import { motion } from 'framer-motion';
import { Leaf, TrendingUp, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

export type SustainabilityTier = 
  | 'excellent'
  | 'very_good'
  | 'good'
  | 'fair'
  | 'moderate'
  | 'low'
  | 'poor';

interface SustainabilityRatingProps {
  score: number;
  tier: SustainabilityTier;
  showBreakdown?: boolean;
  materialScore?: number;
  brandScore?: number;
  manufacturingScore?: number;
  shippingScore?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const TIER_CONFIG: Record<SustainabilityTier, {
  label: string;
  textClass: string;
  iconClass: string;
  softBgClass: string;
  softBgAltClass: string;
  gradient: string;
  minScore: number;
  maxScore: number;
  description: string;
}> = {
  excellent: {
    label: 'Excellent',
    textClass: 'text-emerald-700 dark:text-emerald-400',
    iconClass: 'text-emerald-600 dark:text-emerald-400',
    softBgClass: 'bg-emerald-500/20',
    softBgAltClass: 'bg-emerald-500/15',
    gradient: 'from-emerald-500 to-emerald-600',
    minScore: 90,
    maxScore: 100,
    description: 'Industry-leading sustainability practices',
  },
  very_good: {
    label: 'Very Good',
    textClass: 'text-emerald-700 dark:text-emerald-400',
    iconClass: 'text-emerald-600 dark:text-emerald-400',
    softBgClass: 'bg-emerald-500/20',
    softBgAltClass: 'bg-emerald-500/15',
    gradient: 'from-emerald-400 to-emerald-500',
    minScore: 80,
    maxScore: 89,
    description: 'Strong commitment to sustainability',
  },
  good: {
    label: 'Good',
    textClass: 'text-emerald-700 dark:text-emerald-400',
    iconClass: 'text-emerald-600 dark:text-emerald-400',
    softBgClass: 'bg-emerald-500/20',
    softBgAltClass: 'bg-emerald-500/15',
    gradient: 'from-emerald-300 to-emerald-400',
    minScore: 70,
    maxScore: 79,
    description: 'Above average sustainability practices',
  },
  fair: {
    label: 'Fair',
    textClass: 'text-amber-700 dark:text-amber-400',
    iconClass: 'text-amber-600 dark:text-amber-400',
    softBgClass: 'bg-amber-500/20',
    softBgAltClass: 'bg-amber-500/15',
    gradient: 'from-amber-400 to-amber-500',
    minScore: 60,
    maxScore: 69,
    description: 'Moderate sustainability efforts',
  },
  moderate: {
    label: 'Moderate',
    textClass: 'text-orange-700 dark:text-orange-400',
    iconClass: 'text-orange-600 dark:text-orange-400',
    softBgClass: 'bg-orange-500/20',
    softBgAltClass: 'bg-orange-500/15',
    gradient: 'from-amber-500 to-orange-500',
    minScore: 50,
    maxScore: 59,
    description: 'Room for improvement',
  },
  low: {
    label: 'Low',
    textClass: 'text-orange-700 dark:text-orange-400',
    iconClass: 'text-orange-600 dark:text-orange-400',
    softBgClass: 'bg-orange-500/20',
    softBgAltClass: 'bg-orange-500/15',
    gradient: 'from-orange-500 to-red-500',
    minScore: 40,
    maxScore: 49,
    description: 'Below average sustainability',
  },
  poor: {
    label: 'Poor',
    textClass: 'text-red-700 dark:text-red-400',
    iconClass: 'text-red-600 dark:text-red-400',
    softBgClass: 'bg-red-500/20',
    softBgAltClass: 'bg-red-500/15',
    gradient: 'from-red-500 to-red-600',
    minScore: 0,
    maxScore: 39,
    description: 'Significant improvements needed',
  },
};

const SIZE_CONFIG = {
  sm: {
    container: 'gap-2',
    scoreText: 'text-lg font-bold',
    labelText: 'text-xs',
    iconSize: 'h-4 w-4',
    progressHeight: 'h-1.5',
  },
  md: {
    container: 'gap-3',
    scoreText: 'text-2xl font-bold',
    labelText: 'text-sm',
    iconSize: 'h-5 w-5',
    progressHeight: 'h-2',
  },
  lg: {
    container: 'gap-4',
    scoreText: 'text-3xl font-bold',
    labelText: 'text-base',
    iconSize: 'h-6 w-6',
    progressHeight: 'h-3',
  },
};

export function SustainabilityRating({
  score,
  tier,
  showBreakdown = false,
  materialScore,
  brandScore,
  manufacturingScore,
  shippingScore,
  size = 'md',
  className = '',
}: SustainabilityRatingProps) {
  const tierConfig = TIER_CONFIG[tier];
  const sizeConfig = SIZE_CONFIG[size];

  const componentScores = [
    { label: 'Materials', score: materialScore, weight: 35 },
    { label: 'Brand', score: brandScore, weight: 25 },
    { label: 'Manufacturing', score: manufacturingScore, weight: 25 },
    { label: 'Shipping', score: shippingScore, weight: 15 },
  ].filter(item => item.score !== undefined);

  return (
    <div className={`${sizeConfig.container} ${className}`}>
      {/* Main Score Display */}
      <div className="flex items-center gap-3">
        {/* Score Circle */}
        <motion.div
          initial={{ scale: 0.8, rotate: -10 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={createTransition({ type: 'spring', stiffness: 300, damping: 20 })}
          className="relative flex items-center justify-center"
        >
          <div
            className={cn('absolute inset-0 rounded-full', tierConfig.softBgClass)}
            aria-hidden="true"
          />
          <div
            className={cn('relative flex items-center justify-center w-12 h-12 rounded-full', tierConfig.softBgAltClass)}
            aria-hidden="true"
          >
            <Leaf
              className={cn(sizeConfig.iconSize, tierConfig.iconClass)}
              strokeWidth={2.5}
            />
          </div>
        </motion.div>

        {/* Score & Tier */}
        <div className="flex flex-col">
          <div className="flex items-baseline gap-1.5">
            <motion.span
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(sizeConfig.scoreText, tierConfig.textClass)}
            >
              {score.toFixed(1)}
            </motion.span>
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={createTransition({ delay: 0.2 })}
              className="text-muted-foreground text-sm"
            >
              / 100
            </motion.span>
          </div>
          
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={createTransition({ delay: 0.1 })}
            className="flex items-center gap-1.5"
          >
            <span
              className={cn(sizeConfig.labelText, 'font-semibold', tierConfig.textClass)}
            >
              {tierConfig.label}
            </span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="text-sm">{tierConfig.description}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Score range: {tierConfig.minScore} - {tierConfig.maxScore}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </motion.div>
        </div>
      </div>

      {/* Progress Bar */}
      <motion.div
        initial={{ opacity: 0, scaleX: 0 }}
        animate={{ opacity: 1, scaleX: 1 }}
        transition={createTransition({ delay: 0.2 })}
        className="w-full"
      >
        <div className={cn("relative w-full overflow-hidden rounded-full bg-muted", sizeConfig.progressHeight)}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${score}%` }}
            transition={createTransition({ duration: 0.8, delay: 0.3, ease: "easeOut" })}
            className={cn("h-full rounded-full bg-gradient-to-r", tierConfig.gradient)}
          />
        </div>
      </motion.div>

      {/* Component Breakdown */}
      {showBreakdown && componentScores.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ delay: 0.3 })}
          className="grid grid-cols-2 gap-2 mt-2"
        >
          {componentScores.map((item, index) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={createTransition({ delay: 0.3 + index * 0.1 })}
              className="flex flex-col gap-1 p-2 rounded-lg bg-muted/50"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{item.label}</span>
                <span className="text-xs font-medium text-muted-foreground">
                  {item.weight}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-1 flex-1 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${item.score}%` }}
                    transition={createTransition({ duration: 0.5, delay: 0.3 + index * 0.1 })}
                    className="h-full bg-primary rounded-full"
                  />
                </div>
                <span className="text-sm font-semibold">
                  {item.score?.toFixed(0)}
                </span>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}

// Compact version for product cards
interface SustainabilityBadgeProps {
  score: number;
  tier: SustainabilityTier;
  className?: string;
}

export function SustainabilityBadge({ 
  score, 
  tier, 
  className = '' 
}: SustainabilityBadgeProps) {
  const tierConfig = TIER_CONFIG[tier];

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            whileHover={{ scale: 1.05 }}
            className={cn('inline-flex items-center gap-1.5 px-2 py-1 rounded-full', tierConfig.softBgClass, className)}
          >
            <Leaf
              className={cn('h-3.5 w-3.5', tierConfig.iconClass)}
              strokeWidth={2.5}
            />
            <span
              className={cn('text-xs font-semibold', tierConfig.textClass)}
            >
              {score.toFixed(0)}
            </span>
          </motion.div>
        </TooltipTrigger>
        <TooltipContent side="top" className="bg-charcoal/95 text-white">
          <div className="flex items-center gap-2">
            <Leaf className={cn('h-4 w-4', tierConfig.iconClass)} />
            <span className="font-semibold">{tierConfig.label}</span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Sustainability Score: {score.toFixed(1)}/100
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Comparison indicator
interface SustainabilityComparisonProps {
  score: number;
  categoryAverage?: number;
  className?: string;
}

export function SustainabilityComparison({
  score,
  categoryAverage,
  className = '',
}: SustainabilityComparisonProps) {
  if (!categoryAverage) return null;

  const difference = score - categoryAverage;
  const isAbove = difference > 0;
  const percentageDiff = ((difference / categoryAverage) * 100).toFixed(0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-center gap-1.5 text-xs ${className}`}
    >
      <TrendingUp
        className={`h-3.5 w-3.5 ${isAbove ? 'text-emerald-500' : 'text-red-500 rotate-180'}`}
      />
      <span className={isAbove ? 'text-emerald-600' : 'text-red-600'}>
        {isAbove ? '+' : ''}{percentageDiff}%
      </span>
      <span className="text-muted-foreground">vs. category avg</span>
    </motion.div>
  );
}

export default SustainabilityRating;
