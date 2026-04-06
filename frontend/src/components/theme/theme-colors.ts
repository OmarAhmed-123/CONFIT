// Theme color system for CONFIT luxury fashion brand

export const brandColors = {
  // Primary brand colors
  champagne: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b', // Primary champagne gold
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
  },
  charcoal: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a', // Primary charcoal
  },
  cream: {
    50: '#fefce8',
    100: '#fef9c3',
    200: '#fef08a',
    300: '#fde047',
    400: '#facc15',
    500: '#fef7ed', // Primary cream
    600: '#fef3e2',
    700: '#fce7c8',
    800: '#f9dba9',
    900: '#f5ca96',
  },
} as const;

export const semanticColors = {
  success: {
    light: '#10b981',
    dark: '#34d399',
  },
  warning: {
    light: '#f59e0b',
    dark: '#fbbf24',
  },
  error: {
    light: '#ef4444',
    dark: '#f87171',
  },
  info: {
    light: '#3b82f6',
    dark: '#60a5fa',
  },
} as const;

export const gradients = {
  gold: 'linear-gradient(135deg, #fbbf24 0%, #d97706 100%)',
  charcoal: 'linear-gradient(135deg, #334155 0%, #1e293b 100%)',
  cream: 'linear-gradient(135deg, #fef7ed 0%, #f9dba9 100%)',
  hero: 'linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(255, 255, 255, 1) 100%)',
  luxury: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)',
} as const;

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1)',
  gold: '0 4px 14px 0 rgb(212 175 55 / 0.3)',
  goldDark: '0 4px 14px 0 rgb(212 175 55 / 0.2)',
} as const;

// CSS Custom Properties for runtime theme switching
export const cssVariables = {
  light: {
    '--background': '0 0% 100%',
    '--foreground': '222.2 84% 4.9%',
    '--card': '0 0% 100%',
    '--card-foreground': '222.2 84% 4.9%',
    '--popover': '0 0% 100%',
    '--popover-foreground': '222.2 84% 4.9%',
    '--primary': '38 92% 50%',
    '--primary-foreground': '210 40% 98%',
    '--secondary': '210 40% 96.1%',
    '--secondary-foreground': '222.2 47.4% 11.2%',
    '--muted': '210 40% 96.1%',
    '--muted-foreground': '215.4 16.3% 46.9%',
    '--accent': '38 92% 50%',
    '--accent-foreground': '222.2 47.4% 11.2%',
    '--destructive': '0 84.2% 60.2%',
    '--destructive-foreground': '210 40% 98%',
    '--success': '142 76% 36%',
    '--success-foreground': '210 40% 98%',
    '--border': '214.3 31.8% 91.4%',
    '--input': '214.3 31.8% 91.4%',
    '--ring': '38 92% 50%',
    '--champagne': '38 92% 50%',
    '--charcoal': '0 0% 15%',
    '--cream': '40 30% 95%',
  },
  dark: {
    '--background': '222.2 84% 4.9%',
    '--foreground': '210 40% 98%',
    '--card': '222.2 84% 4.9%',
    '--card-foreground': '210 40% 98%',
    '--popover': '222.2 84% 4.9%',
    '--popover-foreground': '210 40% 98%',
    '--primary': '38 92% 50%',
    '--primary-foreground': '0 0% 0%',
    '--secondary': '217.2 32.6% 17.5%',
    '--secondary-foreground': '210 40% 98%',
    '--muted': '217.2 32.6% 17.5%',
    '--muted-foreground': '215 20.2% 65.1%',
    '--accent': '38 92% 50%',
    '--accent-foreground': '0 0% 0%',
    '--destructive': '0 62.8% 30.6%',
    '--destructive-foreground': '210 40% 98%',
    '--success': '142 76% 36%',
    '--success-foreground': '210 40% 98%',
    '--border': '217.2 32.6% 17.5%',
    '--input': '217.2 32.6% 17.5%',
    '--ring': '38 92% 50%',
    '--champagne': '38 92% 50%',
    '--charcoal': '0 0% 95%',
    '--cream': '40 30% 15%',
  },
} as const;

// Get contrasting text color
export function getContrastColor(bgColor: string): string {
  const hex = bgColor.replace('#', '');
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#0f172a' : '#fef7ed';
}

// Color palette for UI elements
export const uiPalette = {
  background: {
    light: '#ffffff',
    dark: '#0f172a',
  },
  surface: {
    light: '#ffffff',
    dark: '#1e293b',
  },
  text: {
    primary: {
      light: '#0f172a',
      dark: '#f8fafc',
    },
    secondary: {
      light: '#64748b',
      dark: '#94a3b8',
    },
    muted: {
      light: '#94a3b8',
      dark: '#64748b',
    },
  },
  border: {
    light: '#e2e8f0',
    dark: '#334155',
  },
} as const;
