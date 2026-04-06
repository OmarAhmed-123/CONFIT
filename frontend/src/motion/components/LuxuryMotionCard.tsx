/**
 * LuxuryMotionCard — Hover elevation + shadow bloom.
 * Spring physics for natural, weight-aware feel.
 */

import React, { forwardRef } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { luxuryCardVariants } from '../presets';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface LuxuryMotionCardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  /** Disable hover interactions */
  disableHover?: boolean;
}

export const LuxuryMotionCard = forwardRef<HTMLDivElement, LuxuryMotionCardProps>(
  ({ children, disableHover = false, ...props }, ref) => {
    const prefersReduced = useReducedMotion();
    const interactive = !disableHover && !prefersReduced;

    return (
      <motion.div
        ref={ref}
        variants={interactive ? luxuryCardVariants : undefined}
        initial="initial"
        whileHover={interactive ? 'hover' : undefined}
        whileTap={interactive ? 'tap' : undefined}
        style={{ willChange: interactive ? 'transform, box-shadow' : undefined }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

LuxuryMotionCard.displayName = 'LuxuryMotionCard';
