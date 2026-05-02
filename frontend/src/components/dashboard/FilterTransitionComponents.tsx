/**
 * CONFIT — Filter Transition Components
 * =======================================
 * Animated components for smooth filter state transitions.
 * Uses framer-motion with CONFIT luxury aesthetic.
 */

import { memo, useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence, useInView, useAnimation, type MotionStyle } from 'framer-motion';
import { cn } from '@/lib/utils';
import { DURATION_LUXURY, DURATION_STANDARD, EASE_LUXURY, EASE_EXIT } from '@/motion';
import '@/components/predictive/predictive.css';

// ─── Color Palette (CONFIT Luxury) ────────────────────────────────────

const COLORS = {
  gold: '#D4AF37',
  goldLight: 'rgba(212, 175, 55, 0.15)',
  purple: '#8B5CF6',
  purpleLight: 'rgba(139, 92, 246, 0.15)',
  green: '#22C55E',
  amber: '#FBBF24',
  red: '#F87171',
};

// ─── Animation Variants ───────────────────────────────────────────────

export const filterTransitionVariants = {
  initial: {
    opacity: 0,
    scale: 0.98,
    y: 8,
  },
  enter: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: DURATION_LUXURY,
      ease: EASE_LUXURY,
    },
  },
  exit: {
    opacity: 0,
    scale: 0.98,
    y: -8,
    transition: {
      duration: DURATION_STANDARD,
      ease: EASE_EXIT,
    },
  },
};

export const valueChangeVariants = {
  initial: {
    opacity: 0,
    y: 10,
    filter: 'blur(4px)',
  },
  enter: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: DURATION_STANDARD,
      ease: EASE_LUXURY,
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    filter: 'blur(4px)',
    transition: {
      duration: DURATION_STANDARD / 2,
      ease: EASE_EXIT,
    },
  },
};

export const staggerContainerVariants = {
  initial: {},
  enter: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

export const staggerItemVariants = {
  initial: {
    opacity: 0,
    y: 16,
  },
  enter: {
    opacity: 1,
    y: 0,
    transition: {
      duration: DURATION_LUXURY,
      ease: EASE_LUXURY,
    },
  },
};

// ─── Animated Metric Value ────────────────────────────────────────────

interface AnimatedMetricValueProps {
  value: number | string;
  previousValue?: number | string;
  formatFn?: (value: number) => string;
  className?: string;
  highlightColor?: string;
  animateOnChange?: boolean;
}

export const AnimatedMetricValue = memo(function AnimatedMetricValue({
  value,
  previousValue,
  formatFn,
  className,
  highlightColor = COLORS.gold,
  animateOnChange = true,
}: AnimatedMetricValueProps) {
  const [isAnimating, setIsAnimating] = useState(false);
  const displayValue =
    typeof value === 'number' && formatFn ? formatFn(value) : String(value);
  const hasChanged = previousValue !== undefined && previousValue !== value;

  useEffect(() => {
    if (hasChanged && animateOnChange) {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 500);
      return () => clearTimeout(timer);
    }
  }, [hasChanged, animateOnChange]);

  return (
    <div className="relative inline-block">
      <AnimatePresence mode="wait">
        <motion.span
          key={String(value)}
          variants={valueChangeVariants}
          initial="initial"
          animate="enter"
          exit="exit"
          className={cn(className, isAnimating && 'highlight-pulse')}
          style={
            isAnimating
              ? {
                  '--highlight-color': highlightColor,
                } as MotionStyle
              : undefined
          }
        >
          {displayValue}
        </motion.span>
      </AnimatePresence>

      {/* Glow effect on change */}
      {isAnimating && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 0.3, scale: 1.2 }}
          exit={{ opacity: 0, scale: 1 }}
          className="absolute inset-0 rounded-md pointer-events-none"
          style={{
            background: `radial-gradient(circle, ${highlightColor}40 0%, transparent 70%)`,
          }}
        />
      )}
    </div>
  );
});

// ─── Animated Card Container ──────────────────────────────────────────

interface AnimatedCardContainerProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  accentColor?: string;
  inView?: boolean;
}

export const AnimatedCardContainer = memo(function AnimatedCardContainer({
  children,
  className,
  delay = 0,
  accentColor = COLORS.gold,
  inView = true,
}: AnimatedCardContainerProps) {
  const controls = useAnimation();
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: false, margin: '-50px' });

  useEffect(() => {
    if (isInView && inView) {
      controls.start('enter');
    } else {
      controls.start('initial');
    }
  }, [isInView, inView, controls]);

  return (
    <motion.div
      ref={ref}
      variants={filterTransitionVariants}
      initial="initial"
      animate={controls}
      transition={{ delay }}
      className={cn('relative overflow-hidden', className)}
    >
      {/* Gradient accent */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: delay + 0.1, duration: DURATION_LUXURY }}
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `linear-gradient(135deg, ${accentColor}15 0%, transparent 50%)`,
        }}
      />

      {/* Content */}
      <div className="relative">{children}</div>
    </motion.div>
  );
});

// ─── Filter Change Indicator ──────────────────────────────────────────

interface FilterChangeIndicatorProps {
  isVisible: boolean;
  message?: string;
  type?: 'add' | 'remove' | 'clear';
}

export const FilterChangeIndicator = memo(function FilterChangeIndicator({
  isVisible,
  message = 'Filter applied',
  type = 'add',
}: FilterChangeIndicatorProps) {
  const indicatorClass = type === 'add' ? 'filter-indicator-add' :
                         type === 'remove' ? 'filter-indicator-remove' : 'filter-indicator-clear';
  const dotClass = type === 'add' ? 'filter-dot-add' :
                   type === 'remove' ? 'filter-dot-remove' : 'filter-dot-clear';
  const textClass = type === 'add' ? 'filter-text-add' :
                    type === 'remove' ? 'filter-text-remove' : 'filter-text-clear';

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.9 }}
          transition={{ duration: DURATION_STANDARD, ease: EASE_LUXURY }}
          className={cn('fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg', indicatorClass)}
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{
              type: 'spring',
              stiffness: 500,
              damping: 30,
              delay: 0.1,
            }}
            className="flex items-center gap-2"
          >
            <motion.div
              className={cn('w-2 h-2 rounded-full', dotClass)}
              animate={{
                scale: [1, 1.2, 1],
                opacity: [1, 0.7, 1],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                repeatType: 'reverse',
              }}
            />
            <span className={cn('text-sm font-medium', textClass)}>
              {message}
            </span>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});

// ─── Staggered KPI Grid ───────────────────────────────────────────────

interface StaggeredKPIGridProps {
  children: React.ReactNode;
  className?: string;
}

export const StaggeredKPIGrid = memo(function StaggeredKPIGrid({
  children,
  className,
}: StaggeredKPIGridProps) {
  return (
    <motion.div
      variants={staggerContainerVariants}
      initial="initial"
      animate="enter"
      className={cn('grid grid-cols-1 md:grid-cols-2 gap-4', className)}
    >
      {children}
    </motion.div>
  );
});

// ─── Staggered KPI Card ───────────────────────────────────────────────

interface StaggeredKPICardProps {
  children: React.ReactNode;
  className?: string;
}

export const StaggeredKPICard = memo(function StaggeredKPICard({
  children,
  className,
}: StaggeredKPICardProps) {
  return (
    <motion.div variants={staggerItemVariants} className={className}>
      {children}
    </motion.div>
  );
});

// ─── Animated Progress Bar ─────────────────────────────────────────────

interface AnimatedProgressBarProps {
  value: number;
  max?: number;
  color?: string;
  className?: string;
  animateDuration?: number;
}

export const AnimatedProgressBar = memo(function AnimatedProgressBar({
  value,
  max = 100,
  color = COLORS.gold,
  className,
  animateDuration = DURATION_STANDARD,
}: AnimatedProgressBarProps) {
  const percentage = Math.min((value / max) * 100, 100);

  return (
    <div className={cn('h-2 w-full rounded-full bg-muted/20 overflow-hidden', className)}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${percentage}%` }}
        transition={{
          duration: animateDuration,
          ease: EASE_LUXURY,
        }}
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
      />
    </div>
  );
});

// ─── Animated Number Counter ───────────────────────────────────────────

interface AnimatedNumberCounterProps {
  value: number;
  duration?: number;
  formatFn?: (value: number) => string;
  className?: string;
}

export const AnimatedNumberCounter = memo(function AnimatedNumberCounter({
  value,
  duration = DURATION_LUXURY,
  formatFn = (v) => v.toLocaleString(),
  className,
}: AnimatedNumberCounterProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const previousValueRef = useRef(0);

  useEffect(() => {
    const startValue = previousValueRef.current;
    const endValue = value;
    const startTime = performance.now();
    const durationMs = duration * 1000;

    function animate(currentTime: number) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / durationMs, 1);

      // Easing function (ease-out cubic)
      const eased = 1 - Math.pow(1 - progress, 3);

      const currentValue = startValue + (endValue - startValue) * eased;
      setDisplayValue(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        previousValueRef.current = endValue;
      }
    }

    requestAnimationFrame(animate);
  }, [value, duration]);

  return (
    <motion.span
      key={value}
      initial={{ opacity: 0.7 }}
      animate={{ opacity: 1 }}
      className={className}
    >
      {formatFn(Math.round(displayValue))}
    </motion.span>
  );
});

// ─── Filter Transition Wrapper ────────────────────────────────────────

interface FilterTransitionWrapperProps {
  children: React.ReactNode;
  filterKey: string | number;
  className?: string;
}

export const FilterTransitionWrapper = memo(function FilterTransitionWrapper({
  children,
  filterKey,
  className,
}: FilterTransitionWrapperProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={filterKey}
        variants={filterTransitionVariants}
        initial="initial"
        animate="enter"
        exit="exit"
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
});

// ─── Exports ───────────────────────────────────────────────────────────

export default {
  AnimatedMetricValue,
  AnimatedCardContainer,
  FilterChangeIndicator,
  StaggeredKPIGrid,
  StaggeredKPICard,
  AnimatedProgressBar,
  AnimatedNumberCounter,
  FilterTransitionWrapper,
  filterTransitionVariants,
  valueChangeVariants,
  staggerContainerVariants,
  staggerItemVariants,
};
