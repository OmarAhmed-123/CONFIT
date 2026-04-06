/**
 * CONFIT Design System — Theme helpers
 * Provides semantic CSS variables (to be used by UI layers that opt-in).
 */

import { tokens } from "./tokens.js";

export const theme = {
  cssVariables: {
    "--confit-bg": tokens.colors.dark.background,
    "--confit-surface": tokens.colors.dark.surface,
    "--confit-surface-elevated": tokens.colors.dark.surfaceElevated,
    "--confit-border": tokens.colors.dark.border,
    "--confit-border-subtle": tokens.colors.dark.borderSubtle,
    "--confit-text": tokens.colors.dark.text,
    "--confit-text-muted": tokens.colors.dark.textMuted,

    "--confit-accent-gradient": tokens.colors.accent.gradient,
    "--confit-accent-gradient-strong": tokens.colors.accent.gradientStrong,

    "--confit-glow-purple": tokens.colors.glow.purple,
    "--confit-glow-blue": tokens.colors.glow.blue,
    "--confit-glow-cyan": tokens.colors.glow.cyan,

    "--confit-shadow-glass": tokens.shadows.glass,
    "--confit-shadow-glass-hover": tokens.shadows.glassHover,
    "--confit-shadow-elevate": tokens.shadows.elevate,
    "--confit-shadow-glow-purple": tokens.shadows.glowPurple,
    "--confit-shadow-glow-blue": tokens.shadows.glowBlue,
  },
};

