import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { createTransition } from '@/motion';

interface SplashScreenProps {
  onComplete: () => void;
}

export function SplashScreen({ onComplete }: SplashScreenProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onComplete, 500); // Wait for exit animation
    }, 3000); // Show for 3 seconds

    return () => clearTimeout(timer);
  }, [onComplete]);

  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-primary/20 via-background to-accent/20"
    >
      <div className="text-center space-y-8">
        {/* Logo Animation */}
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={createTransition({
            type: "spring",
            stiffness: 260,
            damping: 20,
            delay: 0.2
          })}
          className="relative"
        >
          <motion.div
            animate={{
              scale: [1, 1.1, 1],
              rotate: [0, 5, -5, 0]
            }}
            transition={createTransition({
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            })}
            className="text-6xl font-bold text-primary"
          >
            CONFIT
          </motion.div>

          {/* Floating elements */}
          <motion.div
            animate={{
              y: [0, -10, 0],
              opacity: [0.5, 1, 0.5]
            }}
            transition={createTransition({
              duration: 3,
              repeat: Infinity,
              ease: "easeInOut"
            })}
            className="absolute -top-4 -left-8 text-2xl"
          >
            ✨
          </motion.div>
          <motion.div
            animate={{
              y: [0, -15, 0],
              opacity: [0.3, 0.8, 0.3]
            }}
            transition={createTransition({
              duration: 2.5,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.5
            })}
            className="absolute -top-6 -right-6 text-3xl"
          >
            🎨
          </motion.div>
          <motion.div
            animate={{
              y: [0, -8, 0],
              opacity: [0.4, 0.9, 0.4]
            }}
            transition={createTransition({
              duration: 2.8,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 1
            })}
            className="absolute -bottom-4 -left-4 text-2xl"
          >
            👗
          </motion.div>
        </motion.div>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ delay: 0.8, duration: 0.6 })}
          className="text-lg text-muted-foreground max-w-md mx-auto"
        >
          Your Personal Fashion Assistant
        </motion.p>

        {/* Loading dots */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={createTransition({ delay: 1.2 })}
          className="flex justify-center space-x-2"
        >
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={createTransition({
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.2,
                ease: "easeInOut"
              })}
              className="w-3 h-3 bg-primary rounded-full"
            />
          ))}
        </motion.div>

        {/* Progress bar */}
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: "200px" }}
          transition={createTransition({ delay: 0.5, duration: 2.5, ease: "easeInOut" })}
          className="h-1 bg-primary mx-auto rounded-full"
        />
      </div>
    </motion.div>
  );
}
