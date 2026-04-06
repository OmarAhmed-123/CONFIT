/**
 * Brand Universe Visualization Component
 * Displays brand affinities in a circular universe format
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

interface BrandUniverseData {
  brand_id: string;
  affinity_score: number;
  position: {
    angle: number;
    distance: number;
  };
}

interface BrandUniverseVisualizationProps {
  data: BrandUniverseData[];
  className?: string;
}

export const BrandUniverseVisualization: React.FC<BrandUniverseVisualizationProps> = ({
  data,
  className,
}) => {
  const orbitRingClasses = ['w-[30%] h-[30%]', 'w-[50%] h-[50%]', 'w-[70%] h-[70%]', 'w-[90%] h-[90%]'];

  const getPlanetSizeClass = (affinity: number) => {
    if (affinity >= 0.85) return 'w-14 h-14';
    if (affinity >= 0.7) return 'w-12 h-12';
    if (affinity >= 0.55) return 'w-10 h-10';
    return 'w-8 h-8';
  };

  if (!data || data.length === 0) {
    return (
      <div className={cn('h-64 flex items-center justify-center', className)}>
        <div className="text-center text-muted-foreground">
          <p>No brand preferences yet</p>
          <p className="text-sm mt-1">Shop and browse to discover your favorite brands</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('relative h-80', className)}>
      {/* Universe container */}
      <div className="relative h-full flex items-center justify-center">
        {/* Center - User */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute w-16 h-16 rounded-full bg-primary/20 border-2 border-primary flex items-center justify-center"
        >
          <span className="text-xs font-medium text-primary">You</span>
        </motion.div>

        {/* Orbit rings */}
        {orbitRingClasses.map((ringClass, index) => (
          <div
            key={index}
            className={cn('absolute rounded-full border border-border/30', ringClass)}
          />
        ))}

        {/* Brand planets */}
        {data.map((brand, index) => {
          const { angle, distance } = brand.position;
          const radian = (angle * Math.PI) / 180;
          const radius = distance * 120; // Max radius in pixels
          const x = Math.cos(radian) * radius;
          const y = Math.sin(radian) * radius;

          return (
            <motion.div
              key={brand.brand_id}
              initial={{ scale: 0, opacity: 0, x: 0, y: 0 }}
              animate={{ scale: 1, opacity: 1, x, y }}
              transition={createTransition({ delay: index * 0.1 })}
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
            >
              <div
                className={cn(
                  'rounded-full bg-card border border-border flex items-center justify-center shadow-lg',
                  getPlanetSizeClass(brand.affinity_score)
                )}
              >
                <div className="text-center">
                  <p className="text-xs font-medium truncate px-2">
                    {brand.brand_id.slice(0, 8)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {(brand.affinity_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}

        {/* Legend */}
        <div className="absolute bottom-0 left-0 right-0 flex justify-center gap-4 text-xs text-muted-foreground">
          <span>Closer = Higher Affinity</span>
          <span>•</span>
          <span>Larger = Stronger Match</span>
        </div>
      </div>
    </div>
  );
};

export default BrandUniverseVisualization;
