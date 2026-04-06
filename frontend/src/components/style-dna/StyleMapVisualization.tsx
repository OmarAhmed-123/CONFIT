/**
 * Style Map Visualization Component
 * Interactive visualization showing user's position on style dimensions
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

interface StyleMapData {
  dimensions: [string, string][];
  position: { x: number; y: number };
  primary_style: string | null;
  secondary_styles: string[];
  confidence: number;
}

interface StyleMapVisualizationProps {
  data: StyleMapData;
  compact?: boolean;
  className?: string;
}

export const StyleMapVisualization: React.FC<StyleMapVisualizationProps> = ({
  data,
  compact = false,
  className,
}) => {
  const { dimensions, position, primary_style, confidence } = data;

  const quadrantClasses = [
    'bg-primary/5',
    'bg-accent/5',
    'bg-emerald-500/5',
    'bg-orange-500/5',
  ];

  return (
    <div className={cn('relative', compact ? 'h-48' : 'h-80', className)}>
      {/* Style Quadrants */}
      <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-1">
        {dimensions.slice(0, 4).map(([style1, style2], index) => (
          <div
            key={index}
            className={cn(
              'relative rounded-lg border border-border/50 flex items-center justify-center',
              'transition-colors hover:border-primary/30',
              quadrantClasses[index % quadrantClasses.length]
            )}
          >
            <div className="text-center p-2">
              <p className="text-xs font-medium capitalize">{style1}</p>
              <p className="text-xs text-muted-foreground">↔</p>
              <p className="text-xs font-medium capitalize">{style2}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Position Marker */}
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1, x: `${position.x * 50}%`, y: `${position.y * 50}%` }}
        transition={createTransition({ delay: 0.3, type: 'spring' })}
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
      >
        <div
          className={cn(
            'rounded-full bg-primary shadow-lg shadow-primary/30',
            compact ? 'w-4 h-4' : 'w-6 h-6'
          )}
        />
        {!compact && primary_style && (
          <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
            <span className="text-xs font-medium bg-background/90 px-2 py-1 rounded capitalize">
              {primary_style.replace('_', ' ')}
            </span>
          </div>
        )}
      </motion.div>

      {/* Confidence Ring */}
      {!compact && (
        <svg
          className="absolute inset-0 pointer-events-none"
          viewBox="0 0 100 100"
        >
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.5"
            className="text-border"
            strokeDasharray="4 2"
          />
          <motion.circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-primary"
            strokeLinecap="round"
            initial={{ strokeDasharray: '0 283' }}
            animate={{ strokeDasharray: `${confidence * 283} 283` }}
            transition={createTransition({ delay: 0.5, duration: 1 })}
          />
        </svg>
      )}

      {/* Legend */}
      {!compact && (
        <div className="absolute bottom-0 left-0 right-0 flex justify-center gap-2 text-xs text-muted-foreground">
          <span>Confidence: {(confidence * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
};

export default StyleMapVisualization;
