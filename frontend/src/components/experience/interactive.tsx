import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { ScrollReveal as MotionScrollReveal, useReducedMotion } from "@/motion";

type BaseProps = {
  children: React.ReactNode;
  className?: string;
};

export function InteractiveCard({ children, className }: BaseProps) {
  const prefersReducedMotion = useReducedMotion();
  return (
    <motion.div
      whileHover={prefersReducedMotion ? undefined : { y: -4, scale: 1.04 }}
      whileTap={prefersReducedMotion ? undefined : { scale: 0.97 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-border/70 bg-card/80 transition-shadow",
        "shadow-lg hover:shadow-2xl will-change-transform",
        className
      )}
    >
      <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 bg-gradient-to-br from-accent/10 via-transparent to-primary/10" />
      {children}
    </motion.div>
  );
}

type HoverRevealCardProps = BaseProps & {
  reveal: React.ReactNode;
};

export function HoverRevealCard({ children, reveal, className }: HoverRevealCardProps) {
  return (
    <InteractiveCard className={cn("min-h-full", className)}>
      {children}
      <div className="pointer-events-none absolute inset-0 translate-y-2 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100">
        {reveal}
      </div>
    </InteractiveCard>
  );
}

export function TiltCard({ children, className }: BaseProps) {
  const prefersReducedMotion = useReducedMotion();
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const canTilt = useMemo(() => !prefersReducedMotion, [prefersReducedMotion]);

  return (
    <motion.div
      onMouseMove={(e) => {
        if (!canTilt) return;
        const rect = e.currentTarget.getBoundingClientRect();
        const px = (e.clientX - rect.left) / rect.width;
        const py = (e.clientY - rect.top) / rect.height;
        const rotY = (px - 0.5) * 6;
        const rotX = (0.5 - py) * 6;
        setTilt({ x: rotX, y: rotY });
      }}
      onMouseLeave={() => setTilt({ x: 0, y: 0 })}
      animate={canTilt ? { rotateX: tilt.x, rotateY: tilt.y, y: -2 } : undefined}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      style={{ transformStyle: "preserve-3d" }}
      className={cn("will-change-transform", className)}
    >
      {children}
    </motion.div>
  );
}

type AnimatedSectionProps = BaseProps & {
  title?: string;
  subtitle?: string;
};

export function AnimatedSection({ children, className, title, subtitle }: AnimatedSectionProps) {
  return (
    <section className={cn("space-y-5", className)}>
      {(title || subtitle) && (
        <div className="space-y-2">
          {title ? <h2 className="text-2xl md:text-3xl font-semibold tracking-tight">{title}</h2> : null}
          {subtitle ? <p className="text-muted-foreground">{subtitle}</p> : null}
        </div>
      )}
      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.15 }}
        variants={{
          hidden: {},
          visible: {
            transition: {
              staggerChildren: 0.08,
              delayChildren: 0.04,
            },
          },
        }}
      >
        {children}
      </motion.div>
    </section>
  );
}

export function ScrollReveal({ children, className }: BaseProps) {
  return (
    <MotionScrollReveal className={className} once amount={0.15}>
      {children}
    </MotionScrollReveal>
  );
}

