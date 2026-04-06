/**
 * LuxuryMotionButton — Gold shimmer hover glow + spring press.
 * Wraps any button content with luxury motion behavior.
 */

import React, { forwardRef } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { luxuryButtonVariants } from '../presets';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { SCALE_PRESS } from '../motionTokens';

interface LuxuryMotionButtonProps extends HTMLMotionProps<'button'> {
  children: React.ReactNode;
}

export const LuxuryMotionButton = forwardRef<HTMLButtonElement, LuxuryMotionButtonProps>(
  ({ children, ...props }, ref) => {
    const prefersReduced = useReducedMotion();

    return (
      <motion.button
        ref={ref}
        variants={prefersReduced ? undefined : luxuryButtonVariants}
        initial="initial"
        whileHover={prefersReduced ? undefined : 'hover'}
        whileTap={prefersReduced ? { scale: SCALE_PRESS } : 'tap'}
        {...props}
      >
        {children}
      </motion.button>
    );
  }
);

LuxuryMotionButton.displayName = 'LuxuryMotionButton';
