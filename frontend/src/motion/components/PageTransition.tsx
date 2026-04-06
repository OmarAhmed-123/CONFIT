/**
 * PageTransition — Cinematic page wrapper with fade + upward motion + blur.
 * Use with AnimatePresence for route transitions.
 */

import React, { forwardRef } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { pageVariants, pageVariantsReduced } from '../presets';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface PageTransitionProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
}

export const PageTransition = forwardRef<HTMLDivElement, PageTransitionProps>(
  ({ children, ...props }, ref) => {
    const prefersReduced = useReducedMotion();
    const variants = prefersReduced ? pageVariantsReduced : pageVariants;

    return (
      <motion.div
        ref={ref}
        initial="initial"
        animate="animate"
        exit="exit"
        variants={variants}
        style={{ willChange: 'opacity, transform, filter' }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

PageTransition.displayName = 'PageTransition';
