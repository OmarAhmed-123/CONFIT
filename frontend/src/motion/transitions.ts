/**
 * CONFIT Transition Presets
 * Composed Framer Motion Transition objects combining easing + duration tokens.
 * Use these directly on motion components.
 */

import type { Transition } from 'framer-motion';
import {
  DURATION_FAST,
  DURATION_STANDARD,
  DURATION_LUXURY,
  DURATION_HERO,
  DURATION_CINEMATIC,
  SPRING_GENTLE,
  SPRING_SNAPPY,
  SPRING_BOUNCY,
  SPRING_HEAVY,
  SPRING_MAGNETIC,
  REDUCED_MOTION_TRANSITION,
} from './motionTokens';
import { EASE_LUXURY, EASE_SOFT, EASE_EXIT, EASE_ELEGANT } from './easing';

// ─── Tween Transitions ──────────────────────────────────────────

/** Fast micro-interaction (button press, toggle) */
export const transitionFast: Transition = {
  duration: DURATION_FAST,
  ease: EASE_SOFT,
};

/** Standard UI response (hover state, focus ring) */
export const transitionStandard: Transition = {
  duration: DURATION_STANDARD,
  ease: EASE_LUXURY,
};

/** Luxury timing (card lift, reveal, elevation change) */
export const transitionLuxury: Transition = {
  duration: DURATION_LUXURY,
  ease: EASE_LUXURY,
};

/** Hero transition (page enter, cinematic reveal) */
export const transitionHero: Transition = {
  duration: DURATION_HERO,
  ease: EASE_ELEGANT,
};

/** Cinematic transition (full-page, dramatic sequences) */
export const transitionCinematic: Transition = {
  duration: DURATION_CINEMATIC,
  ease: EASE_ELEGANT,
};

/** Exit transition (element departure) */
export const transitionExit: Transition = {
  duration: DURATION_STANDARD,
  ease: EASE_EXIT,
};

// ─── Spring Transitions ─────────────────────────────────────────

/** Gentle spring — card reveals, modals */
export const springGentle: Transition = SPRING_GENTLE;

/** Snappy spring — button feedback, quick responses */
export const springSnappy: Transition = SPRING_SNAPPY;

/** Bouncy spring — playful emphasis (use sparingly) */
export const springBouncy: Transition = SPRING_BOUNCY;

/** Heavy spring — weighted elements, deliberate motion */
export const springHeavy: Transition = SPRING_HEAVY;

/** Magnetic spring — snap-to-position, outfit builder alignment */
export const springMagnetic: Transition = SPRING_MAGNETIC;

// ─── Utility ─────────────────────────────────────────────────────

/**
 * Returns the appropriate transition respecting reduced-motion preference.
 * Call at render time with the result of useReducedMotion().
 */
export function getTransition(
  transition: Transition,
  prefersReduced: boolean
): Transition {
  return prefersReduced ? REDUCED_MOTION_TRANSITION : transition;
}

export function createStaggerTransition(
  index: number,
  step = 0.05,
  maxDelay = 0.3,
  transition: Transition = transitionStandard
): Transition {
  return {
    ...transition,
    delay: Math.min(index * step, maxDelay),
  };
}


export function createTransition(overrides: Transition = {}): Transition {
  return {
    ...transitionStandard,
    ...overrides,
  };
}

export const transitionLinearLoop: Transition = {
  duration: 1,
  repeat: Infinity,
  ease: 'linear',
};

export function createLoopTransition(delay = 0, duration = 0.6): Transition {
  return {
    duration,
    repeat: Infinity,
    delay,
  };
}
