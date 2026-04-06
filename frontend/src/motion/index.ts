/**
 * CONFIT Motion System — Barrel Export
 * Single import point: import { ... } from '@/motion'
 */

// ─── Token Layer ─────────────────────────────────────────────────
export * from './motionTokens';
export * from './easing';
export { durations, type DurationKey } from './durations';
export * from './transitions';
export * from './gestures';

// ─── Presets ─────────────────────────────────────────────────────
export * from './presets';
export { motionPresets, type MotionPresets } from './presets';

// ─── Components ──────────────────────────────────────────────────
export { PageTransition } from './components/PageTransition';
export { ScrollReveal } from './components/ScrollReveal';
export { LuxuryMotionButton } from './components/LuxuryButton';
export { LuxuryMotionCard } from './components/LuxuryMotionCard';
export { FabIdleMotion } from './components/FabIdleMotion';
export { GarmentCrossfade } from './components/GarmentCrossfade';
export { OutfitItemFly } from './components/OutfitItemFly';
export { StaggerContainer, StaggerItem } from './components/Stagger';

// ─── Hooks ───────────────────────────────────────────────────────
export { useReducedMotion } from './hooks/useReducedMotion';
export { useScrollReveal } from './hooks/useScrollReveal';
export { useParallax } from './hooks/useParallax';
