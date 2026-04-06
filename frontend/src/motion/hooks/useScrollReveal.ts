/**
 * useScrollReveal — IntersectionObserver-based reveal hook.
 * Returns a ref and animation controls for scroll-triggered reveals.
 * Uses Framer Motion's useInView for optimized IO integration.
 */

import { useRef, useEffect } from 'react';
import { useAnimation, useInView } from 'framer-motion';

interface UseScrollRevealOptions {
  /** IO threshold (0-1). Default: 0.2 */
  threshold?: number;
  /** Only animate once. Default: true */
  once?: boolean;
}

export function useScrollReveal(options: UseScrollRevealOptions = {}) {
  const { threshold = 0.2, once = true } = options;
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once, amount: threshold });
  const controls = useAnimation();

  useEffect(() => {
    if (isInView) {
      controls.start('visible');
    }
  }, [isInView, controls]);

  return {
    ref,
    controls,
    isInView,
  };
}
