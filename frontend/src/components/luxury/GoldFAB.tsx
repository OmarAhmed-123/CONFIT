/**
 * GoldFAB - Luxury Gold Floating Action Button
 * Premium FAB with gold gradient and glow effects
 */

import { forwardRef, ButtonHTMLAttributes, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { fabVariants } from '@/motion/presets';
import { createTransition } from '@/motion';

export interface GoldFABProps {
  size?: 'sm' | 'md' | 'lg';
  icon?: ReactNode;
  label?: string;
  position?: 'bottom-right' | 'bottom-left' | 'bottom-center';
  glow?: boolean;
  className?: string;
  children?: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
}

const sizeStyles = {
  sm: 'w-12 h-12 text-sm',
  md: 'w-14 h-14 text-base',
  lg: 'w-16 h-16 text-lg',
};

const positionStyles = {
  'bottom-right': 'bottom-6 right-6',
  'bottom-left': 'bottom-6 left-6',
  'bottom-center': 'bottom-6 left-1/2 -translate-x-1/2',
};

export const GoldFAB: React.FC<GoldFABProps> = ({
  className,
  size = 'md',
  icon,
  label,
  position = 'bottom-right',
  glow = true,
  children,
  disabled,
  onClick,
}) => {
  return (
    <motion.button
      variants={fabVariants}
      initial="initial"
      animate="animate"
      whileHover="hover"
      whileTap="tap"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'fixed z-50',
        'flex items-center justify-center',
        'rounded-full',
        'bg-gradient-to-br from-[#D4AF37] via-[#E8C776] to-[#B8942D]',
        'text-[#0B0F1A] font-semibold',
        'shadow-[0_4px_20px_0_rgba(212,175,55,0.3)]',
        'transition-all duration-300',
        'focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/50 focus:ring-offset-2 focus:ring-offset-[#0B0F1A]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        positionStyles[position],
        sizeStyles[size],
        glow && 'hover:shadow-[0_0_30px_0_rgba(212,175,55,0.4)]',
        className
      )}
    >
      {/* Shimmer effect */}
      <span
        className="absolute inset-0 rounded-full overflow-hidden animate-shimmer-gradient"
      />
      
      {/* Content */}
      <span className="relative z-10 flex items-center gap-2">
        {icon}
        {label && <span className="hidden sm:inline">{label}</span>}
        {children}
      </span>
    </motion.button>
  );
};

GoldFAB.displayName = 'GoldFAB';

// ═══════════════════════════════════════════════════════════════
// GOLD BUTTON (Non-floating variant)
// ═══════════════════════════════════════════════════════════════

export interface GoldButtonProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'solid' | 'outline' | 'ghost';
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
  className?: string;
  children?: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

const buttonSizeStyles = {
  sm: 'px-4 py-2 text-sm gap-1.5',
  md: 'px-6 py-3 text-base gap-2',
  lg: 'px-8 py-4 text-lg gap-2.5',
};

const buttonVariantStyles = {
  solid: `
    bg-gradient-to-br from-[#D4AF37] via-[#E8C776] to-[#B8942D]
    text-[#0B0F1A]
    shadow-[0_4px_20px_0_rgba(212,175,55,0.3)]
    hover:shadow-[0_0_30px_0_rgba(212,175,55,0.4)]
  `,
  outline: `
    bg-transparent
    border-2 border-[#D4AF37]
    text-[#D4AF37]
    hover:bg-[#D4AF37]/10
    hover:shadow-[0_0_20px_0_rgba(212,175,55,0.2)]
  `,
  ghost: `
    bg-transparent
    text-[#D4AF37]
    hover:bg-[#D4AF37]/10
    hover:shadow-[0_0_15px_0_rgba(212,175,55,0.15)]
  `,
};

export const GoldButton: React.FC<GoldButtonProps> = ({
  className,
  size = 'md',
  variant = 'solid',
  icon,
  iconPosition = 'left',
  children,
  disabled,
  onClick,
  type = 'button',
}) => {
  return (
    <motion.button
      type={type}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={createTransition({ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] })}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'relative inline-flex items-center justify-center',
        'rounded-xl font-semibold',
        'transition-all duration-300',
        'focus:outline-none focus:ring-2 focus:ring-[#D4AF37]/50 focus:ring-offset-2 focus:ring-offset-[#0B0F1A]',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
        buttonSizeStyles[size],
        buttonVariantStyles[variant],
        className
      )}
    >
      {variant === 'solid' && (
        <span
          className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none animate-shimmer-gradient"
        />
      )}
      
      <span className="relative z-10 flex items-center gap-2">
        {icon && iconPosition === 'left' && icon}
        {children}
        {icon && iconPosition === 'right' && icon}
      </span>
    </motion.button>
  );
};

GoldButton.displayName = 'GoldButton';

export default GoldFAB;
