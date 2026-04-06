import React from "react";
import { cn } from "@/lib/utils";

export function GlowCard({
  children,
  className,
  glowIntensity = "0.9",
}: {
  children: React.ReactNode;
  className?: string;
  glowIntensity?: string;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-card/20 backdrop-blur-md",
        className
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(1200px circle at 18% 10%, rgba(139,92,246,0.25), transparent 52%), radial-gradient(800px circle at 85% 25%, rgba(59,130,246,0.18), transparent 50%)",
          opacity: glowIntensity,
        }}
      />
      <span
        aria-hidden
        className="pointer-events-none absolute -inset-px bg-[linear-gradient(135deg,rgba(139,92,246,0.35),rgba(59,130,246,0.25),rgba(236,72,153,0.15))] opacity-[0.12] blur-[18px]"
      />
      <div className="relative">{children}</div>
    </div>
  );
}

