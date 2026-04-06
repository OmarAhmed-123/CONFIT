/**
 * CONFIT Design System — Tokens (single source intent)
 * Root-level `design-system/*` folder as requested for cross-layer reuse.
 */

export const tokens = {
  colors: {
    dark: {
      background: "#060810",
      surface: "#0F1524",
      surfaceElevated: "#151B2E",
      border: "rgba(255,255,255,0.10)",
      borderSubtle: "rgba(255,255,255,0.06)",
      text: "#F5F7FF",
      textMuted: "rgba(245,247,255,0.70)",
    },
    accent: {
      // Purple -> Blue luxury gradient
      gradient: "linear-gradient(135deg, rgba(139,92,246,0.22) 0%, rgba(59,130,246,0.14) 55%, rgba(6,182,212,0.10) 100%)",
      gradientStrong: "linear-gradient(135deg, rgba(139,92,246,0.55) 0%, rgba(59,130,246,0.38) 55%, rgba(6,182,212,0.25) 100%)",
    },
    semantic: {
      success: "#22C55E",
      warning: "#FBBF24",
      error: "#F87171",
      info: "#38BDF8",
    },
    glow: {
      purple: "rgba(139,92,246,0.45)",
      blue: "rgba(59,130,246,0.35)",
      cyan: "rgba(6,182,212,0.22)",
    },
  },
  typography: {
    fontFamily: {
      display: `"Playfair Display", Georgia, serif`,
      body: `Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif`,
      mono: `"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace`,
    },
    scale: {
      h1: { size: 56, lineHeight: 60, letterSpacing: "-0.04em" },
      h2: { size: 40, lineHeight: 44, letterSpacing: "-0.03em" },
      h3: { size: 28, lineHeight: 34, letterSpacing: "-0.02em" },
      body: { size: 16, lineHeight: 24, letterSpacing: "0em" },
      "bodySm": { size: 14, lineHeight: 20, letterSpacing: "0em" },
      caption: { size: 12, lineHeight: 18, letterSpacing: "0.02em" },
    },
  },
  spacing: {
    unit: 8,
    // Common steps (8px system)
    0: 0,
    1: 8,
    2: 16,
    3: 24,
    4: 32,
    5: 40,
    6: 48,
    7: 56,
    8: 64,
  },
  radius: {
    sm: 8,
    md: 12,
    lg: 20,
    xl: 28,
    "2xl": 36,
    full: 9999,
  },
  shadows: {
    glass: "0 12px 48px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.06)",
    glassHover: "0 16px 60px rgba(0,0,0,0.65), inset 0 1px 0 rgba(255,255,255,0.10)",
    elevate: "0 12px 30px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.07)",
    glowPurple: "0 0 22px rgba(139,92,246,0.35), 0 0 60px rgba(139,92,246,0.14)",
    glowBlue: "0 0 18px rgba(59,130,246,0.30), 0 0 55px rgba(59,130,246,0.12)",
  },
};

export const designTokens = tokens;

