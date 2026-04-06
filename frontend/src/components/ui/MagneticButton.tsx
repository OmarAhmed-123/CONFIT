import React, { useCallback, useRef } from "react";
import { cn } from "@/lib/utils";

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function MagneticButton({
  children,
  className,
  strength = 10,
  maxTranslate = 12,
  glow = true,
}: {
  children: React.ReactNode;
  className?: string;
  strength?: number;
  maxTranslate?: number;
  glow?: boolean;
}) {
  const wrapRef = useRef<HTMLSpanElement | null>(null);
  const rafRef = useRef<number | null>(null);

  const reset = useCallback(() => {
    if (!wrapRef.current) return;
    wrapRef.current.style.transition = "transform 220ms cubic-bezier(0.25, 0.46, 0.45, 0.94)";
    wrapRef.current.style.transform = "translate3d(0,0,0)";
    if (glow) {
      wrapRef.current.style.setProperty("--mag-x", "50%");
      wrapRef.current.style.setProperty("--mag-y", "50%");
      wrapRef.current.style.setProperty("--mag-a", "0");
    }
  }, [glow]);

  const onMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!wrapRef.current) return;
      const node = wrapRef.current;
      const rect = node.getBoundingClientRect();

      const relX = (e.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
      const relY = (e.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);

      const nx = clamp(relX, -1, 1);
      const ny = clamp(relY, -1, 1);

      const tx = clamp(nx * strength, -maxTranslate, maxTranslate);
      const ty = clamp(ny * strength, -maxTranslate, maxTranslate);

      const magX = `${clamp((e.clientX - rect.left) / rect.width, 0, 1) * 100}%`;
      const magY = `${clamp((e.clientY - rect.top) / rect.height, 0, 1) * 100}%`;
      const a = `${(Math.abs(nx) + Math.abs(ny)) / 2}`;

      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        node.style.transition = "transform 0ms";
        node.style.transform = `translate3d(${tx}px, ${ty}px, 0)`;
        if (glow) {
          node.style.setProperty("--mag-x", magX);
          node.style.setProperty("--mag-y", magY);
          node.style.setProperty("--mag-a", a);
        }
      });
    },
    [glow, maxTranslate, strength]
  );

  return (
    <span
      ref={wrapRef}
      className={cn(
        "relative inline-flex will-change-transform",
        glow && "group",
        className
      )}
      style={
        glow
          ? ({
              ["--mag-x" as any]: "50%",
              ["--mag-y" as any]: "50%",
              ["--mag-a" as any]: "0",
            } as React.CSSProperties)
          : undefined
      }
      onMouseMove={onMouseMove}
      onMouseLeave={reset}
      onFocus={reset}
    >
      {glow && (
        <span
          aria-hidden
          className="pointer-events-none absolute -inset-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
          style={{
            backgroundImage:
              "radial-gradient(circle at var(--mag-x) var(--mag-y), rgba(139,92,246,0.22), rgba(59,130,246,0.10) 28%, transparent 62%)",
            filter: "blur(8px)",
            opacity: "var(--mag-a)",
          }}
        />
      )}
      <span className="relative">{children}</span>
    </span>
  );
}

