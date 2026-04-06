/**
 * CONFIT Motion Tokens
 * Single source of truth for all motion timing, spring, and physics values.
 * Designed for luxury, calm, weight-aware motion.
 */

// ─── Duration Tokens (seconds) ───────────────────────────────────
export const DURATION_FAST = 0.16;
export const DURATION_STANDARD = 0.24;
export const DURATION_LUXURY = 0.32;
export const DURATION_HERO = 0.45;
export const DURATION_CINEMATIC = 0.6;

// ─── Spring Configs ──────────────────────────────────────────────
export const SPRING_GENTLE = { type: 'spring' as const, stiffness: 180, damping: 24, mass: 1 };
export const SPRING_SNAPPY = { type: 'spring' as const, stiffness: 300, damping: 30, mass: 0.8 };
export const SPRING_BOUNCY = { type: 'spring' as const, stiffness: 400, damping: 20, mass: 0.6 };
export const SPRING_HEAVY  = { type: 'spring' as const, stiffness: 120, damping: 20, mass: 1.4 };
export const SPRING_MAGNETIC = { type: 'spring' as const, stiffness: 500, damping: 35, mass: 0.5 };

// ─── Stagger Delays (seconds) ────────────────────────────────────
export const STAGGER_FAST = 0.04;
export const STAGGER_STANDARD = 0.06;
export const STAGGER_LUXURY = 0.08;

// ─── Scale Values ────────────────────────────────────────────────
export const SCALE_PRESS = 0.97;
export const SCALE_HOVER_SUBTLE = 1.02;
export const SCALE_HOVER_CARD = 1.015;
export const SCALE_EXPAND = 1.05;

// ─── Elevation (Y offsets in px) ─────────────────────────────────
export const LIFT_SUBTLE = -4;
export const LIFT_CARD = -6;
export const LIFT_HERO = -8;

// ─── Blur Values (px) ────────────────────────────────────────────
export const BLUR_REVEAL_START = 4;
export const BLUR_REVEAL_END = 0;

// ─── Parallax Speed Multipliers ──────────────────────────────────
export const PARALLAX_SLOW = 0.3;
export const PARALLAX_MEDIUM = 0.5;
export const PARALLAX_FAST = 0.8;

// ─── Floating Idle Motion ────────────────────────────────────────
export const FLOAT_DISTANCE = 6;
export const FLOAT_DURATION = 4;
export const BREATHING_SCALE = [1, 1.03, 1] as const;
export const BREATHING_DURATION = 3;

// ─── Reduced Motion Fallbacks ────────────────────────────────────
export const REDUCED_MOTION_DURATION = 0.01;
export const REDUCED_MOTION_TRANSITION = {
  duration: REDUCED_MOTION_DURATION,
  ease: 'linear' as const,
};
