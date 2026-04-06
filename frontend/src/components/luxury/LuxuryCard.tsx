/**
 * LuxuryCard - Premium card component with dark luxury styling
 * Features: Glass effect, gold accents, smooth hover animations
 */

import { forwardRef, HTMLAttributes, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { luxuryCardVariants } from '@/motion/presets';

export interface LuxuryCardProps {
  variant?: 'default' | 'elevated' | 'glass' | 'gold';
  hover?: boolean;
  glow?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  className?: string;
  children?: ReactNode;
}

const paddingStyles = {
  none: 'p-0',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

const variantStyles = {
  default: `
    bg-[#151925] 
    border border-white/10 
    shadow-[0_4px_20px_0_rgba(0,0,0,0.4)]
  `,
  elevated: `
    bg-gradient-to-b from-[#1A1F2E] to-[#151925] 
    border border-white/[0.08] 
    shadow-[0_8px_30px_0_rgba(0,0,0,0.5)]
  `,
  glass: `
    bg-white/[0.03] 
    backdrop-blur-xl 
    border border-white/[0.06] 
    shadow-[0_8px_32px_0_rgba(0,0,0,0.4),inset_0_1px_0_0_rgba(255,255,255,0.05)]
  `,
  gold: `
    bg-gradient-to-b from-[#1A1F2E] to-[#151925] 
    border border-[#D4AF37]/30 
    shadow-[0_4px_20px_0_rgba(212,175,55,0.15)]
  `,
};

export const LuxuryCard: React.FC<LuxuryCardProps> = ({
  className,
  variant = 'default',
  hover = true,
  glow = false,
  padding = 'md',
  children,
}) => {
  return (
    <motion.div
      variants={hover ? luxuryCardVariants : undefined}
      initial="initial"
      whileHover={hover ? 'hover' : undefined}
      whileTap={hover ? 'tap' : undefined}
      className={cn(
        'rounded-2xl transition-colors duration-300',
        variantStyles[variant],
        paddingStyles[padding],
        glow && 'hover:shadow-[0_0_30px_0_rgba(212,175,55,0.25)]',
        className
      )}
    >
      {children}
    </motion.div>
  );
};

LuxuryCard.displayName = 'LuxuryCard';

// ═══════════════════════════════════════════════════════════════
// LUXURY CARD HEADER
// ═══════════════════════════════════════════════════════════════

export interface LuxuryCardHeaderProps extends HTMLAttributes<HTMLDivElement> {}

export const LuxuryCardHeader = forwardRef<HTMLDivElement, LuxuryCardHeaderProps>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('mb-4 pb-4 border-b border-white/10', className)}
      {...props}
    >
      {children}
    </div>
  )
);

LuxuryCardHeader.displayName = 'LuxuryCardHeader';

// ═══════════════════════════════════════════════════════════════
// LUXURY CARD TITLE
// ═══════════════════════════════════════════════════════════════

export interface LuxuryCardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

export const LuxuryCardTitle = forwardRef<HTMLHeadingElement, LuxuryCardTitleProps>(
  ({ className, as: Component = 'h3', children, ...props }, ref) => (
    <Component
      ref={ref}
      className={cn(
        'font-display text-xl font-semibold text-[#F5F5F5] tracking-tight',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  )
);

LuxuryCardTitle.displayName = 'LuxuryCardTitle';

// ═══════════════════════════════════════════════════════════════
// LUXURY CARD DESCRIPTION
// ═══════════════════════════════════════════════════════════════

export interface LuxuryCardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {}

export const LuxuryCardDescription = forwardRef<HTMLParagraphElement, LuxuryCardDescriptionProps>(
  ({ className, children, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-[#A0A3A8] leading-relaxed', className)}
      {...props}
    >
      {children}
    </p>
  )
);

LuxuryCardDescription.displayName = 'LuxuryCardDescription';

// ═══════════════════════════════════════════════════════════════
// LUXURY CARD CONTENT
// ═══════════════════════════════════════════════════════════════

export interface LuxuryCardContentProps extends HTMLAttributes<HTMLDivElement> {}

export const LuxuryCardContent = forwardRef<HTMLDivElement, LuxuryCardContentProps>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn('', className)} {...props}>
      {children}
    </div>
  )
);

LuxuryCardContent.displayName = 'LuxuryCardContent';

// ═══════════════════════════════════════════════════════════════
// LUXURY CARD FOOTER
// ═══════════════════════════════════════════════════════════════

export interface LuxuryCardFooterProps extends HTMLAttributes<HTMLDivElement> {}

export const LuxuryCardFooter = forwardRef<HTMLDivElement, LuxuryCardFooterProps>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('mt-4 pt-4 border-t border-white/10', className)}
      {...props}
    >
      {children}
    </div>
  )
);

LuxuryCardFooter.displayName = 'LuxuryCardFooter';

export default LuxuryCard;
