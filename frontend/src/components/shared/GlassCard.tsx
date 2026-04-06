import React from "react";
import { GlowCard } from "@/components/ui/GlowCard";
import { cn } from "@/lib/utils";

type Props = {
  children: React.ReactNode;
  className?: string;
  glowIntensity?: string;
};

/**
 * GlassCard — shared frosted/glow surface.
 * Reuses existing `GlowCard` to avoid duplicating styles.
 */
export function GlassCard({ children, className, glowIntensity = "0.9" }: Props) {
  return <GlowCard className={cn(className)} glowIntensity={glowIntensity}>{children}</GlowCard>;
}

