import { motion } from 'framer-motion';
import { Camera, Shirt, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

const STEPS = [
  { key: 1 as const, label: 'Photo', icon: Camera },
  { key: 2 as const, label: 'Garment', icon: Shirt },
  { key: 3 as const, label: 'Preview', icon: Sparkles },
];

type Step = 1 | 2 | 3;

interface TryOnStepRailProps {
  step: Step;
}

export function TryOnStepRail({ step }: TryOnStepRailProps) {
  return (
    <div className="mb-8 md:mb-10">
      <div className="flex items-center justify-center gap-1 sm:gap-3">
        {STEPS.map(({ key, label, icon: Icon }, i) => {
          const active = step === key;
          const done = step > key;
          return (
            <div key={key} className="flex items-center">
              <div className="flex flex-col items-center gap-2">
                <motion.div
                  className={cn(
                    'flex h-11 w-11 items-center justify-center rounded-2xl border text-sm font-medium shadow-sm transition-colors md:h-12 md:w-12',
                    done && 'border-accent/50 bg-accent/15 text-accent',
                    active && !done && 'border-accent bg-accent/20 text-accent ring-2 ring-accent/30',
                    !active && !done && 'border-border bg-card/60 text-muted-foreground'
                  )}
                  animate={active ? { scale: [1, 1.04, 1] } : { scale: 1 }}
                  transition={{ duration: 2, repeat: active ? Infinity : 0, repeatDelay: 3 }}
                >
                  <Icon className="h-5 w-5" aria-hidden />
                </motion.div>
                <span
                  className={cn(
                    'text-[10px] font-medium uppercase tracking-[0.18em] md:text-xs',
                    active || done ? 'text-foreground' : 'text-muted-foreground'
                  )}
                >
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    'mx-1 h-px w-6 rounded-full sm:mx-4 sm:w-28',
                    step > STEPS[i].key ? 'bg-accent/50' : 'bg-border'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
