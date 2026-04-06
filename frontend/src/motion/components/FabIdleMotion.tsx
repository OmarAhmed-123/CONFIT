/**
 * FabIdleMotion — Floating idle animation wrapper for FABs.
 * Gentle bobbing with spring keyframes. Composable.
 */

import React, { forwardRef } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { FLOAT_DISTANCE, FLOAT_DURATION } from '../motionTokens';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface FabIdleMotionProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  /** Bobbing distance in px (default: 6) */
  distance?: number;
  /** Cycle duration in seconds (default: 4) */
  duration?: number;
}

export const FabIdleMotion = forwardRef<HTMLDivElement, FabIdleMotionProps>(
  (
    {
      children,
      distance = FLOAT_DISTANCE,
      duration = FLOAT_DURATION,
      ...props
    },
    ref
  ) => {
    const prefersReduced = useReducedMotion();

    return (
      <motion.div
        ref={ref}
        animate={
          prefersReduced
            ? undefined
            : {
                y: [-distance, distance, -distance],
              }
        }
        transition={
          prefersReduced
            ? undefined
            : {
                duration,
                repeat: Infinity,
                ease: 'easeInOut',
              }
        }
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

FabIdleMotion.displayName = 'FabIdleMotion';
