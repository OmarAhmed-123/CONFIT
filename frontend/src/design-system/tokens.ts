/**
 * CONFIT Dark Luxury Design System Tokens
 * Style: "Dark Luxury — Confidence, Styled"
 */

// ═══════════════════════════════════════════════════════════════
// COLOR SYSTEM
// ═══════════════════════════════════════════════════════════════

export const colors = {
  // Primary Background - Deep Navy / Midnight Blue
  midnight: {
    50: '#E8E9EC',
    100: '#C5C7CE',
    200: '#9DA1AC',
    300: '#757B8A',
    400: '#4D5568',
    500: '#252F46',
    600: '#1E2638',
    700: '#171D2A',
    800: '#10141C',
    900: '#0B0F1A', // Primary background
    950: '#060810',
  },

  // Luxury Gold Accent
  gold: {
    50: '#FBF6E8',
    100: '#F5E9C4',
    200: '#EED89D',
    300: '#E8C776',
    400: '#E1B64F',
    500: '#D4AF37', // Primary gold accent
    600: '#B8942D',
    700: '#9C7924',
    800: '#805F1A',
    900: '#644411',
    950: '#482A0B',
  },

  // Text Colors
  text: {
    primary: '#F5F5F5',    // Soft White
    secondary: '#A0A3A8',  // Muted Gray
    tertiary: '#6B6E73',   // Subtle Gray
    disabled: '#4A4D52',   // Disabled state
  },

  // Surface Colors
  surface: {
    elevated: '#151925',   // Elevated card background
    glass: '#1A1F2E',      // Glass container base
    glassLight: '#222838', // Glass hover state
    overlay: '#0D1117',    // Modal overlay
  },

  // Semantic Colors
  semantic: {
    success: '#4ADE80',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#60A5FA',
  },

  // Border Colors
  border: {
    subtle: 'rgba(255, 255, 255, 0.06)',
    default: 'rgba(255, 255, 255, 0.10)',
    emphasis: 'rgba(255, 255, 255, 0.15)',
    gold: 'rgba(212, 175, 55, 0.30)',
    goldBright: 'rgba(212, 175, 55, 0.50)',
  },
} as const;

// ═══════════════════════════════════════════════════════════════
// TYPOGRAPHY SYSTEM
// ═══════════════════════════════════════════════════════════════

export const typography = {
  fontFamily: {
    display: ['Playfair Display', 'Georgia', 'serif'].join(', '),
    body: ['Inter', 'system-ui', 'sans-serif'].join(', '),
    mono: ['JetBrains Mono', 'monospace'].join(', '),
  },

  fontSize: {
    '2xs': ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.05em' }],
    xs: ['0.75rem', { lineHeight: '1rem', letterSpacing: '0.025em' }],
    sm: ['0.875rem', { lineHeight: '1.25rem', letterSpacing: '0.015em' }],
    base: ['1rem', { lineHeight: '1.5rem', letterSpacing: '0' }],
    lg: ['1.125rem', { lineHeight: '1.75rem', letterSpacing: '-0.005em' }],
    xl: ['1.25rem', { lineHeight: '1.875rem', letterSpacing: '-0.01em' }],
    '2xl': ['1.5rem', { lineHeight: '2rem', letterSpacing: '-0.015em' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.02em' }],
    '4xl': ['2.25rem', { lineHeight: '2.5rem', letterSpacing: '-0.025em' }],
    '5xl': ['3rem', { lineHeight: '3.5rem', letterSpacing: '-0.03em' }],
    '6xl': ['3.75rem', { lineHeight: '4.5rem', letterSpacing: '-0.035em' }],
    '7xl': ['4.5rem', { lineHeight: '5.5rem', letterSpacing: '-0.04em' }],
    '8xl': ['6rem', { lineHeight: '7rem', letterSpacing: '-0.045em' }],
  },

  fontWeight: {
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
  },
} as const;

// ═══════════════════════════════════════════════════════════════
// SPACING SYSTEM (8px Grid)
// ═══════════════════════════════════════════════════════════════

export const spacing = {
  px: '1px',
  0: '0',
  0.5: '0.125rem',  // 2px
  1: '0.25rem',     // 4px
  1.5: '0.375rem',  // 6px
  2: '0.5rem',      // 8px - Base unit
  2.5: '0.625rem',  // 10px
  3: '0.75rem',     // 12px
  3.5: '0.875rem',  // 14px
  4: '1rem',        // 16px
  5: '1.25rem',     // 20px
  6: '1.5rem',      // 24px
  7: '1.75rem',     // 28px
  8: '2rem',        // 32px
  9: '2.25rem',     // 36px
  10: '2.5rem',     // 40px
  11: '2.75rem',    // 44px
  12: '3rem',       // 48px
  14: '3.5rem',     // 56px
  16: '4rem',       // 64px
  20: '5rem',       // 80px
  24: '6rem',       // 96px
  28: '7rem',       // 112px
  32: '8rem',       // 128px
  36: '9rem',       // 144px
  40: '10rem',      // 160px
  44: '11rem',      // 176px
  48: '12rem',      // 192px
  52: '13rem',      // 208px
  56: '14rem',      // 224px
  60: '15rem',      // 240px
  64: '16rem',      // 256px
  72: '18rem',      // 288px
  80: '20rem',      // 320px
  96: '24rem',      // 384px
} as const;

// ═══════════════════════════════════════════════════════════════
// SHADOW SYSTEM
// ═══════════════════════════════════════════════════════════════

export const shadows = {
  // Subtle shadows for depth
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.4)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.6)',

  // Luxury gold glow
  gold: {
    sm: '0 0 10px 0 rgba(212, 175, 55, 0.15)',
    md: '0 0 20px 0 rgba(212, 175, 55, 0.20)',
    lg: '0 0 30px 0 rgba(212, 175, 55, 0.25)',
    xl: '0 0 40px 0 rgba(212, 175, 55, 0.30)',
  },

  // Glass shadows
  glass: '0 8px 32px 0 rgba(0, 0, 0, 0.4), inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
  glassHover: '0 12px 40px 0 rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',

  // Elevation shadows
  elevated: '0 4px 20px 0 rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05)',
  elevatedHover: '0 8px 30px 0 rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.08)',

  // Inner shadows
  inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.3)',
  innerGold: 'inset 0 0 20px 0 rgba(212, 175, 55, 0.1)',
} as const;

// ═══════════════════════════════════════════════════════════════
// BORDER RADIUS SYSTEM
// ═══════════════════════════════════════════════════════════════

export const borderRadius = {
  none: '0',
  sm: '0.25rem',    // 4px
  md: '0.375rem',   // 6px
  lg: '0.5rem',     // 8px
  xl: '0.75rem',    // 12px
  '2xl': '1rem',    // 16px
  '3xl': '1.5rem',  // 24px
  '4xl': '2rem',    // 32px
  full: '9999px',
} as const;

// ═══════════════════════════════════════════════════════════════
// ANIMATION TIMING (Luxury Motion)
// ═══════════════════════════════════════════════════════════════

export const animation = {
  duration: {
    instant: '0ms',
    fast: '150ms',
    normal: '200ms',
    slow: '350ms',
    slower: '500ms',
    slowest: '700ms',
  },

  // Luxury cubic-bezier easing
  easing: {
    // Smooth, premium feel
    luxury: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    // Elegant entrance
    elegant: 'cubic-bezier(0.16, 1, 0.3, 1)',
    // Smooth exit
    smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
    // Bounce feel
    bounce: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    // Linear
    linear: 'linear',
  },
} as const;

// ═══════════════════════════════════════════════════════════════
// BREAKPOINTS
// ═══════════════════════════════════════════════════════════════

export const breakpoints = {
  xs: '320px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1400px',
  '3xl': '1600px',
} as const;

// ═══════════════════════════════════════════════════════════════
// Z-INDEX SCALE
// ═══════════════════════════════════════════════════════════════

export const zIndex = {
  hide: -1,
  base: 0,
  dropdown: 10,
  sticky: 20,
  fixed: 30,
  modalBackdrop: 40,
  modal: 50,
  popover: 60,
  tooltip: 70,
  toast: 80,
  max: 999,
} as const;

// ═══════════════════════════════════════════════════════════════
// GLASS EFFECT TOKENS
// ═══════════════════════════════════════════════════════════════

export const glass = {
  blur: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    '2xl': '24px',
  },
  background: {
    light: 'rgba(255, 255, 255, 0.05)',
    medium: 'rgba(255, 255, 255, 0.08)',
    heavy: 'rgba(255, 255, 255, 0.12)',
    dark: 'rgba(0, 0, 0, 0.4)',
  },
} as const;

// Export all tokens as a unified design system
export const designTokens = {
  colors,
  typography,
  spacing,
  shadows,
  borderRadius,
  animation,
  breakpoints,
  zIndex,
  glass,
} as const;

export type DesignTokens = typeof designTokens;
