import { describe, it, expect } from 'vitest';
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
  SCALE_PRESS,
  SCALE_HOVER_SUBTLE,
  FLOAT_DISTANCE,
  REDUCED_MOTION_TRANSITION,
} from '@/motion/motionTokens';
import { EASE_LUXURY, EASE_SOFT, EASE_EXIT } from '@/motion/easing';
import { durations } from '@/motion/durations';
import {
  transitionLuxury,
  transitionHero,
  transitionExit,
  springGentle,
  getTransition,
} from '@/motion/transitions';
import {
  pageVariants,
  pageVariantsReduced,
  luxuryCardVariants,
  luxuryButtonVariants,
  fabVariants,
  staggerContainer,
  crossfadeVariants,
  outfitFlyInVariants,
  motionPresets,
} from '@/motion/presets';
import {
  gesturePress,
  gestureCardHover,
  gestureGoldGlow,
  gestureFabFloat,
  gestureIconBreathe,
} from '@/motion/gestures';

describe('Motion Tokens', () => {
  it('has correct duration values', () => {
    expect(DURATION_FAST).toBe(0.16);
    expect(DURATION_STANDARD).toBe(0.24);
    expect(DURATION_LUXURY).toBe(0.32);
    expect(DURATION_HERO).toBe(0.45);
    expect(DURATION_CINEMATIC).toBe(0.6);
  });

  it('has correct spring configs', () => {
    expect(SPRING_GENTLE.type).toBe('spring');
    expect(SPRING_GENTLE.stiffness).toBe(180);
    expect(SPRING_SNAPPY.type).toBe('spring');
    expect(SPRING_BOUNCY.type).toBe('spring');
    expect(SPRING_HEAVY.mass).toBe(1.4);
    expect(SPRING_MAGNETIC.stiffness).toBe(500);
  });

  it('has correct interaction scales', () => {
    expect(SCALE_PRESS).toBe(0.97);
    expect(SCALE_HOVER_SUBTLE).toBe(1.02);
  });

  it('has reduced motion fallback', () => {
    expect(REDUCED_MOTION_TRANSITION.duration).toBe(0.01);
    expect(REDUCED_MOTION_TRANSITION.ease).toBe('linear');
  });
});

describe('Easing Curves', () => {
  it('exports easing arrays with 4 values', () => {
    expect(EASE_LUXURY).toHaveLength(4);
    expect(EASE_SOFT).toHaveLength(4);
    expect(EASE_EXIT).toHaveLength(4);
  });

  it('has correct luxury ease values', () => {
    expect(EASE_LUXURY).toEqual([0.22, 1, 0.36, 1]);
  });
});

describe('Durations', () => {
  it('exports named durations matching tokens', () => {
    expect(durations.fast).toBe(DURATION_FAST);
    expect(durations.luxury).toBe(DURATION_LUXURY);
    expect(durations.hero).toBe(DURATION_HERO);
  });
});

describe('Transitions', () => {
  it('has luxury transition with correct shape', () => {
    expect(transitionLuxury).toHaveProperty('duration', DURATION_LUXURY);
    expect(transitionLuxury).toHaveProperty('ease', EASE_LUXURY);
  });

  it('has hero transition', () => {
    expect(transitionHero).toHaveProperty('duration', DURATION_HERO);
  });

  it('has spring transitions', () => {
    expect(springGentle).toHaveProperty('type', 'spring');
  });

  it('getTransition returns reduced motion when preferred', () => {
    const result = getTransition(transitionLuxury, true);
    expect(result).toEqual(REDUCED_MOTION_TRANSITION);
  });

  it('getTransition returns original when not reduced', () => {
    const result = getTransition(transitionLuxury, false);
    expect(result).toBe(transitionLuxury);
  });
});

describe('Presets', () => {
  it('has page variants with initial/animate/exit', () => {
    expect(pageVariants).toHaveProperty('initial');
    expect(pageVariants).toHaveProperty('animate');
    expect(pageVariants).toHaveProperty('exit');
  });

  it('has reduced page variants', () => {
    expect(pageVariantsReduced).toHaveProperty('initial');
    expect(pageVariantsReduced).toHaveProperty('animate');
  });

  it('has luxury card with hover/tap states', () => {
    expect(luxuryCardVariants).toHaveProperty('initial');
    expect(luxuryCardVariants).toHaveProperty('hover');
    expect(luxuryCardVariants).toHaveProperty('tap');
  });

  it('has FAB variants', () => {
    expect(fabVariants).toHaveProperty('animate');
    expect(fabVariants).toHaveProperty('hover');
  });

  it('has crossfade for try-on', () => {
    expect(crossfadeVariants).toHaveProperty('initial');
    expect(crossfadeVariants).toHaveProperty('animate');
    expect(crossfadeVariants).toHaveProperty('exit');
  });

  it('has outfit fly-in', () => {
    expect(outfitFlyInVariants).toHaveProperty('initial');
    expect(outfitFlyInVariants).toHaveProperty('animate');
  });

  it('exports motionPresets unified object', () => {
    expect(motionPresets).toHaveProperty('page');
    expect(motionPresets).toHaveProperty('card');
    expect(motionPresets).toHaveProperty('buttonLuxury');
    expect(motionPresets).toHaveProperty('fab');
    expect(motionPresets).toHaveProperty('crossfade');
    expect(motionPresets).toHaveProperty('outfitFlyIn');
    expect(motionPresets).toHaveProperty('scrollReveal');
  });
});

describe('Gestures', () => {
  it('has press gesture with correct scale', () => {
    expect(gesturePress.scale).toBe(0.97);
  });

  it('has card hover with lift', () => {
    expect(gestureCardHover.y).toBeLessThan(0);
  });

  it('has gold glow effect', () => {
    expect(gestureGoldGlow.boxShadow).toBeDefined();
  });

  it('has FAB float animation', () => {
    expect(gestureFabFloat.y).toBeDefined();
    expect(gestureFabFloat.transition.repeat).toBe(Infinity);
  });

  it('has icon breathe animation', () => {
    expect(gestureIconBreathe.scale).toBeDefined();
    expect(gestureIconBreathe.transition.repeat).toBe(Infinity);
  });
});
