import { motion, AnimatePresence } from 'framer-motion';
import { 
  Cloud, Droplet, FlaskConical, Trash2, 
  ChevronDown, ChevronUp, AlertCircle, CheckCircle2,
  MinusCircle
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { createStaggerTransition, transitionFast, transitionHero } from '@/motion';

interface ImpactMetric {
  value: number | string;
  unit: string;
  rating: 'excellent' | 'good' | 'moderate' | 'poor' | 'very_poor';
  description?: string;
}

interface ImpactBreakdownData {
  carbon?: ImpactMetric;
  water?: ImpactMetric;
  chemicals?: ImpactMetric;
  waste?: ImpactMetric;
}

interface ImpactBreakdownProps {
  breakdown: ImpactBreakdownData;
  expanded?: boolean;
  className?: string;
}

const RATING_CONFIG = {
  excellent: {
    label: 'Excellent',
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/30',
    icon: CheckCircle2,
  },
  good: {
    label: 'Good',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-400/10',
    borderColor: 'border-emerald-400/30',
    icon: CheckCircle2,
  },
  moderate: {
    label: 'Moderate',
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
    icon: MinusCircle,
  },
  poor: {
    label: 'Poor',
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    icon: AlertCircle,
  },
  very_poor: {
    label: 'Very Poor',
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    icon: AlertCircle,
  },
};

const METRIC_CONFIG = {
  carbon: {
    label: 'Carbon Footprint',
    icon: Cloud,
    defaultUnit: 'kg CO2',
    description: 'Estimated CO2 emissions from production and shipping',
  },
  water: {
    label: 'Water Usage',
    icon: Droplet,
    defaultUnit: 'L',
    description: 'Water consumed during material production and manufacturing',
  },
  chemicals: {
    label: 'Chemical Impact',
    icon: FlaskConical,
    defaultUnit: '',
    description: 'Environmental impact of dyes and chemical processes',
  },
  waste: {
    label: 'Waste Generation',
    icon: Trash2,
    defaultUnit: '',
    description: 'Waste produced during manufacturing and packaging',
  },
};

export function ImpactBreakdown({ 
  breakdown, 
  expanded = false,
  className = '' 
}: ImpactBreakdownProps) {
  const [isExpanded, setIsExpanded] = useState(expanded);

  const metrics = Object.entries(breakdown).map(([key, data]) => ({
    key,
    ...data,
    config: METRIC_CONFIG[key as keyof typeof METRIC_CONFIG],
    ratingConfig: RATING_CONFIG[data.rating as keyof typeof RATING_CONFIG],
  }));

  if (metrics.length === 0) return null;

  // Summary view
  const summaryMetrics = metrics.slice(0, 2);
  const detailMetrics = metrics.slice(2);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Summary Metrics */}
      <div className="grid grid-cols-2 gap-2">
        {summaryMetrics.map((metric, index) => {
          const Icon = metric.config.icon;
          const RatingIcon = metric.ratingConfig.icon;

          return (
            <motion.div
              key={metric.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={createStaggerTransition(index, 0.1, 0.6)}
              className={cn(
                'p-3 rounded-lg border',
                metric.ratingConfig.bgColor,
                metric.ratingConfig.borderColor
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={cn('h-4 w-4', metric.ratingConfig.color)} />
                <span className="text-xs font-medium text-muted-foreground">
                  {metric.config.label}
                </span>
              </div>
              
              <div className="flex items-baseline gap-1">
                <span className={cn('text-lg font-bold', metric.ratingConfig.color)}>
                  {typeof metric.value === 'number' ? metric.value.toFixed(1) : metric.value}
                </span>
                {metric.unit && (
                  <span className="text-xs text-muted-foreground">
                    {metric.unit}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1 mt-1.5">
                <RatingIcon className={cn('h-3 w-3', metric.ratingConfig.color)} />
                <span className={cn('text-xs font-medium', metric.ratingConfig.color)}>
                  {metric.ratingConfig.label}
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Expandable Details */}
      {(detailMetrics.length > 0 || metrics.some(m => m.description)) && (
        <motion.div
          initial={false}
          animate={{ height: 'auto' }}
        >
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-full justify-center py-1"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" />
                <span>Less details</span>
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" />
                <span>More details</span>
              </>
            )}
          </button>

          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={transitionFast}
                className="overflow-hidden"
              >
                <div className="grid grid-cols-2 gap-2 pt-2">
                  {detailMetrics.map((metric, index) => {
                    const Icon = metric.config.icon;
                    const RatingIcon = metric.ratingConfig.icon;

                    return (
                      <motion.div
                        key={metric.key}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={createStaggerTransition(index)}
                        className={cn(
                          'p-3 rounded-lg border',
                          metric.ratingConfig.bgColor,
                          metric.ratingConfig.borderColor
                        )}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Icon className={cn('h-4 w-4', metric.ratingConfig.color)} />
                          <span className="text-xs font-medium text-muted-foreground">
                            {metric.config.label}
                          </span>
                        </div>
                        
                        <div className="flex items-baseline gap-1">
                          <span className={cn('text-lg font-bold', metric.ratingConfig.color)}>
                            {typeof metric.value === 'number' ? metric.value.toFixed(1) : metric.value}
                          </span>
                          {metric.unit && (
                            <span className="text-xs text-muted-foreground">
                              {metric.unit}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-1 mt-1.5">
                          <RatingIcon className={cn('h-3 w-3', metric.ratingConfig.color)} />
                          <span className={cn('text-xs font-medium', metric.ratingConfig.color)}>
                            {metric.ratingConfig.label}
                          </span>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>

                {/* Descriptions */}
                <div className="mt-3 space-y-2">
                  {metrics.map((metric) => (
                    metric.description && (
                      <motion.p
                        key={`${metric.key}-desc`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-xs text-muted-foreground"
                      >
                        <span className="font-medium">{metric.config.label}:</span>{' '}
                        {metric.description}
                      </motion.p>
                    )
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  );
}

// Compact inline version for product cards
interface ImpactSummaryProps {
  breakdown: ImpactBreakdownData;
  className?: string;
}

export function ImpactSummary({ breakdown, className = '' }: ImpactSummaryProps) {
  const metrics = Object.entries(breakdown).slice(0, 3);
  
  if (metrics.length === 0) return null;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {metrics.map(([key, data]) => {
        const config = METRIC_CONFIG[key as keyof typeof METRIC_CONFIG];
        const ratingConfig = RATING_CONFIG[data.rating as keyof typeof RATING_CONFIG];
        const Icon = config.icon;

        return (
          <motion.div
            key={key}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn(
              'flex items-center gap-1 px-2 py-0.5 rounded-full',
              ratingConfig.bgColor
            )}
          >
            <Icon className={cn('h-3 w-3', ratingConfig.color)} />
            <span className={cn('text-xs font-medium', ratingConfig.color)}>
              {typeof data.value === 'number' ? data.value.toFixed(0) : data.value}
              {data.unit && <span className="ml-0.5">{data.unit}</span>}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}

// Visual comparison chart
interface ImpactComparisonProps {
  productBreakdown: ImpactBreakdownData;
  categoryAverage?: ImpactBreakdownData;
  className?: string;
}

export function ImpactComparison({ 
  productBreakdown, 
  categoryAverage,
  className = '' 
}: ImpactComparisonProps) {
  if (!categoryAverage) return null;

  const metrics = Object.entries(productBreakdown).map(([key, data]) => {
    const avg = categoryAverage[key as keyof typeof categoryAverage];
    const config = METRIC_CONFIG[key as keyof typeof METRIC_CONFIG];
    
    let comparisonPercent = 0;
    if (avg && typeof data.value === 'number' && typeof avg.value === 'number' && avg.value > 0) {
      comparisonPercent = (data.value / avg.value) * 100;
    }

    return {
      key,
      label: config.label,
      value: data.value,
      unit: data.unit,
      rating: data.rating,
      average: avg?.value,
      comparisonPercent,
      ratingConfig: RATING_CONFIG[data.rating as keyof typeof RATING_CONFIG],
    };
  });

  return (
    <div className={`space-y-3 ${className}`}>
      <h4 className="text-sm font-semibold text-foreground">Impact vs. Category Average</h4>
      
      {metrics.map((metric, index) => (
        <motion.div
          key={metric.key}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={createStaggerTransition(index, 0.1, 0.6)}
          className="space-y-1"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{metric.label}</span>
            <span className={cn('text-xs font-medium', metric.ratingConfig.color)}>
              {typeof metric.value === 'number' ? metric.value.toFixed(1) : metric.value} {metric.unit}
            </span>
          </div>
          
          <div className="relative h-2 bg-muted rounded-full overflow-hidden">
            {/* Category average marker */}
            <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/30" />
            
            {/* Product value bar */}
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(metric.comparisonPercent, 150)}%` }}
              transition={createStaggerTransition(index, 0.1, 0.6, transitionHero)}
              className={cn(
                'h-full rounded-full',
                metric.comparisonPercent <= 100 
                  ? 'bg-emerald-500' 
                  : metric.comparisonPercent <= 150 
                    ? 'bg-amber-500' 
                    : 'bg-red-500'
              )}
            />
          </div>
          
          {metric.average !== undefined && (
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Avg: {typeof metric.average === 'number' ? metric.average.toFixed(1) : metric.average} {metric.unit}</span>
              <span className={cn(
                metric.comparisonPercent <= 100 ? 'text-emerald-500' : 'text-red-500'
              )}>
                {metric.comparisonPercent <= 100 ? '↓' : '↑'} 
                {Math.abs(metric.comparisonPercent - 100).toFixed(0)}%
              </span>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

export default ImpactBreakdown;
