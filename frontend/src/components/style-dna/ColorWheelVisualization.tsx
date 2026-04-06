/**
 * Color Wheel Visualization Component
 * Displays user's color preferences in a wheel format
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

interface ColorWheelData {
  primary: string[];
  secondary: string[];
  avoided: string[];
  undertone: string | null;
  palette_type: string | null;
  recommended: string[];
}

interface ColorWheelVisualizationProps {
  data: ColorWheelData;
  compact?: boolean;
  className?: string;
}

const COLOR_BADGE_CLASSES: Record<string, string> = {
  black: 'bg-black text-white ring-black/30',
  white: 'bg-white text-black ring-black/20',
  gray: 'bg-gray-500 text-white ring-gray-500/30',
  navy: 'bg-slate-800 text-white ring-slate-800/30',
  blue: 'bg-blue-500 text-white ring-blue-500/30',
  red: 'bg-red-500 text-white ring-red-500/30',
  green: 'bg-green-500 text-white ring-green-500/30',
  yellow: 'bg-yellow-400 text-black ring-yellow-400/30',
  orange: 'bg-orange-500 text-white ring-orange-500/30',
  pink: 'bg-pink-500 text-white ring-pink-500/30',
  purple: 'bg-purple-500 text-white ring-purple-500/30',
  brown: 'bg-amber-900 text-white ring-amber-900/30',
  beige: 'bg-stone-200 text-black ring-stone-300/60',
  cream: 'bg-amber-50 text-black ring-amber-100/80',
  coral: 'bg-orange-400 text-white ring-orange-400/30',
  peach: 'bg-orange-200 text-black ring-orange-200/60',
  gold: 'bg-yellow-500 text-black ring-yellow-500/30',
  silver: 'bg-zinc-300 text-black ring-zinc-300/60',
  emerald: 'bg-emerald-500 text-white ring-emerald-500/30',
  lavender: 'bg-violet-200 text-black ring-violet-200/70',
  rose: 'bg-rose-500 text-white ring-rose-500/30',
  teal: 'bg-teal-500 text-white ring-teal-500/30',
  maroon: 'bg-red-900 text-white ring-red-900/30',
  olive: 'bg-lime-700 text-white ring-lime-700/30',
  tan: 'bg-amber-300 text-black ring-amber-300/60',
  khaki: 'bg-yellow-200 text-black ring-yellow-200/60',
  indigo: 'bg-indigo-700 text-white ring-indigo-700/30',
  magenta: 'bg-fuchsia-600 text-white ring-fuchsia-600/30',
  cyan: 'bg-cyan-400 text-black ring-cyan-400/30',
  turquoise: 'bg-cyan-500 text-white ring-cyan-500/30',
};

function getColorBadgeClass(colorName: string): string {
  return COLOR_BADGE_CLASSES[colorName.toLowerCase()] || 'bg-muted text-foreground ring-border';
}

export const ColorWheelVisualization: React.FC<ColorWheelVisualizationProps> = ({
  data,
  compact = false,
  className,
}) => {
  const { primary, secondary, undertone, recommended } = data;

  const allColors = [...primary, ...secondary].slice(0, 8);

  return (
    <div className={cn('relative', compact ? 'h-48' : 'h-80', className)}>
      {/* Color Wheel */}
      <div className="relative h-full flex items-center justify-center">
        {/* Outer ring - Primary colors */}
        <div
          className={cn(
            'absolute rounded-full border-2 border-border/50',
            compact ? 'w-36 h-36' : 'w-56 h-56'
          )}
        >
          {allColors.map((color, index) => {
            const angle = (index / allColors.length) * 360 - 90;
            const radian = (angle * Math.PI) / 180;
            const radius = compact ? 72 : 112;
            const x = Math.cos(radian) * radius;
            const y = Math.sin(radian) * radius;

            return (
              <motion.div
                key={color}
                initial={{ scale: 0, opacity: 0, x: 0, y: 0 }}
                animate={{ scale: 1, opacity: 1, x, y }}
                transition={createTransition({ delay: index * 0.05 })}
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
              >
                <div
                  className={cn(
                    'rounded-full ring-2 flex items-center justify-center font-medium shadow-lg',
                    compact ? 'w-8 h-8 text-xs' : 'w-12 h-12 text-sm'
                  , getColorBadgeClass(color)
                  )}
                >
                  {compact ? '' : color.slice(0, 3)}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Inner circle - Undertone indicator */}
        <div
          className={cn(
            'absolute rounded-full bg-card border border-border flex items-center justify-center',
            compact ? 'w-20 h-20' : 'w-32 h-32'
          )}
        >
          <div className="text-center">
            {undertone && !compact && (
              <>
                <p className="text-xs text-muted-foreground">Undertone</p>
                <p className="text-sm font-medium capitalize">{undertone}</p>
              </>
            )}
            {undertone && compact && (
              <p className="text-xs font-medium capitalize">{undertone}</p>
            )}
          </div>
        </div>

        {/* Center dot */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={createTransition({ delay: 0.3 })}
          className={cn(
            'absolute rounded-full bg-primary',
            compact ? 'w-3 h-3' : 'w-4 h-4'
          )}
        />
      </div>

      {/* Recommended colors (non-compact only) */}
      {!compact && recommended.length > 0 && (
        <div className="absolute bottom-0 left-0 right-0">
          <p className="text-xs text-muted-foreground mb-2">Recommended for you</p>
          <div className="flex flex-wrap gap-1">
            {recommended.slice(0, 5).map((color) => (
              <div
                key={color}
                className={cn('w-6 h-6 rounded-full border border-border', getColorBadgeClass(color))}
                title={color}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ColorWheelVisualization;
