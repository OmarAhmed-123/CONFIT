/**
 * CONFIT Duration Constants
 * Named duration exports for semantic usage.
 * All values in seconds (Framer Motion convention).
 */

import {
  DURATION_FAST,
  DURATION_STANDARD,
  DURATION_LUXURY,
  DURATION_HERO,
  DURATION_CINEMATIC,
} from './motionTokens';

export const durations = {
  /** 160ms — micro interactions, button press feedback */
  fast: DURATION_FAST,
  /** 240ms — standard UI responses, hover states */
  standard: DURATION_STANDARD,
  /** 320ms — luxury transitions, card lifts, reveals */
  luxury: DURATION_LUXURY,
  /** 450ms — hero transitions, page-level cinematic motion */
  hero: DURATION_HERO,
  /** 600ms — full cinematic sequences, dramatic reveals */
  cinematic: DURATION_CINEMATIC,
} as const;

export type DurationKey = keyof typeof durations;
