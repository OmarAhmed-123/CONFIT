'use client';

import { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from 'react';
import { SplashScreen } from './SplashScreen';

type LoadingVariant = 'startup' | 'auth' | 'dashboard' | 'payment' | 'tryon' | 'route';

interface LoadingState {
  id: string;
  variant: LoadingVariant;
  message?: string;
  progress?: number;
  priority: number;
}

interface LoadingManagerContextType {
  isLoading: boolean;
  activeState: LoadingState | null;
  startLoading: (variant: LoadingVariant, options?: { message?: string; progress?: number; priority?: number; id?: string }) => string;
  updateLoading: (id: string, updates: Partial<Omit<LoadingState, 'id' | 'variant'>>) => void;
  stopLoading: (id: string) => void;
  withLoading: <T>(
    variant: LoadingVariant,
    promise: Promise<T>,
    options?: { message?: string; priority?: number }
  ) => Promise<T>;
}

const LoadingManagerContext = createContext<LoadingManagerContextType | undefined>(undefined);

let globalId = 0;
function generateId() {
  return `loading-${++globalId}-${Date.now()}`;
}

const PRIORITY_WEIGHTS: Record<LoadingVariant, number> = {
  startup: 100,
  auth: 90,
  payment: 80,
  tryon: 70,
  dashboard: 60,
  route: 50,
};

export function LoadingManagerProvider({ children }: { children: ReactNode }) {
  const [loadingStates, setLoadingStates] = useState<LoadingState[]>([]);
  const activeState = useMemo((): LoadingState | null => {
    if (loadingStates.length === 0) return null;
    return loadingStates.reduce((highest: LoadingState, current: LoadingState) =>
      current.priority > highest.priority ? current : highest
    );
  }, [loadingStates]);
  const isLoading = activeState !== null;

  const startLoading = useCallback(
    (
      variant: LoadingVariant,
      options?: { message?: string; progress?: number; priority?: number; id?: string }
    ): string => {
      const id = options?.id ?? generateId();
      const priority = options?.priority ?? PRIORITY_WEIGHTS[variant];
      setLoadingStates((prev: LoadingState[]) => {
        const exists = prev.find((s: LoadingState) => s.id === id);
        if (exists) return prev;
        return [...prev, { id, variant, message: options?.message, progress: options?.progress, priority }];
      });
      return id;
    },
    []
  );

  const updateLoading = useCallback(
    (id: string, updates: Partial<Omit<LoadingState, 'id' | 'variant'>>) => {
      setLoadingStates((prev: LoadingState[]) =>
        prev.map((s: LoadingState) => (s.id === id ? { ...s, ...updates } : s))
      );
    },
    []
  );

  const stopLoading = useCallback((id: string) => {
    setLoadingStates((prev: LoadingState[]) => prev.filter((s: LoadingState) => s.id !== id));
  }, []);

  const withLoading = useCallback(
    <T,>(
      variant: LoadingVariant,
      promise: Promise<T>,
      options?: { message?: string; priority?: number }
    ): Promise<T> => {
      const id = startLoading(variant, {
        message: options?.message,
        priority: options?.priority,
      });
      return promise.finally(() => stopLoading(id));
    },
    [startLoading, stopLoading]
  );

  return (
    <LoadingManagerContext.Provider
      value={{ isLoading, activeState, startLoading, updateLoading, stopLoading, withLoading }}
    >
      <SplashScreen
        isVisible={isLoading}
        variant={activeState?.variant ?? 'startup'}
        message={activeState?.message}
        progress={activeState?.progress}
        minDuration={activeState?.variant === 'startup' ? 900 : activeState?.variant === 'route' ? 300 : 700}
      />
      {children}
    </LoadingManagerContext.Provider>
  );
}

export function useLoadingManager() {
  const context = useContext(LoadingManagerContext);
  if (context === undefined) {
    throw new Error('useLoadingManager must be used within LoadingManagerProvider');
  }
  return context;
}
