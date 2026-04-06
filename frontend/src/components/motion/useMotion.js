import { durationFast, durationBase, durationSlow, easing } from "./motionTokens";

export function useMotion() {
  return {
    durationFast,
    durationBase,
    durationSlow,
    easing,

    // Shared hover/press/tap micro-interactions
    hoverLift: { y: -4, scale: 1.04 },
    hoverScale: { scale: 1.04 },
    hoverGlow: {
      // Keep it mostly to transforms; glow can be applied via CSS utility classes.
      scale: 1.02,
    },
    press: { scale: 0.97 },
  };
}

export { durationFast, durationBase, durationSlow, easing };

