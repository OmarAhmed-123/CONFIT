// Performance monitoring and optimization utilities

// Debounce function
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Throttle function
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// Request Idle Callback polyfill
export const requestIdleCallback =
  typeof window !== 'undefined' && 'requestIdleCallback' in window
    ? window.requestIdleCallback
    : (cb: IdleRequestCallback) => setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 50 }), 1);

// Measure performance
export function measurePerformance(name: string, fn: () => void) {
  if (typeof performance !== 'undefined') {
    performance.mark(`${name}-start`);
    fn();
    performance.mark(`${name}-end`);
    performance.measure(name, `${name}-start`, `${name}-end`);
    const measure = performance.getEntriesByName(name)[0];
    console.log(`${name} took ${measure.duration}ms`);
    return measure.duration;
  }
  fn();
  return 0;
}

// Chunk array for batch processing
export function chunkArray<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

// Process in batches to avoid blocking
export async function processBatch<T, R>(
  items: T[],
  processor: (item: T) => R,
  batchSize = 50,
  delay = 0
): Promise<R[]> {
  const results: R[] = [];
  const chunks = chunkArray(items, batchSize);
  
  for (const chunk of chunks) {
    const chunkResults = chunk.map(processor);
    results.push(...chunkResults);
    if (delay > 0) {
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
  
  return results;
}

// Memory-efficient deep clone
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map(deepClone) as T;
  
  const cloned = {} as T;
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      cloned[key] = deepClone(obj[key]);
    }
  }
  return cloned;
}

// Memoize function results
export function memoize<T extends (...args: any[]) => any>(
  fn: T,
  resolver?: (...args: Parameters<T>) => string
): T {
  const cache = new Map<string, ReturnType<T>>();
  
  return ((...args: Parameters<T>) => {
    const key = resolver ? resolver(...args) : JSON.stringify(args);
    if (cache.has(key)) {
      return cache.get(key);
    }
    const result = fn(...args);
    cache.set(key, result);
    return result;
  }) as T;
}

// RAF-based scheduler
export class RafScheduler {
  private scheduled = new Map<string, () => void>();
  private rafId: number | null = null;

  schedule(id: string, callback: () => void) {
    this.scheduled.set(id, callback);
    if (!this.rafId) {
      this.rafId = requestAnimationFrame(() => {
        this.scheduled.forEach((cb) => cb());
        this.scheduled.clear();
        this.rafId = null;
      });
    }
  }

  cancel(id: string) {
    this.scheduled.delete(id);
  }
}

// Image preload
export function preloadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

// Batch image preload
export async function preloadImages(sources: string[], concurrency = 3): Promise<HTMLImageElement[]> {
  const results: HTMLImageElement[] = [];
  const chunks = chunkArray(sources, concurrency);
  
  for (const chunk of chunks) {
    const images = await Promise.all(chunk.map(preloadImage));
    results.push(...images);
  }
  
  return results;
}

// Performance observer wrapper
export function observePerformance(
  entryTypes: string[],
  callback: (entries: PerformanceEntry[]) => void
): PerformanceObserver | null {
  if (typeof PerformanceObserver === 'undefined') return null;
  
  try {
    const observer = new PerformanceObserver((list) => {
      callback(list.getEntries());
    });
    observer.observe({ entryTypes });
    return observer;
  } catch {
    return null;
  }
}

// Web Vitals helpers
export function getCLS(callback: (value: number) => void) {
  return observePerformance(['layout-shift'], (entries) => {
    let clsValue = 0;
    entries.forEach((entry) => {
      if (!(entry as any).hadRecentInput) {
        clsValue += (entry as any).value;
      }
    });
    callback(clsValue);
  });
}

export function getFID(callback: (value: number) => void) {
  return observePerformance(['first-input'], (entries) => {
    const firstInput = entries[0] as any;
    callback(firstInput.processingStart - firstInput.startTime);
  });
}

export function getLCP(callback: (value: number) => void) {
  return observePerformance(['largest-contentful-paint'], (entries) => {
    const lastEntry = entries[entries.length - 1] as any;
    callback(lastEntry.startTime);
  });
}

// Bundle size tracker
export function trackBundleSize() {
  if (typeof navigator !== 'undefined' && 'connection' in navigator) {
    const connection = (navigator as any).connection;
    console.log('Effective connection type:', connection.effectiveType);
    console.log('Downlink:', connection.downlink, 'Mbps');
    console.log('RTT:', connection.rtt, 'ms');
  }
}
