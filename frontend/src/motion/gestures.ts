/**
 * CONFIT Gesture Presets
 * Reusable gesture configurations for whileHover, whileTap, whileDrag.
 * All gestures use spring physics for natural, tactile feel.
 */

import type { TargetAndTransition } from 'framer-motion';
import {
  SCALE_PRESS,
  SCALE_HOVER_SUBTLE,
  SCALE_HOVER_CARD,
  LIFT_SUBTLE,
  LIFT_CARD,
  FLOAT_DISTANCE,
  FLOAT_DURATION,
  BREATHING_SCALE,
  BREATHING_DURATION,
  SPRING_SNAPPY,
  SPRING_GENTLE,
} from './motionTokens';
import { EASE_LUXURY, EASE_IN_OUT } from './easing';
import { DURATION_LUXURY } from './motionTokens';

// ─── Button Gestures ─────────────────────────────────────────────

/** Soft press — scale down to 0.97 with snappy spring */
export const gesturePress: TargetAndTransition = {
  scale: SCALE_PRESS,
  transition: SPRING_SNAPPY,
};

/** Button hover — subtle scale up */
export const gestureButtonHover: TargetAndTransition = {
  scale: SCALE_HOVER_SUBTLE,
  transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
};

// ─── Card Gestures ───────────────────────────────────────────────

/** Card hover — lift + subtle scale for elevation feel */
export const gestureCardHover: TargetAndTransition = {
  y: LIFT_CARD,
  scale: SCALE_HOVER_CARD,
  transition: SPRING_GENTLE,
};

/** Card press — settle back with quick feedback */
export const gestureCardPress: TargetAndTransition = {
  scale: SCALE_PRESS,
  y: 0,
  transition: SPRING_SNAPPY,
};

// ─── Shadow Bloom ────────────────────────────────────────────────

/** Gold glow hover — for luxury buttons and CTAs */
export const gestureGoldGlow: TargetAndTransition = {
  boxShadow: '0 0 30px 0 rgba(212, 175, 55, 0.3)',
  transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
};

/** Shadow bloom hover — depth elevation for cards */
export const gestureShadowBloom: TargetAndTransition = {
  boxShadow: '0 16px 48px 0 rgba(0, 0, 0, 0.5), 0 0 20px 0 rgba(212, 175, 55, 0.1)',
  transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
};

// ─── Idle / Ambient Animations ───────────────────────────────────

/** FAB floating idle — gentle bobbing motion */
export const gestureFabFloat = {
  y: [-FLOAT_DISTANCE, FLOAT_DISTANCE, -FLOAT_DISTANCE] as number[],
  transition: {
    duration: FLOAT_DURATION,
    repeat: Infinity,
    ease: 'easeInOut' as const,
  },
};

/** Icon breathing — subtle scale pulse */
export const gestureIconBreathe = {
  scale: BREATHING_SCALE as unknown as number[],
  transition: {
    duration: BREATHING_DURATION,
    repeat: Infinity,
    ease: EASE_IN_OUT,
  },
};

// ─── Gold Shimmer ────────────────────────────────────────────────

/** Gold shimmer sweep — background-position animation for gradient overlay */
export const gestureGoldShimmer = {
  backgroundPosition: ['200% 0', '-200% 0'],
  transition: {
    duration: 2.5,
    repeat: Infinity,
    ease: 'linear' as const,
  },
};
