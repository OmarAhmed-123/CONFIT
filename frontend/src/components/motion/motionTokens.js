/**
 * Motion Tokens (ms) — single source of timing for UI micro-interactions.
 * Keep these aligned with `src/styles/tokens.js`.
 */
export const durationFast = 200;
export const durationBase = 300;
export const durationSlow = 400;

// Research-based luxury easing curve
export const easing = "cubic-bezier(0.4, 0, 0.2, 1)";

export const motionTokens = {
  durationFast,
  durationBase,
  durationSlow,
  easing,
};

export default motionTokens;

