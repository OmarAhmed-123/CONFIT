/**
 * CONFIT Dark Luxury Design System
 * Main entry point for all design system exports
 *
 * Animation system is now centralized in @/motion.
 * This file provides backward-compatible re-exports so existing
 * imports from '@/design-system' continue to work.
 */

// Design Tokens
export * from './tokens';
export { designTokens } from './tokens';

// Re-export commonly used token items
export { colors, typography, spacing, shadows, borderRadius, animation, glass } from './tokens';

// ─── Backward-compatible animation re-exports (source: @/motion) ─────
export {
  luxuryCardVariants,
  elevatedCardVariants,
  productCardVariants,
  luxuryButtonVariants,
  goldButtonVariants,
  goldGlowVariants,
  goldShimmerVariants,
  staggerContainer,
  staggerItem,
  modalOverlayVariants,
  modalContentVariants,
  fabVariants,
  productImageVariants,
  fadeVariants as fadeIn,
  fadeUpVariants as fadeInUp,
  fadeDownVariants as fadeInDown,
  scrollRevealVariants,
  navItemVariants,
  navUnderlineVariants,
  heroTextVariants,
  tooltipVariants,
  dropdownVariants,
  toastVariants,
  pulseVariants,
  shimmerVariants,
  crossfadeVariants,
  outfitFlyInVariants,
  drawerRightVariants,
  drawerBottomVariants,
  accordionVariants,
  pageVariants as pageTransition,
} from '@/motion/presets';

export {
  transitionLuxury as luxuryTransition,
  transitionHero as elegantTransition,
  transitionExit as smoothTransition,
  transitionFast,
  transitionStandard,
  transitionCinematic,
  springGentle,
  springSnappy,
  springBouncy,
  springHeavy,
  springMagnetic,
} from '@/motion/transitions';
