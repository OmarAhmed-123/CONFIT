/**
 * GarmentCrossfade — Intelligent crossfade for try-on garment switching.
 * Maintains body position, animates fabric appearance smoothly.
 * No flicker — uses AnimatePresence mode="wait".
 */

import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { crossfadeVariants } from '../presets';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { DURATION_LUXURY } from '../motionTokens';
import { EASE_SOFT } from '../easing';

interface GarmentCrossfadeProps {
  /** Unique key for current garment — triggers crossfade on change */
  garmentKey: string;
  children: React.ReactNode;
  className?: string;
}

export const GarmentCrossfade: React.FC<GarmentCrossfadeProps> = ({
  garmentKey,
  children,
  className,
}) => {
  const prefersReduced = useReducedMotion();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={garmentKey}
        variants={crossfadeVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={
          prefersReduced
            ? { duration: 0.1 }
            : { duration: DURATION_LUXURY, ease: EASE_SOFT }
        }
        className={className}
        style={{ willChange: 'opacity, transform' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};

GarmentCrossfade.displayName = 'GarmentCrossfade';
