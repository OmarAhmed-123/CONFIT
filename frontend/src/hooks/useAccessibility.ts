import { useEffect, useRef, useCallback, useState } from 'react';
import { createFocusTrap, announce, prefersReducedMotion, Keys } from '@/lib/accessibility';

// Focus trap hook
export function useFocusTrap(isActive: boolean) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!isActive || !ref.current) return;

    const trap = createFocusTrap(ref.current);
    trap.activate();

    return () => trap.deactivate();
  }, [isActive]);

  return ref;
}

// Keyboard navigation hook
export function useKeyboardNavigation(
  handlers: Partial<Record<keyof typeof Keys, (e: KeyboardEvent) => void>>
) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const handler = handlers[e.key as keyof typeof Keys];
      if (handler) {
        handler(e);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handlers]);
}

// Announce to screen readers
export function useAnnounce() {
  return useCallback((message: string, priority?: 'polite' | 'assertive') => {
    announce(message, priority);
  }, []);
}

// Reduced motion hook
export function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    
    const handler = (e: MediaQueryListEvent) => {
      setReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return reducedMotion;
}

// Focus management hook
export function useFocusManagement() {
  const previousFocus = useRef<HTMLElement | null>(null);

  const saveFocus = useCallback(() => {
    previousFocus.current = document.activeElement as HTMLElement;
  }, []);

  const restoreFocus = useCallback(() => {
    previousFocus.current?.focus();
  }, []);

  const setFocus = useCallback((element: HTMLElement | null) => {
    element?.focus();
  }, []);

  return { saveFocus, restoreFocus, setFocus };
}

// Roving tabindex hook for lists/menus
export function useRovingTabIndex(items: HTMLElement[]) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    items.forEach((item, index) => {
      item.tabIndex = index === currentIndex ? 0 : -1;
    });
  }, [items, currentIndex]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, orientation: 'horizontal' | 'vertical' = 'vertical') => {
      const nextKey = orientation === 'vertical' ? Keys.ARROW_DOWN : Keys.ARROW_RIGHT;
      const prevKey = orientation === 'vertical' ? Keys.ARROW_UP : Keys.ARROW_LEFT;

      let newIndex = currentIndex;

      if (e.key === nextKey) {
        e.preventDefault();
        newIndex = (currentIndex + 1) % items.length;
      } else if (e.key === prevKey) {
        e.preventDefault();
        newIndex = (currentIndex - 1 + items.length) % items.length;
      } else if (e.key === Keys.HOME) {
        e.preventDefault();
        newIndex = 0;
      } else if (e.key === Keys.END) {
        e.preventDefault();
        newIndex = items.length - 1;
      }

      if (newIndex !== currentIndex) {
        setCurrentIndex(newIndex);
        items[newIndex]?.focus();
      }
    },
    [currentIndex, items]
  );

  return { currentIndex, setCurrentIndex, handleKeyDown };
}

// Skip link hook
export function useSkipLink(targetId: string) {
  useEffect(() => {
    const skipLink = document.querySelector(`a[href="#${targetId}"]`);
    if (!skipLink) {
      const link = document.createElement('a');
      link.href = `#${targetId}`;
      link.className = 'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md';
      link.textContent = 'Skip to main content';
      document.body.insertBefore(link, document.body.firstChild);
    }
  }, [targetId]);
}

// Live region hook
export function useLiveRegion() {
  const regionRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const region = document.createElement('div');
    region.setAttribute('aria-live', 'polite');
    region.setAttribute('aria-atomic', 'true');
    region.className = 'sr-only';
    document.body.appendChild(region);
    regionRef.current = region;

    return () => region.remove();
  }, []);

  const updateRegion = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (regionRef.current) {
      regionRef.current.setAttribute('aria-live', priority);
      regionRef.current.textContent = '';
      // Force re-announcement
      setTimeout(() => {
        if (regionRef.current) {
          regionRef.current.textContent = message;
        }
      }, 50);
    }
  }, []);

  return updateRegion;
}
