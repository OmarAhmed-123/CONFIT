import { useState, useEffect, useCallback } from 'react';

// Hook for checking online status
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

// Hook for local storage with offline support
export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error('Error writing to localStorage:', error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue] as const;
}

// Hook for indexedDB operations (for larger offline data)
export function useIndexedDB(dbName: string, storeName: string) {
  const [db, setDb] = useState<IDBDatabase | null>(null);

  useEffect(() => {
    const request = indexedDB.open(dbName, 1);

    request.onerror = () => {
      console.error('Error opening IndexedDB');
    };

    request.onsuccess = () => {
      setDb(request.result);
    };

    request.onupgradeneeded = (event) => {
      const database = (event.target as IDBOpenDBRequest).result;
      if (!database.objectStoreNames.contains(storeName)) {
        database.createObjectStore(storeName, { keyPath: 'id' });
      }
    };

    return () => {
      db?.close();
    };
  }, [dbName, storeName]);

  const addItem = useCallback(async (item: { id: string; [key: string]: unknown }) => {
    if (!db) return;

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.add(item);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }, [db, storeName]);

  const getItem = useCallback(async (id: string) => {
    if (!db) return null;

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.get(id);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }, [db, storeName]);

  const getAllItems = useCallback(async () => {
    if (!db) return [];

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }, [db, storeName]);

  const deleteItem = useCallback(async (id: string) => {
    if (!db) return;

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.delete(id);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }, [db, storeName]);

  return { addItem, getItem, getAllItems, deleteItem };
}

// Hook for caching API responses
export function useCache<T>(key: string, fetcher: () => Promise<T>, maxAge = 5 * 60 * 1000) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isOnline = useOnlineStatus();

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const result = await fetcher();
      setData(result);
      setError(null);
      
      // Cache the result
      const cacheItem = {
        data: result,
        timestamp: Date.now(),
        maxAge,
      };
      localStorage.setItem(`cache-${key}`, JSON.stringify(cacheItem));
    } catch (err) {
      setError(err as Error);
      
      // Try to load from cache
      const cached = localStorage.getItem(`cache-${key}`);
      if (cached) {
        const cacheItem = JSON.parse(cached);
        if (Date.now() - cacheItem.timestamp < cacheItem.maxAge) {
          setData(cacheItem.data);
        }
      }
    } finally {
      setIsLoading(false);
    }
  }, [key, fetcher, maxAge]);

  useEffect(() => {
    // Try to load from cache first
    const cached = localStorage.getItem(`cache-${key}`);
    if (cached) {
      const cacheItem = JSON.parse(cached);
      if (Date.now() - cacheItem.timestamp < cacheItem.maxAge) {
        setData(cacheItem.data);
        setIsLoading(false);
        return;
      }
    }

    // Fetch fresh data if online
    if (isOnline) {
      fetchData();
    } else {
      setIsLoading(false);
    }
  }, [key, maxAge, isOnline, fetchData]);

  const invalidate = useCallback(() => {
    localStorage.removeItem(`cache-${key}`);
    if (isOnline) {
      fetchData();
    }
  }, [key, isOnline, fetchData]);

  return { data, isLoading, error, refetch: fetchData, invalidate };
}

// Hook for service worker registration
export function useServiceWorker() {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').then((reg) => {
        setRegistration(reg);

        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                setUpdateAvailable(true);
              }
            });
          }
        });
      }).catch((error) => {
        console.error('Service worker registration failed:', error);
      });
    }
  }, []);

  const update = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  }, [registration]);

  return { registration, updateAvailable, update };
}
