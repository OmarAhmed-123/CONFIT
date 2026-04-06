import React, { useCallback } from "react";

export function SpotlightBackground({
  className,
  defaultSpotX = "50%",
  defaultSpotY = "20%",
  children,
}: {
  className?: string;
  defaultSpotX?: string;
  defaultSpotY?: string;
  children: React.ReactNode;
}) {
  const onMove = useCallback((e: React.MouseEvent) => {
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    const x = rect.width ? ((e.clientX - rect.left) / rect.width) * 100 : 50;
    const y = rect.height ? ((e.clientY - rect.top) / rect.height) * 100 : 20;
    el.style.setProperty("--spot-x", `${x}%`);
    el.style.setProperty("--spot-y", `${y}%`);
  }, []);

  const onLeave = useCallback((e: React.MouseEvent) => {
    const el = e.currentTarget as HTMLElement;
    el.style.setProperty("--spot-x", defaultSpotX);
    el.style.setProperty("--spot-y", defaultSpotY);
  }, [defaultSpotX, defaultSpotY]);

  return (
    <div
      className={className}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={
        {
          ["--spot-x" as any]: defaultSpotX,
          ["--spot-y" as any]: defaultSpotY,
        } as React.CSSProperties
      }
    >
      {children}
    </div>
  );
}

