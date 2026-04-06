/**
 * CONFIT Animation Presets
 * Composed Framer Motion Variants built from the token layer.
 * These are the primary animation definitions used by motion components.
 */

import type { Variants } from 'framer-motion';
import {
  DURATION_FAST,
  DURATION_STANDARD,
  DURATION_LUXURY,
  DURATION_HERO,
  DURATION_CINEMATIC,
  SCALE_PRESS,
  SCALE_HOVER_SUBTLE,
  SCALE_HOVER_CARD,
  LIFT_SUBTLE,
  LIFT_CARD,
  LIFT_HERO,
  BLUR_REVEAL_START,
  STAGGER_FAST,
  STAGGER_STANDARD,
  STAGGER_LUXURY,
  SPRING_GENTLE,
  SPRING_SNAPPY,
} from './motionTokens';
import { EASE_LUXURY, EASE_SOFT, EASE_EXIT, EASE_ELEGANT } from './easing';

// ═══════════════════════════════════════════════════════════════════
// PAGE TRANSITIONS
// ═══════════════════════════════════════════════════════════════════

export const pageVariants: Variants = {
  initial: {
    opacity: 0,
    y: 12,
    filter: `blur(${BLUR_REVEAL_START}px)`,
  },
  animate: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: DURATION_HERO,
      ease: EASE_ELEGANT,
      filter: { duration: DURATION_LUXURY },
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    filter: 'blur(2px)',
    transition: {
      duration: DURATION_STANDARD,
      ease: EASE_EXIT,
    },
  },
};

/** Reduced-motion page variants — simple fade */
export const pageVariantsReduced: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.15 } },
  exit: { opacity: 0, transition: { duration: 0.1 } },
};

// ═══════════════════════════════════════════════════════════════════
// FADE VARIANTS
// ═══════════════════════════════════════════════════════════════════

export const fadeVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  exit: {
    opacity: 0,
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

export const fadeUpVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

export const fadeDownVariants: Variants = {
  hidden: { opacity: 0, y: -20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  exit: {
    opacity: 0,
    y: 10,
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// SCROLL REVEAL
// ═══════════════════════════════════════════════════════════════════

export const scrollRevealVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 24,
    filter: `blur(${BLUR_REVEAL_START}px)`,
  },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: DURATION_HERO,
      ease: EASE_LUXURY,
      filter: { duration: DURATION_LUXURY, ease: EASE_SOFT },
    },
  },
};

// ═══════════════════════════════════════════════════════════════════
// CARD VARIANTS
// ═══════════════════════════════════════════════════════════════════

export const luxuryCardVariants: Variants = {
  initial: {
    y: 0,
    scale: 1,
    boxShadow: '0 4px 20px 0 rgba(0, 0, 0, 0.4)',
  },
  hover: {
    y: LIFT_CARD,
    scale: SCALE_HOVER_CARD,
    boxShadow: '0 16px 48px 0 rgba(0, 0, 0, 0.5), 0 0 20px 0 rgba(212, 175, 55, 0.1)',
    transition: SPRING_GENTLE,
  },
  tap: {
    y: 0,
    scale: SCALE_PRESS,
    transition: SPRING_SNAPPY,
  },
};

export const elevatedCardVariants: Variants = {
  initial: { y: 0, scale: 1 },
  hover: {
    y: LIFT_HERO,
    scale: 1.01,
    transition: { duration: DURATION_LUXURY, ease: EASE_ELEGANT },
  },
  tap: {
    scale: 0.99,
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

export const productCardVariants: Variants = {
  initial: { opacity: 0, y: 30, scale: 0.98 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: DURATION_HERO, ease: EASE_ELEGANT },
  },
  hover: {
    y: LIFT_CARD,
    transition: SPRING_GENTLE,
  },
  tap: {
    scale: 0.99,
    transition: SPRING_SNAPPY,
  },
};

export const productImageVariants: Variants = {
  initial: { scale: 1 },
  hover: {
    scale: 1.06,
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
};

// ═══════════════════════════════════════════════════════════════════
// BUTTON VARIANTS
// ═══════════════════════════════════════════════════════════════════

export const luxuryButtonVariants: Variants = {
  initial: {
    scale: 1,
    boxShadow: '0 0 0px 0 rgba(212, 175, 55, 0)',
  },
  hover: {
    scale: SCALE_HOVER_SUBTLE,
    boxShadow: '0 0 24px 0 rgba(212, 175, 55, 0.3)',
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  tap: {
    scale: SCALE_PRESS,
    boxShadow: '0 0 12px 0 rgba(212, 175, 55, 0.2)',
    transition: SPRING_SNAPPY,
  },
};

export const goldButtonVariants: Variants = {
  initial: {
    scale: 1,
    background: 'linear-gradient(135deg, #D4AF37, #B8942D)',
  },
  hover: {
    scale: 1.03,
    background: 'linear-gradient(135deg, #E8C776, #D4AF37)',
    boxShadow: '0 0 28px 0 rgba(212, 175, 55, 0.4)',
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  tap: {
    scale: SCALE_PRESS,
    boxShadow: '0 0 16px 0 rgba(212, 175, 55, 0.3)',
    transition: SPRING_SNAPPY,
  },
};

// ═══════════════════════════════════════════════════════════════════
// GOLD GLOW EFFECTS
// ═══════════════════════════════════════════════════════════════════

export const goldGlowVariants: Variants = {
  initial: { boxShadow: '0 0 0px 0 rgba(212, 175, 55, 0)' },
  hover: {
    boxShadow: '0 0 30px 0 rgba(212, 175, 55, 0.25)',
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  active: {
    boxShadow: '0 0 20px 0 rgba(212, 175, 55, 0.35)',
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

export const goldShimmerVariants: Variants = {
  initial: { backgroundPosition: '200% 0' },
  animate: {
    backgroundPosition: '-200% 0',
    transition: { duration: 2.5, ease: 'linear', repeat: Infinity },
  },
};

// ═══════════════════════════════════════════════════════════════════
// STAGGER CONTAINERS
// ═══════════════════════════════════════════════════════════════════

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: STAGGER_LUXURY,
      delayChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      staggerChildren: STAGGER_FAST,
      staggerDirection: -1,
    },
  },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// MODAL / DIALOG
// ═══════════════════════════════════════════════════════════════════

export const modalOverlayVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: DURATION_STANDARD } },
  exit: { opacity: 0, transition: { duration: DURATION_FAST } },
};

export const modalContentVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: SPRING_GENTLE,
  },
  exit: {
    opacity: 0,
    scale: 0.98,
    y: 10,
    transition: { duration: DURATION_STANDARD, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// DRAWER / SHEET
// ═══════════════════════════════════════════════════════════════════

export const drawerRightVariants: Variants = {
  hidden: { x: '100%' },
  visible: { x: 0, transition: SPRING_GENTLE },
  exit: {
    x: '100%',
    transition: { duration: DURATION_LUXURY, ease: EASE_EXIT },
  },
};

export const drawerBottomVariants: Variants = {
  hidden: { y: '100%' },
  visible: { y: 0, transition: SPRING_GENTLE },
  exit: {
    y: '100%',
    transition: { duration: DURATION_LUXURY, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// FAB
// ═══════════════════════════════════════════════════════════════════

export const fabVariants: Variants = {
  initial: { scale: 0, opacity: 0 },
  animate: {
    scale: 1,
    opacity: 1,
    transition: SPRING_GENTLE,
  },
  hover: {
    scale: 1.1,
    boxShadow: '0 0 30px 0 rgba(212, 175, 55, 0.4)',
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  tap: {
    scale: 0.95,
    transition: SPRING_SNAPPY,
  },
};

// ═══════════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════════

export const navItemVariants: Variants = {
  initial: { opacity: 0.7 },
  hover: {
    opacity: 1,
    transition: { duration: DURATION_FAST, ease: EASE_SOFT },
  },
  active: { opacity: 1, color: '#D4AF37' },
};

export const navUnderlineVariants: Variants = {
  initial: { scaleX: 0, originX: 0 },
  animate: {
    scaleX: 1,
    transition: { duration: DURATION_LUXURY, ease: EASE_LUXURY },
  },
  exit: {
    scaleX: 0,
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// HERO TEXT
// ═══════════════════════════════════════════════════════════════════

export const heroTextVariants: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.1,
      duration: DURATION_HERO,
      ease: EASE_ELEGANT,
    },
  }),
};

// ═══════════════════════════════════════════════════════════════════
// TOOLTIP / DROPDOWN / TOAST
// ═══════════════════════════════════════════════════════════════════

export const tooltipVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: DURATION_FAST, ease: EASE_SOFT },
  },
  exit: { opacity: 0, scale: 0.95, transition: { duration: 0.1 } },
};

export const dropdownVariants: Variants = {
  hidden: { opacity: 0, y: -8, scale: 0.96 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: DURATION_STANDARD, ease: EASE_LUXURY },
  },
  exit: {
    opacity: 0,
    y: -8,
    scale: 0.96,
    transition: { duration: DURATION_FAST, ease: EASE_EXIT },
  },
};

export const toastVariants: Variants = {
  hidden: { opacity: 0, x: 80, scale: 0.92 },
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: SPRING_SNAPPY,
  },
  exit: {
    opacity: 0,
    x: 80,
    scale: 0.92,
    transition: { duration: DURATION_STANDARD, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// LOADING
// ═══════════════════════════════════════════════════════════════════

export const pulseVariants: Variants = {
  initial: { opacity: 0.4 },
  animate: {
    opacity: [0.4, 0.8, 0.4],
    transition: { duration: 1.5, ease: 'easeInOut', repeat: Infinity },
  },
};

export const shimmerVariants: Variants = {
  initial: { x: '-100%' },
  animate: {
    x: '100%',
    transition: { duration: 1.5, ease: 'easeInOut', repeat: Infinity, repeatDelay: 0.5 },
  },
};

// ═══════════════════════════════════════════════════════════════════
// CROSSFADE (Try-On)
// ═══════════════════════════════════════════════════════════════════

export const crossfadeVariants: Variants = {
  initial: { opacity: 0, scale: 1.02 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: { duration: DURATION_LUXURY, ease: EASE_SOFT },
  },
  exit: {
    opacity: 0,
    scale: 0.98,
    transition: { duration: DURATION_STANDARD, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// OUTFIT BUILDER (Fly-in)
// ═══════════════════════════════════════════════════════════════════

export const outfitFlyInVariants: Variants = {
  initial: { opacity: 0, scale: 0.6, y: 40 },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: SPRING_GENTLE,
  },
  exit: {
    opacity: 0,
    scale: 0.8,
    y: -20,
    transition: { duration: DURATION_STANDARD, ease: EASE_EXIT },
  },
};

// ═══════════════════════════════════════════════════════════════════
// ACCORDION
// ═══════════════════════════════════════════════════════════════════

export const accordionVariants: Variants = {
  collapsed: {
    height: 0,
    opacity: 0,
    transition: { duration: DURATION_STANDARD, ease: EASE_EXIT },
  },
  expanded: {
    height: 'auto',
    opacity: 1,
    transition: {
      duration: DURATION_LUXURY,
      ease: EASE_LUXURY,
      height: { duration: DURATION_LUXURY },
    },
  },
};

// ═══════════════════════════════════════════════════════════════════
// UNIFIED EXPORT OBJECT
// ═══════════════════════════════════════════════════════════════════

export const motionPresets = {
  page: pageVariants,
  pageReduced: pageVariantsReduced,
  fade: fadeVariants,
  fadeUp: fadeUpVariants,
  fadeDown: fadeDownVariants,
  scrollReveal: scrollRevealVariants,
  card: luxuryCardVariants,
  cardElevated: elevatedCardVariants,
  cardProduct: productCardVariants,
  productImage: productImageVariants,
  buttonLuxury: luxuryButtonVariants,
  buttonGold: goldButtonVariants,
  goldGlow: goldGlowVariants,
  goldShimmer: goldShimmerVariants,
  staggerContainer,
  staggerItem,
  modalOverlay: modalOverlayVariants,
  modalContent: modalContentVariants,
  drawerRight: drawerRightVariants,
  drawerBottom: drawerBottomVariants,
  fab: fabVariants,
  navItem: navItemVariants,
  navUnderline: navUnderlineVariants,
  heroText: heroTextVariants,
  tooltip: tooltipVariants,
  dropdown: dropdownVariants,
  toast: toastVariants,
  pulse: pulseVariants,
  shimmer: shimmerVariants,
  crossfade: crossfadeVariants,
  outfitFlyIn: outfitFlyInVariants,
  accordion: accordionVariants,
} as const;

export type MotionPresets = typeof motionPresets;
