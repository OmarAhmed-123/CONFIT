/**
 * CONFIT Easing Curves
 * Premium easing functions for luxury motion feel.
 * All curves tuned for calm, elegant, weight-aware animation.
 */

// ─── Named Easing Curves ─────────────────────────────────────────

/** Primary luxury ease — slow decel, feels premium & confident */
export const EASE_LUXURY: [number, number, number, number] = [0.22, 1, 0.36, 1];

/** Soft ease — gentle decel for subtle interactions */
export const EASE_SOFT: [number, number, number, number] = [0.25, 0.8, 0.25, 1];

/** Elegant entrance — wide decel for hero reveals */
export const EASE_ELEGANT: [number, number, number, number] = [0.16, 1, 0.3, 1];

/** Smooth exit — quick settle for departing elements */
export const EASE_EXIT: [number, number, number, number] = [0.4, 0, 0.2, 1];

/** Expo out — dramatic deceleration for cinematic moments */
export const EASE_EXPO_OUT: [number, number, number, number] = [0.16, 1, 0.3, 1];

/** Quart out — balanced decel for general motion */
export const EASE_QUART_OUT: [number, number, number, number] = [0.25, 1, 0.5, 1];

/** In-out symmetric — for looping/idle animations */
export const EASE_IN_OUT: [number, number, number, number] = [0.76, 0, 0.24, 1];

// ─── CSS Custom Property Strings ─────────────────────────────────
export const CSS_EASE_LUXURY = 'cubic-bezier(0.22, 1, 0.36, 1)';
export const CSS_EASE_SOFT = 'cubic-bezier(0.25, 0.8, 0.25, 1)';
export const CSS_EASE_EXIT = 'cubic-bezier(0.4, 0, 0.2, 1)';
