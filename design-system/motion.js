/**
 * CONFIT Design System — Motion Tokens
 * Durations are tuned for premium micro-interactions (200–1200ms).
 */

import { tokens } from "./tokens.js";

export const motion = {
  duration: {
    instant: 0,
    fast: 200,
    normal: 300,
    slow: 500,
    slowest: 800,
    cinematic: 1200,
  },
  easing: {
    // Luxury cubic-bezier curves
    luxury: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
    elegant: "cubic-bezier(0.16, 1, 0.3, 1)",
    smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
    bounce: "cubic-bezier(0.34, 1.56, 0.64, 1)",
    linear: "linear",
  },
  presets: {
    hover: {
      scale: 1.06,
      glow: 1,
      elevation: true,
      durationMs: 220,
      easing: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
    },
    entrance: {
      durationMs: 650,
      easing: "cubic-bezier(0.16, 1, 0.3, 1)",
      from: { opacity: 0, y: 18, filter: "blur(10px)" },
      to: { opacity: 1, y: 0, filter: "blur(0px)" },
    },
    exit: {
      durationMs: 380,
      easing: "cubic-bezier(0.4, 0, 0.2, 1)",
      from: { opacity: 1, y: 0, filter: "blur(0px)" },
      to: { opacity: 0, y: -8, filter: "blur(8px)" },
    },
    scrollReveal: {
      staggerMs: 70,
      durationMs: 720,
      easing: "cubic-bezier(0.16, 1, 0.3, 1)",
    },
    magneticButton: {
      strength: 10,
      maxTranslatePx: 12,
      glowOpacity: 0.2,
    },
  },
  reference: {
    unit: tokens.spacing.unit,
    borderRadius: tokens.radius,
  },
};

