import React from "react";
import { StaggerContainer, StaggerItem } from "@/motion";

/**
 * StaggerGroup — convenience wrapper around `StaggerContainer`/`StaggerItem`.
 * Usage:
 * <StaggerGroup>
 *   <StaggerItem>...</StaggerItem>
 * </StaggerGroup>
 */
export function StaggerGroup({ children, ...props }) {
  return (
    <StaggerContainer {...props}>
      {children}
    </StaggerContainer>
  );
}

export { StaggerItem };

