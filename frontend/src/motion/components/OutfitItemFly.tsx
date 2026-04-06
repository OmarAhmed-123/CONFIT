/**
 * OutfitItemFly — Item fly-in animation for the outfit builder.
 * Soft magnetic alignment with elastic snap via spring physics.
 * Must feel tactile — items "fly" into the outfit canvas.
 */

import React, { forwardRef } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { outfitFlyInVariants, fadeVariants } from '../presets';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { createTransition } from '@/motion';

interface OutfitItemFlyProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  /** Delay before animation starts (for stagger effect) */
  delay?: number;
}

export const OutfitItemFly = forwardRef<HTMLDivElement, OutfitItemFlyProps>(
  ({ children, delay = 0, ...props }, ref) => {
    const prefersReduced = useReducedMotion();
    const variants = prefersReduced ? fadeVariants : outfitFlyInVariants;

    return (
      <motion.div
        ref={ref}
        variants={variants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={createTransition({ delay })}
        style={{ willChange: 'opacity, transform' }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

OutfitItemFly.displayName = 'OutfitItemFly';
