import { lazy, Suspense, ComponentType } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

// Generic lazy component factory
export function createLazyComponent<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  fallback: React.ReactNode = <Skeleton className="h-32 w-full" />
) {
  const LazyComponent = lazy(importFn);

  return function LazyComponentWrapper(props: React.ComponentProps<T>) {
    return (
      <Suspense fallback={fallback}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}

// Lazy loaded heavy components - placeholders for future implementation
// export const LazyChatbotWidget = createLazyComponent(
//   () => import('@/components/ChatbotWidget'),
//   <Skeleton className="h-96 w-full rounded-lg" />
// );

// Intersection Observer based lazy loading wrapper
interface LazyLoadProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  rootMargin?: string;
  threshold?: number;
  className?: string;
  once?: boolean;
}

export function LazyLoad({
  children,
  fallback = <Skeleton className="h-32 w-full" />,
  rootMargin = '200px',
  threshold = 0.01,
  className,
  once = true,
}: LazyLoadProps) {
  const [isInView, setIsInView] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          if (once) {
            observer.disconnect();
          }
        } else if (!once) {
          setIsInView(false);
        }
      },
      { rootMargin, threshold }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [rootMargin, threshold, once]);

  return (
    <div ref={ref} className={className}>
      {isInView ? children : fallback}
    </div>
  );
}

import { useState, useRef, useEffect } from 'react';

// Chunk loader for code splitting
interface ChunkLoaderProps {
  load: () => Promise<any>;
  children: (data: any) => React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error) => void;
}

export function ChunkLoader({
  load,
  children,
  fallback = <Skeleton className="h-32 w-full" />,
  onError,
}: ChunkLoaderProps) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    load()
      .then((result) => {
        if (mounted) {
          setData(result);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err);
          setIsLoading(false);
          onError?.(err);
        }
      });

    return () => {
      mounted = false;
    };
  }, [load, onError]);

  if (isLoading) {
    return <>{fallback}</>;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
        Failed to load component
      </div>
    );
  }

  return <>{children(data)}</>;
}

// Preload helper
export function preloadRoute(route: string) {
  switch (route) {
    case '/':
      return import('@/pages/Index');
    case '/discover':
      return import('@/pages/Discover');
    case '/stylist':
      return import('@/pages/VirtualStylist');
    case '/try-on':
      return import('@/pages/VirtualTryOn');
    case '/outfits':
      return import('@/pages/OutfitBuilder');
    case '/wardrobe':
      return import('@/pages/Wardrobe');
    case '/visual-search':
      return import('@/pages/VisualSearch');
    case '/profile':
      return import('@/pages/Profile');
    case '/cart':
      return import('@/pages/Cart');
    case '/checkout':
      return import('@/pages/Checkout');
    case '/orders':
      return import('@/pages/OrderHistory');
    case '/brand-dashboard':
      return import('@/pages/BrandDashboard');
    case '/admin':
      return import('@/pages/AdminPanel');
    case '/wishlist':
      return import('@/pages/Wishlist');
    case '/brands':
      return import('@/pages/BrandsPage');
    default:
      return Promise.resolve();
  }
}

// Route prefetcher component
interface RoutePrefetcherProps {
  route: string;
  children: React.ReactNode;
  delay?: number;
}

export function RoutePrefetcher({ route, children, delay = 100 }: RoutePrefetcherProps) {
  const timeoutRef = useRef<NodeJS.Timeout>();

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      preloadRoute(route);
    }, delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  };

  return (
    <div onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      {children}
    </div>
  );
}
