/**
 * CONFIT — usePreferenceSync Hook
 * =================================
 * Enhanced hook for notification preference synchronization with:
 * - Optimistic updates with rollback
 * - Conflict detection and resolution
 * - Offline queue with IndexedDB
 * - Real-time sync status
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { v4 as uuidv4 } from 'uuid';
import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

export type DeviceType = 'mobile_app' | 'desktop_browser' | 'tablet_app' | 'other';
export type RecipientType = 'customer' | 'owner';
export type ChannelType = 'in_app' | 'email' | 'push' | 'toast';
export type FrequencySetting = 'real_time' | 'daily_digest' | 'weekly_summary' | 'disabled';
export type ConflictType = 'VERSION_STALE' | 'CONCURRENT_UPDATE' | 'CHECKSUM_MISMATCH';

export interface PreferenceState {
  global_enabled: boolean;
  channels: {
    in_app: { enabled: boolean; frequency: FrequencySetting };
    email: { enabled: boolean; frequency: FrequencySetting };
    push: { enabled: boolean; frequency: FrequencySetting };
    toast: { enabled: boolean; frequency: FrequencySetting };
  };
  notification_types: Record<string, {
    enabled: boolean;
    channels?: Record<string, { enabled: boolean }>;
  }>;
  batch_settings: {
    daily_digest?: { preferred_time: string; last_sent?: string };
    weekly_summary?: { preferred_day: string; preferred_time: string; last_sent?: string };
  };
}

export interface ServerPreferenceData {
  preferences: PreferenceState;
  sync_version: string;
  checksum: string;
  last_modified: string;
  registered_devices: RegisteredDevice[];
}

export interface RegisteredDevice {
  device_id: string;
  device_type: DeviceType;
  device_name: string | null;
  last_seen_at: string;
  registered_at: string;
  is_current: boolean;
}

export interface PendingOperation {
  id: string;
  type: 'update';
  payload: Partial<PreferenceState>;
  timestamp: Date;
  retryCount: number;
  status: 'pending' | 'syncing' | 'failed' | 'completed';
}

export interface ConflictError {
  code: 'CONFLICT_DETECTED';
  message: string;
  conflict_type: ConflictType;
  current_server_state: PreferenceState;
  server_sync_version: string;
  server_checksum: string;
  resolution?: {
    type: 'server_wins' | 'client_wins' | 'merged';
    details: string;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// INDEXED DB FOR OFFLINE QUEUE
// ─────────────────────────────────────────────────────────────────────────────

interface OfflineQueueDB extends DBSchema {
  pendingUpdates: {
    key: string;
    value: PendingOperation;
  };
  staleState: {
    key: string;
    value: { preferences: PreferenceState; timestamp: Date };
  };
}

let dbPromise: Promise<IDBPDatabase<OfflineQueueDB>> | null = null;

async function getDB(): Promise<IDBPDatabase<OfflineQueueDB>> {
  if (dbPromise) return dbPromise;
  
  dbPromise = openDB<OfflineQueueDB>('confit-preference-sync', 1, {
    upgrade(db) {
      db.createObjectStore('pendingUpdates', { keyPath: 'id' });
      db.createObjectStore('staleState', { keyPath: 'id' });
    },
  });
  
  return dbPromise;
}

// ─────────────────────────────────────────────────────────────────────────────
// DEVICE ID MANAGEMENT
// ─────────────────────────────────────────────────────────────────────────────

const DEVICE_ID_KEY = 'confit_device_id';

function getDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    deviceId = `device-${uuidv4()}`;
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

function getDeviceType(): DeviceType {
  const ua = navigator.userAgent.toLowerCase();
  
  if (/mobile|android|iphone|ipad|ipod/.test(ua)) {
    if (/ipad|tablet/.test(ua) || (navigator.maxTouchPoints > 1 && /macintosh/.test(ua))) {
      return 'tablet_app';
    }
    return 'mobile_app';
  }
  
  return 'desktop_browser';
}

// ─────────────────────────────────────────────────────────────────────────────
// API FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

async function fetchPreferences(deviceId: string): Promise<ServerPreferenceData> {
  const token = getAuthToken();
  if (!token) throw new Error('UNAUTHORIZED');
  
  const res = await fetch(
    apiUrl('/api/v1/notifications/preferences'),
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-Device-ID': deviceId,
      },
    }
  );
  
  if (!res.ok) {
    if (res.status === 401) throw new Error('UNAUTHORIZED');
    throw new Error('FETCH_FAILED');
  }
  
  const data = await res.json();
  return data.data;
}

async function updatePreferences(
  update: Partial<PreferenceState>,
  deviceId: string,
  baseSyncVersion: string,
  baseChecksum: string
): Promise<ServerPreferenceData> {
  const token = getAuthToken();
  if (!token) throw new Error('UNAUTHORIZED');
  
  const res = await fetch(
    apiUrl('/api/v1/notifications/preferences'),
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-Idempotency-Key': uuidv4(),
      },
      body: JSON.stringify({
        device_id: deviceId,
        device_type: getDeviceType(),
        base_sync_version: baseSyncVersion,
        base_checksum: baseChecksum,
        client_timestamp: new Date().toISOString(),
        preferences: update,
      }),
    }
  );
  
  if (!res.ok) {
    if (res.status === 409) {
      const error = await res.json();
      const conflictError: ConflictError = {
        code: 'CONFLICT_DETECTED',
        message: error.error?.message || 'Conflict detected',
        conflict_type: error.error?.conflict_type || 'CONCURRENT_UPDATE',
        current_server_state: error.error?.current_server_state,
        server_sync_version: error.error?.server_sync_version,
        server_checksum: error.error?.server_checksum,
        resolution: error.error?.resolution,
      };
      throw conflictError;
    }
    
    if (res.status === 401) throw new Error('UNAUTHORIZED');
    if (res.status === 429) throw new Error('RATE_LIMITED');
    throw new Error('UPDATE_FAILED');
  }
  
  const data = await res.json();
  return data.data;
}

// ─────────────────────────────────────────────────────────────────────────────
// DEFAULT PREFERENCES
// ─────────────────────────────────────────────────────────────────────────────

function getDefaultPreferences(): PreferenceState {
  return {
    global_enabled: true,
    channels: {
      in_app: { enabled: true, frequency: 'real_time' },
      email: { enabled: true, frequency: 'real_time' },
      push: { enabled: true, frequency: 'real_time' },
      toast: { enabled: true, frequency: 'real_time' },
    },
    notification_types: {},
    batch_settings: {},
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN HOOK
// ─────────────────────────────────────────────────────────────────────────────

export interface UsePreferenceSyncOptions {
  recipientType: RecipientType;
  onConflict?: (error: ConflictError) => void;
  onSyncError?: (error: Error) => void;
  onOfflineChange?: (isOffline: boolean) => void;
}

export function usePreferenceSync(options: UsePreferenceSyncOptions) {
  const { recipientType, onConflict, onSyncError, onOfflineChange } = options;
  
  const queryClient = useQueryClient();
  const deviceId = getDeviceId();
  const retryTimeoutRef = useRef<NodeJS.Timeout>();
  
  // Optimistic state (local changes pending sync)
  const [optimisticState, setOptimisticState] = useState<PreferenceState | null>(null);
  const [pendingOperations, setPendingOperations] = useState<PendingOperation[]>([]);
  const [syncError, setSyncError] = useState<Error | null>(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  
  // Fetch server preferences
  const { 
    data: serverData, 
    isLoading, 
    refetch 
  } = useQuery({
    queryKey: ['notification-preferences', deviceId],
    queryFn: () => fetchPreferences(deviceId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
  });
  
  // Persisted state from server
  const persistedState = serverData?.preferences ?? null;
  const syncVersion = serverData?.sync_version ?? '';
  const checksum = serverData?.checksum ?? '';
  
  // Effective state = optimistic overrides persisted
  const effectiveState = optimisticState ?? persistedState ?? getDefaultPreferences();
  
  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      onOfflineChange?.(false);
      // Sync pending operations when back online
      syncPendingOperations();
    };
    
    const handleOffline = () => {
      setIsOnline(false);
      onOfflineChange?.(true);
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [onOfflineChange]);
  
  // Load pending operations from IndexedDB on mount
  useEffect(() => {
    async function loadPendingOperations() {
      try {
        const db = await getDB();
        const pending = await db.getAll('pendingUpdates');
        setPendingOperations(pending.filter(op => op.status === 'pending' || op.status === 'failed'));
      } catch (error) {
        console.error('Failed to load pending operations:', error);
      }
    }
    
    loadPendingOperations();
  }, []);
  
  // Update mutation with optimistic update
  const updateMutation = useMutation({
    mutationFn: async (update: Partial<PreferenceState>) => {
      return updatePreferences(update, deviceId, syncVersion, checksum);
    },
    
    // Optimistic update - apply immediately before server response
    onMutate: async (update) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['notification-preferences'] });
      
      // Snapshot previous state for rollback
      const previousOptimistic = optimisticState;
      
      // Apply optimistic update
      const newOptimistic = applyPartialUpdate(effectiveState, update);
      setOptimisticState(newOptimistic);
      
      // Add to pending queue
      const operation: PendingOperation = {
        id: uuidv4(),
        type: 'update',
        payload: update,
        timestamp: new Date(),
        retryCount: 0,
        status: 'syncing',
      };
      setPendingOperations(prev => [...prev, operation]);
      
      // Store in IndexedDB for offline persistence
      try {
        const db = await getDB();
        await db.put('pendingUpdates', operation);
      } catch (error) {
        console.error('Failed to store pending operation:', error);
      }
      
      // Clear previous error
      setSyncError(null);
      
      return { previousOptimistic, operation };
    },
    
    // Success - merge server response
    onSuccess: async (data, variables, context) => {
      // Update persisted state
      queryClient.setQueryData(['notification-preferences', deviceId], { data });
      
      // Clear optimistic state (server is now authoritative)
      setOptimisticState(null);
      
      // Mark operation as completed
      const updatedOp = { ...context.operation, status: 'completed' as const };
      setPendingOperations(prev => 
        prev.map(op => op.id === context.operation.id ? updatedOp : op)
      );
      
      // Remove from IndexedDB
      try {
        const db = await getDB();
        await db.delete('pendingUpdates', context.operation.id);
      } catch (error) {
        console.error('Failed to remove completed operation:', error);
      }
      
      // Remove from UI after delay
      setTimeout(() => {
        setPendingOperations(prev => prev.filter(op => op.id !== context.operation.id));
      }, 1000);
    },
    
    // Error - rollback and handle
    onError: async (error, variables, context) => {
      if (!context) {
        setSyncError(error instanceof Error ? error : new Error('Sync failed'));
        return;
      }
      // Rollback optimistic state
      setOptimisticState(context.previousOptimistic);
      
      // Mark operation as failed
      const failedOp = { 
        ...context.operation, 
        status: 'failed' as const,
        retryCount: context.operation.retryCount + 1 
      };
      setPendingOperations(prev => 
        prev.map(op => op.id === context.operation.id ? failedOp : op)
      );
      
      // Update in IndexedDB
      try {
        const db = await getDB();
        await db.put('pendingUpdates', failedOp);
      } catch (dbError) {
        console.error('Failed to update failed operation:', dbError);
      }
      
      // Handle specific error types
      if (isConflictError(error)) {
        onConflict?.(error);
        handleConflictError(error);
      } else if (error instanceof Error && error.message === 'RATE_LIMITED') {
        setSyncError(new Error('Too many changes. Please wait a moment.'));
        onSyncError?.(error);
      } else if (error instanceof Error && (error.message === 'NETWORK_ERROR' || !navigator.onLine)) {
        // Network error - schedule retry
        scheduleRetry(context.operation);
      } else {
        setSyncError(error instanceof Error ? error : new Error('Sync failed'));
        onSyncError?.(error instanceof Error ? error : new Error('Sync failed'));
      }
    },
  });
  
  // Handle conflict error
  const handleConflictError = useCallback((error: ConflictError) => {
    // Show conflict resolution UI
    setSyncError(new Error(error.message));
    
    // Force refetch to get current server state
    queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    setOptimisticState(null);
  }, [queryClient]);
  
  // Schedule retry with exponential backoff
  const scheduleRetry = useCallback((operation: PendingOperation) => {
    const maxRetries = 3;
    const baseDelay = 1000;
    
    if (operation.retryCount >= maxRetries) {
      setSyncError(new Error('Unable to sync preferences. Please try manually.'));
      return;
    }
    
    const delay = baseDelay * Math.pow(2, operation.retryCount);
    
    retryTimeoutRef.current = setTimeout(() => {
      if (navigator.onLine) {
        updateMutation.mutate(operation.payload);
      }
    }, delay);
  }, [updateMutation]);
  
  // Sync pending operations when back online
  const syncPendingOperations = useCallback(async () => {
    const failedOps = pendingOperations.filter(op => op.status === 'failed');
    
    for (const op of failedOps) {
      if (op.retryCount < 3) {
        updateMutation.mutate(op.payload);
      }
    }
  }, [pendingOperations, updateMutation]);
  
  // Update preference with optimistic UI
  const updatePreference = useCallback(
    (update: Partial<PreferenceState>) => {
      if (!isOnline) {
        // Queue for later sync
        queueOfflineUpdate(update);
        return;
      }
      
      updateMutation.mutate(update);
    },
    [isOnline, updateMutation]
  );
  
  // Queue update for offline sync
  const queueOfflineUpdate = useCallback(async (update: Partial<PreferenceState>) => {
    const operation: PendingOperation = {
      id: uuidv4(),
      type: 'update',
      payload: update,
      timestamp: new Date(),
      retryCount: 0,
      status: 'pending',
    };
    
    // Apply optimistically
    const newOptimistic = applyPartialUpdate(effectiveState, update);
    setOptimisticState(newOptimistic);
    
    // Store in IndexedDB
    try {
      const db = await getDB();
      await db.put('pendingUpdates', operation);
    } catch (error) {
      console.error('Failed to queue offline update:', error);
    }
    
    setPendingOperations(prev => [...prev, operation]);
  }, [effectiveState]);
  
  // Manual retry for failed operations
  const retryFailedOperations = useCallback(() => {
    const failedOps = pendingOperations.filter(op => op.status === 'failed');
    failedOps.forEach(op => {
      updateMutation.mutate(op.payload);
    });
  }, [pendingOperations, updateMutation]);
  
  // Clear error and reset
  const clearError = useCallback(() => {
    setSyncError(null);
  }, []);
  
  // Refresh from server
  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    setOptimisticState(null);
    setSyncError(null);
  }, [queryClient]);
  
  return {
    // State
    preferences: effectiveState,
    persistedPreferences: persistedState,
    syncVersion,
    checksum,
    isPending: updateMutation.isPending || pendingOperations.some(op => op.status === 'syncing'),
    hasFailedOperations: pendingOperations.some(op => op.status === 'failed'),
    pendingOperationsCount: pendingOperations.filter(op => op.status === 'pending' || op.status === 'failed').length,
    syncError,
    isLoading,
    isOnline,
    deviceId,
    registeredDevices: serverData?.registered_devices ?? [],
    
    // Actions
    updatePreference,
    retryFailedOperations,
    clearError,
    refresh,
    
    // Helpers
    isConflictError: (error: unknown): error is ConflictError => {
      return typeof error === 'object' && error !== null && 'code' in error && (error as any).code === 'CONFLICT_DETECTED';
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

function applyPartialUpdate(
  current: PreferenceState,
  update: Partial<PreferenceState>
): PreferenceState {
  const result = { ...current };
  
  if (update.global_enabled !== undefined) {
    result.global_enabled = update.global_enabled;
  }
  
  if (update.channels) {
    result.channels = {
      in_app: { ...result.channels.in_app, ...update.channels.in_app },
      email: { ...result.channels.email, ...update.channels.email },
      push: { ...result.channels.push, ...update.channels.push },
      toast: { ...result.channels.toast, ...update.channels.toast },
    };
  }
  
  if (update.notification_types) {
    result.notification_types = {
      ...result.notification_types,
      ...update.notification_types,
    };
  }
  
  if (update.batch_settings) {
    result.batch_settings = {
      ...result.batch_settings,
      ...update.batch_settings,
    };
  }
  
  return result;
}

function isConflictError(error: unknown): error is ConflictError {
  return typeof error === 'object' && error !== null && 
    'code' in error && (error as ConflictError).code === 'CONFLICT_DETECTED';
}

export default usePreferenceSync;
