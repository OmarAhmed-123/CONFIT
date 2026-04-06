/**
 * GlassContainer - Dark glass morphism container
 * Premium frosted glass effect with subtle reflections
 */

import { forwardRef, HTMLAttributes, CSSProperties, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

export interface GlassContainerProps extends HTMLAttributes<HTMLDivElement> {
  blur?: 'sm' | 'md' | 'lg' | 'xl';
  opacity?: 'light' | 'medium' | 'heavy';
  border?: boolean;
  shine?: boolean;
}

const blurStyles = {
  sm: 'backdrop-blur-sm',
  md: 'backdrop-blur-md',
  lg: 'backdrop-blur-lg',
  xl: 'backdrop-blur-xl',
};

const opacityStyles = {
  light: 'bg-white/[0.02]',
  medium: 'bg-white/[0.04]',
  heavy: 'bg-white/[0.06]',
};

export const GlassContainer = forwardRef<HTMLDivElement, GlassContainerProps>(
  ({ 
    className, 
    blur = 'lg', 
    opacity = 'medium',
    border = true,
    shine = false,
    children, 
    ...props 
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'relative overflow-hidden rounded-2xl',
          blurStyles[blur],
          opacityStyles[opacity],
          border && 'border border-white/[0.06]',
          'shadow-[0_8px_32px_0_rgba(0,0,0,0.4),inset_0_1px_0_0_rgba(255,255,255,0.05)]',
          className
        )}
        {...props}
      >
        {/* Shine effect overlay */}
        {shine && (
          <div 
            className="absolute inset-0 pointer-events-none animate-shine-gradient"
          />
        )}
        {children}
      </div>
    );
  }
);

GlassContainer.displayName = 'GlassContainer';

// ═══════════════════════════════════════════════════════════════
// ANIMATED GLASS CONTAINER
// ═══════════════════════════════════════════════════════════════

export interface AnimatedGlassContainerProps {
  hover?: boolean;
  className?: string;
  children?: ReactNode;
}

export const AnimatedGlassContainer: React.FC<AnimatedGlassContainerProps> = ({
  className,
  hover = true,
  children,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={hover ? { 
        y: -2, 
        boxShadow: '0 12px 40px 0 rgba(0,0,0,0.5), inset 0 1px 0 0 rgba(255,255,255,0.08)' 
      } : undefined}
      transition={createTransition({ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] })}
      className={cn(
        'relative overflow-hidden rounded-2xl',
        'backdrop-blur-xl bg-white/[0.04]',
        'border border-white/[0.06]',
        'shadow-[0_8px_32px_0_rgba(0,0,0,0.4),inset_0_1px_0_0_rgba(255,255,255,0.05)]',
        className
      )}
    >
      {children}
    </motion.div>
  );
};

AnimatedGlassContainer.displayName = 'AnimatedGlassContainer';

// ═══════════════════════════════════════════════════════════════
// GLASS PANEL
// ═══════════════════════════════════════════════════════════════

export interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  intensity?: 'subtle' | 'normal' | 'strong';
}

export const GlassPanel = forwardRef<HTMLDivElement, GlassPanelProps>(
  ({ className, intensity = 'normal', children, ...props }, ref) => {
    const intensityStyles = {
      subtle: 'bg-black/20 backdrop-blur-md border-white/[0.04]',
      normal: 'bg-black/40 backdrop-blur-xl border-white/[0.06]',
      strong: 'bg-black/60 backdrop-blur-2xl border-white/[0.08]',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl border',
          intensityStyles[intensity],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

GlassPanel.displayName = 'GlassPanel';

export default GlassContainer;
