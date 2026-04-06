/**
 * ScrollReveal — IntersectionObserver-driven reveal with opacity + blur reduction.
 * GPU-accelerated, reduces to simple fade under reduced motion.
 */

import React, { forwardRef } from 'react';
import { motion, type HTMLMotionProps, type Variants } from 'framer-motion';
import { scrollRevealVariants, fadeVariants } from '../presets';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface ScrollRevealProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  /** Custom variants (defaults to scrollRevealVariants) */
  variants?: Variants;
  /** Only animate once (default: true) */
  once?: boolean;
  /** Viewport amount visible to trigger (default: 0.2) */
  amount?: number;
}

export const ScrollReveal = forwardRef<HTMLDivElement, ScrollRevealProps>(
  (
    {
      children,
      variants: customVariants,
      once = true,
      amount = 0.2,
      ...props
    },
    ref
  ) => {
    const prefersReduced = useReducedMotion();
    const variants = prefersReduced
      ? fadeVariants
      : (customVariants ?? scrollRevealVariants);

    return (
      <motion.div
        ref={ref}
        initial="hidden"
        whileInView="visible"
        viewport={{ once, amount }}
        variants={variants}
        style={{ willChange: 'opacity, transform, filter' }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

ScrollReveal.displayName = 'ScrollReveal';
