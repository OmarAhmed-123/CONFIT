import React from "react";
import { motion } from "framer-motion";
import { useReducedMotion } from "@/motion";

/**
 * MotionWrapper — a small accessibility-first bridge.
 * When `prefers-reduced-motion` is enabled, we render without motion props.
 */
export function MotionWrapper({
  as: As = motion.div,
  className,
  children,
  initial,
  animate,
  exit,
  transition,
  whileInView,
  viewport,
  ...rest
}) {
  const prefersReduced = useReducedMotion();

  if (prefersReduced) {
    return (
      <div className={className} {...rest}>
        {children}
      </div>
    );
  }

  return (
    <As
      className={className}
      initial={initial}
      animate={animate}
      exit={exit}
      transition={transition}
      whileInView={whileInView}
      viewport={viewport}
      {...rest}
    >
      {children}
    </As>
  );
}

