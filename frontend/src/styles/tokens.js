export const tokens = {
  typography: {
    fontFamily: "Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
    scale: {
      h1: "clamp(2rem, 4vw, 3.25rem)",
      h2: "clamp(1.5rem, 2.8vw, 2.25rem)",
      h3: "clamp(1.25rem, 2.2vw, 1.75rem)",
      body: "1rem",
      caption: "0.8125rem",
    },
  },
  spacing: {
    base: 8,
    xs: "0.5rem",
    sm: "0.75rem",
    md: "1rem",
    lg: "1.5rem",
    xl: "2rem",
    "2xl": "3rem",
  },
  radius: {
    sm: "0.5rem",
    md: "0.75rem",
    lg: "1rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
  },
  colors: {
    // Neutral base (CSS variables already drive the active theme)
    neutral: {
      black: "hsl(0 0% 0%)",
      white: "hsl(0 0% 100%)",
      gray: "hsl(220 15% 14%)",
    },
    // Luxury gradient primary: purple -> blue
    gradientPrimary: "linear-gradient(135deg, hsl(260 85% 66% / 1), hsl(210 95% 60% / 1))",
    // Semantic colors (align with existing CSS vars)
    semantic: {
      success: "hsl(var(--success))",
      error: "hsl(var(--destructive))",
      warning: "hsl(38 92% 50% / 1)",
    },
    // App semantic surfaces/ink
    surface: {
      background: "hsl(var(--background))",
      foreground: "hsl(var(--foreground))",
      card: "hsl(var(--card))",
      muted: "hsl(var(--muted))",
      border: "hsl(var(--border))",
    },
    accent: {
      primary: "hsl(var(--primary))",
      accent: "hsl(var(--accent))",
    },
  },
  shadows: {
    soft: "0 8px 24px rgba(0, 0, 0, 0.16)",
    elevated: "0 18px 46px rgba(0, 0, 0, 0.24)",
    glow: "0 0 0 1px rgba(255,255,255,0.06), 0 10px 40px rgba(139,92,246,0.28)",
  },
  motion: {
    durationFast: 200,
    durationBase: 300,
    durationSlow: 400,
    easing: "cubic-bezier(0.4, 0, 0.2, 1)",
  },
};

export default tokens;

