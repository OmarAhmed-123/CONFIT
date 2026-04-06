/**
 * useParallax — GPU-accelerated parallax effect.
 * Uses transform: translate3d only (no layout properties).
 * Passive scroll listener for 60fps performance.
 */

import { useRef, useState, useEffect, useCallback } from 'react';
import { PARALLAX_MEDIUM } from '../motionTokens';
import { useReducedMotion } from './useReducedMotion';

interface UseParallaxOptions {
  /** Speed multiplier (0-1). Default: 0.5 */
  speed?: number;
}

export function useParallax(options: UseParallaxOptions = {}) {
  const { speed = PARALLAX_MEDIUM } = options;
  const ref = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState(0);
  const prefersReduced = useReducedMotion();

  const handleScroll = useCallback(() => {
    if (!ref.current || prefersReduced) return;

    const rect = ref.current.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    // Normalized position: 0 = element at bottom of viewport, 1 = at top
    const normalized =
      (viewportHeight - rect.top) / (viewportHeight + rect.height);
    setOffset((normalized - 0.5) * speed * 100);
  }, [speed, prefersReduced]);

  useEffect(() => {
    if (prefersReduced) return;

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial calculation
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll, prefersReduced]);

  return {
    ref,
    /** Y-axis offset in px. Apply as transform: translateY(${offset}px) */
    offset,
    /** Inline style ready to spread onto an element */
    style: {
      transform: `translate3d(0, ${prefersReduced ? 0 : offset}px, 0)`,
      willChange: prefersReduced ? undefined : ('transform' as const),
    },
  };
}
