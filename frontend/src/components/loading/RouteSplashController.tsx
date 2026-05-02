'use client';

import { useEffect, useRef } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { useLoadingManager } from './LoadingManager';

const STARTUP_SPLASH_ID = 'startup-splash';

export function RouteSplashController() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const routeKey = `${pathname}?${searchParams?.toString() || ''}`;
  const previousRouteRef = useRef<string | null>(null);
  const { startLoading, stopLoading } = useLoadingManager();

  useEffect(() => {
    startLoading('startup', {
      id: STARTUP_SPLASH_ID,
      message: 'Launching CONFIT',
      priority: 120,
    });

    const timer = setTimeout(() => stopLoading(STARTUP_SPLASH_ID), 900);
    return () => clearTimeout(timer);
  }, [startLoading, stopLoading]);

  useEffect(() => {
    if (previousRouteRef.current === null) {
      previousRouteRef.current = routeKey;
      return;
    }

    if (previousRouteRef.current === routeKey) {
      return;
    }

    previousRouteRef.current = routeKey;
    const loadingId = startLoading('route', {
      message: 'Loading page',
      priority: 55,
    });

    const timer = setTimeout(() => stopLoading(loadingId), 300);
    return () => clearTimeout(timer);
  }, [routeKey, startLoading, stopLoading]);

  return null;
}
