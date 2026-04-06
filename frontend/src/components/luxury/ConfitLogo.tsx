/**
 * ConfitLogo - Luxury CONFIT logo with gold crown
 * Premium brand identity component
 */

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Crown } from 'lucide-react';
import { createTransition } from '@/motion';

export interface ConfitLogoProps {
  variant?: 'full' | 'icon' | 'text';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  animated?: boolean;
  showGlow?: boolean;
  className?: string;
}

const sizeStyles = {
  sm: { icon: 'w-5 h-5', text: 'text-lg', gap: 'gap-1.5' },
  md: { icon: 'w-6 h-6', text: 'text-xl', gap: 'gap-2' },
  lg: { icon: 'w-8 h-8', text: 'text-2xl', gap: 'gap-2.5' },
  xl: { icon: 'w-10 h-10', text: 'text-3xl', gap: 'gap-3' },
};

export const ConfitLogo: React.FC<ConfitLogoProps> = ({
  variant = 'full',
  size = 'md',
  animated = true,
  showGlow = true,
  className,
}) => {
  const styles = sizeStyles[size];

  const LogoContent = (
    <div className={cn('flex items-center', styles.gap)}>
      {/* Crown Icon */}
      {(variant === 'full' || variant === 'icon') && (
        <div className="relative">
          <Crown 
            className={cn(
              styles.icon,
              'text-[#D4AF37]',
              animated && 'drop-shadow-[0_0_8px_rgba(212,175,55,0.4)]'
            )} 
          />
          {/* Glow effect */}
          {showGlow && (
            <div className="absolute inset-0 bg-[#D4AF37]/20 blur-lg rounded-full pointer-events-none" />
          )}
        </div>
      )}
      
      {/* Text */}
      {(variant === 'full' || variant === 'text') && (
        <span 
          className={cn(
            'font-display font-bold tracking-tight text-[#F5F5F5]',
            styles.text
          )}
        >
          CONFIT
        </span>
      )}
    </div>
  );

  if (animated) {
    return (
      <motion.div
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        transition={createTransition({ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] })}
        className={cn('cursor-pointer', className)}
      >
        {LogoContent}
      </motion.div>
    );
  }

  return <div className={className}>{LogoContent}</div>;
};

// ═══════════════════════════════════════════════════════════════
// LUXURY LOGO MARK (Icon only)
// ═══════════════════════════════════════════════════════════════

export interface LogoMarkProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LogoMark: React.FC<LogoMarkProps> = ({ size = 'md', className }) => {
  const sizeClass = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  }[size];

  return (
    <div 
      className={cn(
        'relative flex items-center justify-center rounded-xl',
        'bg-gradient-to-br from-[#D4AF37]/20 to-transparent',
        'border border-[#D4AF37]/30',
        sizeClass,
        className
      )}
    >
      <Crown className="w-1/2 h-1/2 text-[#D4AF37]" />
      <div className="absolute inset-0 bg-[#D4AF37]/10 blur-xl rounded-full" />
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// BRAND TAGLINE
// ═══════════════════════════════════════════════════════════════

export interface BrandTaglineProps {
  className?: string;
}

export const BrandTagline: React.FC<BrandTaglineProps> = ({ className }) => (
  <p className={cn('text-sm text-[#A0A3A8] tracking-widest uppercase', className)}>
    Confidence, Styled
  </p>
);

// ═══════════════════════════════════════════════════════════════
// LUXURY DIVIDER
// ═══════════════════════════════════════════════════════════════

export interface LuxuryDividerProps {
  className?: string;
}

export const LuxuryDivider: React.FC<LuxuryDividerProps> = ({ className }) => (
  <div className={cn('flex items-center gap-4', className)}>
    <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    <Crown className="w-4 h-4 text-[#D4AF37]/50" />
    <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
  </div>
);

export default ConfitLogo;
