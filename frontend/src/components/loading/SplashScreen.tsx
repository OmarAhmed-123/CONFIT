'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface SplashScreenProps {
  isVisible: boolean;
  message?: string;
  progress?: number;
  variant?: 'startup' | 'auth' | 'dashboard' | 'payment' | 'tryon' | 'route';
  onComplete?: () => void;
  minDuration?: number;
}

const VARIANT_CONFIG = {
  startup: { message: 'Launching CONFIT', minDuration: 900 },
  auth: { message: 'Securing your session', minDuration: 700 },
  dashboard: { message: 'Preparing your workspace', minDuration: 700 },
  payment: { message: 'Initializing secure payment', minDuration: 700 },
  tryon: { message: 'Loading virtual studio', minDuration: 900 },
  route: { message: 'Loading', minDuration: 300 },
} as const;

export function SplashScreen({
  isVisible,
  message,
  progress,
  variant = 'startup',
  onComplete,
  minDuration,
}: SplashScreenProps) {
  const [internalVisible, setInternalVisible] = useState(isVisible);
  const [hasRendered, setHasRendered] = useState(false);
  const config = VARIANT_CONFIG[variant];
  const displayMessage = message ?? config.message;
  const displayMinDuration = minDuration ?? config.minDuration;

  useEffect(() => {
    if (isVisible) {
      setInternalVisible(true);
      setHasRendered(true);
    } else if (hasRendered) {
      const timer = setTimeout(() => setInternalVisible(false), 250);
      return () => clearTimeout(timer);
    }
  }, [isVisible, hasRendered]);

  useEffect(() => {
    if (!isVisible && hasRendered) {
      const timer = setTimeout(() => onComplete?.(), displayMinDuration);
      return () => clearTimeout(timer);
    }
  }, [isVisible, hasRendered, onComplete, displayMinDuration]);

  return (
    <AnimatePresence>
      {internalVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#0a0e1a]"
          style={{
            background:
              'radial-gradient(ellipse at 50% 0%, rgba(212,175,55,0.08) 0%, transparent 50%), linear-gradient(180deg, #0a0e1a 0%, #0f1525 100%)',
          }}
        >
          {/* Ambient glow behind logo */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <motion.div
              animate={{
                opacity: [0.3, 0.6, 0.3],
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full"
              style={{
                background: 'radial-gradient(circle, rgba(212,175,55,0.15) 0%, transparent 70%)',
              }}
            />
          </div>

          {/* Logo and brand */}
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="relative flex flex-col items-center"
          >
            {/* CONFIT Logo mark */}
            <div className="relative mb-8">
              <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
                className="relative"
              >
                <svg
                  width="72"
                  height="72"
                  viewBox="0 0 72 72"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  className="drop-shadow-[0_0_30px_rgba(212,175,55,0.4)]"
                >
                  <motion.circle
                    cx="36"
                    cy="36"
                    r="32"
                    stroke="rgba(212,175,55,0.3)"
                    strokeWidth="1"
                    fill="none"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 2, ease: 'easeInOut', delay: 0.3 }}
                  />
                  <motion.path
                    d="M24 28C24 28 28 20 36 20C44 20 48 28 48 28"
                    stroke="rgba(212,175,55,0.9)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    fill="none"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1.2, ease: 'easeInOut', delay: 0.5 }}
                  />
                  <motion.path
                    d="M20 36C20 36 20 48 36 52C52 48 52 36 52 36"
                    stroke="rgba(212,175,55,0.9)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    fill="none"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1.2, ease: 'easeInOut', delay: 0.7 }}
                  />
                  <motion.circle
                    cx="36"
                    cy="36"
                    r="4"
                    fill="rgba(212,175,55,0.9)"
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.6, ease: 'easeOut', delay: 1.2 }}
                  />
                </svg>
              </motion.div>
            </div>

            {/* Brand name */}
            <motion.h1
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="text-3xl font-display font-semibold tracking-[0.2em] text-white mb-3"
            >
              CONFIT
            </motion.h1>

            {/* Tagline */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.9 }}
              className="text-sm tracking-[0.3em] uppercase text-[rgba(212,175,55,0.7)] mb-12"
            >
              Personal Fashion Platform
            </motion.p>
          </motion.div>

          {/* Loading state */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.0 }}
            className="flex flex-col items-center gap-4"
          >
            {/* Progress bar */}
            <div className="w-48 h-[2px] bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{
                  background: 'linear-gradient(90deg, rgba(212,175,55,0.8), rgba(212,175,55,0.4))',
                }}
                initial={{ width: '0%' }}
                animate={{
                  width: progress !== undefined ? `${progress}%` : ['0%', '40%', '70%', '90%'],
                }}
                transition={
                  progress !== undefined
                    ? { duration: 0.4, ease: 'easeOut' }
                    : {
                        duration: 2.5,
                        times: [0, 0.4, 0.7, 1],
                        ease: 'easeInOut',
                        repeat: progress === undefined ? Infinity : 0,
                      }
                }
              />
            </div>

            {/* Message */}
            <motion.p
              key={displayMessage}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-xs tracking-[0.15em] uppercase text-white/40"
            >
              {displayMessage}
            </motion.p>
          </motion.div>

          {/* Bottom shimmer line */}
          <motion.div
            className="absolute bottom-0 left-0 right-0 h-[1px]"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.3), transparent)',
            }}
            animate={{
              backgroundPosition: ['-200% 0', '200% 0'],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default SplashScreen;
