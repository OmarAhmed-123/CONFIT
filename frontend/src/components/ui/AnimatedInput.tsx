import React from "react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export function AnimatedInput({
  className,
  ...props
}: React.ComponentProps<typeof Input>) {
  return (
    <div
      className={cn(
        "relative rounded-2xl",
        "focus-within:ring-1 focus-within:ring-accent/40",
        className
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition-opacity duration-200"
        style={{
          backgroundImage:
            "linear-gradient(135deg, rgba(139,92,246,0.45), rgba(59,130,246,0.35), rgba(236,72,153,0.20))",
          filter: "blur(10px)",
        }}
      />
      <Input
        {...props}
        className={cn(
          "relative z-10 rounded-2xl bg-background/60 border-white/10",
          "focus-visible:ring-accent/50 focus-visible:border-accent/50",
          "transition-colors duration-200",
          props.className
        )}
      />
    </div>
  );
}

