import React from "react";

/**
 * FloatingDecor — wraps children with GPU-friendly float animation.
 * Uses transform-only keyframes defined in `src/index.css` (`.animate-float`).
 */
export function FloatingDecor({
  className,
  delayMs = 0,
  children,
}: {
  className?: string;
  delayMs?: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className={["animate-float", className].filter(Boolean).join(" ")}
      style={{ animationDelay: `${delayMs}ms` }}
    >
      {children}
    </div>
  );
}

