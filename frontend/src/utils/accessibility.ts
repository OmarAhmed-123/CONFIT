/**
 * CONFIT — Accessibility Utilities
 * WCAG 2.1 Level AA compliant utilities for Lighthouse 95+ accessibility score
 */

import { useEffect, useRef, useCallback, useState } from 'react';

// ── Focus Management ────────────────────────────────────────────────

/**
 * Hook to trap focus within a container (for modals, dialogs)
 */
export function useFocusTrap<T extends HTMLElement>(active: boolean) {
  const containerRef = useRef<T>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!active || !containerRef.current) return;

    // Store the previously focused element
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Focus the first focusable element
    const focusableElements = getFocusableElements(containerRef.current);
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || !containerRef.current) return;

      const focusable = getFocusableElements(containerRef.current);
      if (focusable.length === 0) return;

      const firstElement = focusable[0];
      const lastElement = focusable[focusable.length - 1];

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus when trap is deactivated
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [active]);

  return containerRef;
}

/**
 * Get all focusable elements within a container
 */
export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const selector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  return Array.from(container.querySelectorAll<HTMLElement>(selector))
    .filter(el => el.offsetParent !== null) // Filter out hidden elements
    .filter(el => !el.hasAttribute('aria-hidden'));
}

/**
 * Hook to manage focus restoration
 */
export function useFocusRestore<T extends HTMLElement>(trigger: boolean) {
  const elementRef = useRef<T>(null);

  useEffect(() => {
    if (trigger && elementRef.current) {
      elementRef.current.focus();
    }
  }, [trigger]);

  return elementRef;
}

// ── Skip Links ──────────────────────────────────────────────────────

/**
 * Skip link component props
 */
export interface SkipLinkProps {
  targetId: string;
  label: string;
}

/**
 * Create skip link for keyboard navigation
 */
export function createSkipLink({ targetId, label }: SkipLinkProps) {
  const handleSkip = () => {
    const target = document.getElementById(targetId);
    if (target) {
      target.tabIndex = -1;
      target.focus();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return { onClick: handleSkip, href: `#${targetId}` };
}

// ── Keyboard Navigation ─────────────────────────────────────────────

/**
 * Hook for arrow key navigation in lists
 */
export function useArrowNavigation<T extends HTMLElement>(
  items: HTMLElement[],
  orientation: 'horizontal' | 'vertical' = 'vertical',
  loop: boolean = true
) {
  const containerRef = useRef<T>(null);
  const [currentIndex, setCurrentIndex] = useState(-1);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!items.length) return;

    const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight';
    const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft';

    let newIndex = currentIndex;

    if (e.key === nextKey) {
      e.preventDefault();
      newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : (loop ? 0 : currentIndex);
    } else if (e.key === prevKey) {
      e.preventDefault();
      newIndex = currentIndex > 0 ? currentIndex - 1 : (loop ? items.length - 1 : 0);
    } else if (e.key === 'Home') {
      e.preventDefault();
      newIndex = 0;
    } else if (e.key === 'End') {
      e.preventDefault();
      newIndex = items.length - 1;
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      items[currentIndex]?.click();
      return;
    }

    if (newIndex !== currentIndex) {
      setCurrentIndex(newIndex);
      items[newIndex]?.focus();
    }
  }, [items, currentIndex, orientation, loop]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return { containerRef, currentIndex, setCurrentIndex };
}

// ── Screen Reader Announcements ─────────────────────────────────────

/**
 * Announce message to screen readers
 */
export function announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
  const announcer = document.createElement('div');
  announcer.setAttribute('aria-live', priority);
  announcer.setAttribute('aria-atomic', 'true');
  announcer.setAttribute('class', 'sr-only');
  announcer.style.cssText = `
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  `;

  document.body.appendChild(announcer);

  // Delay to ensure screen reader catches the change
  setTimeout(() => {
    announcer.textContent = message;
    // Remove after announcement
    setTimeout(() => {
      document.body.removeChild(announcer);
    }, 1000);
  }, 100);
}

/**
 * Hook for screen reader announcements
 */
export function useAnnouncer() {
  return useCallback((message: string, priority?: 'polite' | 'assertive') => {
    announce(message, priority);
  }, []);
}

// ── Color Contrast ──────────────────────────────────────────────────

/**
 * Calculate relative luminance
 */
export function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors
 */
export function getContrastRatio(color1: { r: number; g: number; b: number }, color2: { r: number; g: number; b: number }): number {
  const L1 = getLuminance(color1.r, color1.g, color1.b);
  const L2 = getLuminance(color2.r, color2.g, color2.b);
  const lighter = Math.max(L1, L2);
  const darker = Math.min(L1, L2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast ratio meets WCAG AA
 */
export function meetsWCAGAA(ratio: number, isLargeText: boolean = false): boolean {
  return isLargeText ? ratio >= 3 : ratio >= 4.5;
}

// ── Reduced Motion ───────────────────────────────────────────────────

/**
 * Hook to detect user's motion preference
 */
export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return prefersReducedMotion;
}

// ── High Contrast Mode ───────────────────────────────────────────────

/**
 * Hook to detect high contrast mode
 */
export function useHighContrast(): boolean {
  const [isHighContrast, setIsHighContrast] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: high)');
    setIsHighContrast(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => {
      setIsHighContrast(e.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return isHighContrast;
}

// ── ARIA Utilities ───────────────────────────────────────────────────

/**
 * Generate unique ID for ARIA associations
 */
let idCounter = 0;
export function generateAriaId(prefix: string = 'aria'): string {
  return `${prefix}-${++idCounter}`;
}

/**
 * Create ARIA attributes for describedby
 */
export function ariaDescribedBy(ids: string | string[]) {
  const idList = Array.isArray(ids) ? ids.join(' ') : ids;
  return { 'aria-describedby': idList };
}

/**
 * Create ARIA attributes for labelledby
 */
export function ariaLabelledBy(ids: string | string[]) {
  const idList = Array.isArray(ids) ? ids.join(' ') : ids;
  return { 'aria-labelledby': idList };
}

/**
 * Create ARIA attributes for controls
 */
export function ariaControls(id: string) {
  return { 'aria-controls': id };
}

/**
 * Create ARIA attributes for expanded state
 */
export function ariaExpanded(expanded: boolean) {
  return { 'aria-expanded': expanded };
}

/**
 * Create ARIA attributes for hidden state
 */
export function ariaHidden(hidden: boolean) {
  return { 'aria-hidden': hidden };
}

/**
 * Create ARIA attributes for current state
 */
export function ariaCurrent(current: 'page' | 'step' | 'location' | 'date' | 'time' | 'true' | 'false' = 'true') {
  return { 'aria-current': current };
}

// ── Form Accessibility ──────────────────────────────────────────────

/**
 * Create accessible form field attributes
 */
export function createFieldAttributes(
  id: string,
  label: string,
  error?: string,
  description?: string
) {
  const describedBy: string[] = [];
  
  if (description) {
    describedBy.push(`${id}-description`);
  }
  
  if (error) {
    describedBy.push(`${id}-error`);
  }

  return {
    id,
    'aria-label': label,
    'aria-invalid': !!error,
    'aria-describedby': describedBy.length > 0 ? describedBy.join(' ') : undefined,
  };
}

/**
 * Create accessible error message attributes
 */
export function createErrorAttributes(id: string) {
  return {
    id: `${id}-error`,
    role: 'alert',
    'aria-live': 'polite' as const,
  };
}

// ── Button Accessibility ─────────────────────────────────────────────

/**
 * Create accessible button attributes for icon-only buttons
 */
export function createIconButtonAttributes(label: string) {
  return {
    'aria-label': label,
    title: label, // Tooltip for sighted users
  };
}

/**
 * Create accessible loading button attributes
 */
export function createLoadingButtonAttributes(isLoading: boolean, label: string) {
  return {
    'aria-busy': isLoading,
    'aria-disabled': isLoading,
    'aria-label': isLoading ? `${label}, loading` : label,
  };
}

// ── Modal/Dialog Accessibility ──────────────────────────────────────

/**
 * Create accessible modal attributes
 */
export function createModalAttributes(id: string, title: string) {
  return {
    role: 'dialog' as const,
    'aria-modal': true,
    'aria-labelledby': `${id}-title`,
    'aria-describedby': `${id}-description`,
  };
}

// ── Table Accessibility ──────────────────────────────────────────────

/**
 * Create accessible table header attributes
 */
export function createTableHeaderAttributes(sortable: boolean = false, sorted?: 'ascending' | 'descending') {
  if (!sortable) return {};

  return {
    'aria-sort': sorted || 'none',
    role: 'columnheader' as const,
  };
}

// ── Tab Panel Accessibility ──────────────────────────────────────────

/**
 * Create accessible tab attributes
 */
export function createTabAttributes(panelId: string, selected: boolean, index: number) {
  return {
    id: `tab-${index}`,
    role: 'tab' as const,
    'aria-selected': selected,
    'aria-controls': panelId,
    tabIndex: selected ? 0 : -1,
  };
}

/**
 * Create accessible tab panel attributes
 */
export function createTabPanelAttributes(tabId: string, selected: boolean, index: number) {
  return {
    id: `tabpanel-${index}`,
    role: 'tabpanel' as const,
    'aria-labelledby': tabId,
    tabIndex: 0,
    hidden: !selected,
  };
}

// ── Export All ───────────────────────────────────────────────────────

export default {
  useFocusTrap,
  useFocusRestore,
  useArrowNavigation,
  useAnnouncer,
  useReducedMotion,
  useHighContrast,
  announce,
  getFocusableElements,
  createSkipLink,
  getContrastRatio,
  meetsWCAGAA,
  generateAriaId,
  ariaDescribedBy,
  ariaLabelledBy,
  ariaControls,
  ariaExpanded,
  ariaHidden,
  ariaCurrent,
  createFieldAttributes,
  createErrorAttributes,
  createIconButtonAttributes,
  createLoadingButtonAttributes,
  createModalAttributes,
  createTableHeaderAttributes,
  createTabAttributes,
  createTabPanelAttributes,
};
