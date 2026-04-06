/**
 * CONFIT — Sales Alert Store
 * ============================
 * Zustand store for intelligent real-time sales alerts.
 * Manages alert state, preferences, throttling, and history.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import {
  type SalesAlert,
  type SalesAlertType,
  type AlertSeverity,
  type AlertStatus,
  type SalesAlertPreferences,
  type AlertHistoryFilter,
  type AlertHistorySort,
  type AlertThresholdConfig,
  type AlertFrequencyConfig,
  type AlertTypePreference,
  DEFAULT_THRESHOLD_CONFIG,
  DEFAULT_FREQUENCY_CONFIG,
  DEFAULT_TYPE_PREFERENCES,
  generateAlertTitle,
  generateRichPreview,
  generateAlertActions,
} from '@/types/salesAlertTypes';

// ─── Deduplication Cache ───

interface DedupEntry {
  alertId: string;
  firstTriggered: string;
  lastTriggered: string;
  count: number;
}

// In-memory deduplication (resets on page refresh, backend handles persistent dedup)
const dedupCache = new Map<string, DedupEntry>();

function makeDedupKey(type: SalesAlertType, storeId: string, identifier: string): string {
  return `${type}::${storeId}::${identifier}`;
}

function isWithinDedupWindow(key: string, windowMinutes: number): boolean {
  const entry = dedupCache.get(key);
  if (!entry) return false;
  const lastTriggered = new Date(entry.lastTriggered);
  const now = new Date();
  const diffMs = now.getTime() - lastTriggered.getTime();
  return diffMs < windowMinutes * 60 * 1000;
}

function recordTrigger(key: string, alertId: string): void {
  const existing = dedupCache.get(key);
  const now = new Date().toISOString();
  if (existing) {
    existing.lastTriggered = now;
    existing.count += 1;
    existing.alertId = alertId;
  } else {
    dedupCache.set(key, {
      alertId,
      firstTriggered: now,
      lastTriggered: now,
      count: 1,
    });
  }
}

// ─── Throttling State ───

interface ThrottleState {
  hourlyCount: number;
  hourStart: string;
  batchQueue: SalesAlert[];
  lastBatchSent: string | null;
}

function getHourKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}-${now.getHours()}`;
}

// ─── Store State Interface ───

interface SalesAlertState {
  // Alert storage
  alerts: SalesAlert[];
  unreadCount: number;

  // Preferences per store
  preferencesMap: Record<string, SalesAlertPreferences>;

  // Throttling state
  throttleState: ThrottleState;

  // History filters
  activeFilters: AlertHistoryFilter;
  activeSort: AlertHistorySort;

  // ─── Alert Actions ───

  addAlert: (alert: SalesAlert) => void;
  addAlerts: (alerts: SalesAlert[]) => void;
  markRead: (alertId: string) => void;
  markAllRead: () => void;
  dismissAlert: (alertId: string) => void;
  acknowledgeAlert: (alertId: string) => void;
  resolveAlert: (alertId: string) => void;
  deleteAlert: (alertId: string) => void;
  clearAlerts: (storeId: string) => void;

  // ─── Alert Retrieval ───

  getAlertsForStore: (storeId: string) => SalesAlert[];
  getUnreadAlerts: (storeId: string) => SalesAlert[];
  getFilteredHistory: (storeId: string, filters: AlertHistoryFilter, sort: AlertHistorySort) => SalesAlert[];
  getAlertsBySeverity: (storeId: string, severity: AlertSeverity) => SalesAlert[];
  getAlertsByType: (storeId: string, type: SalesAlertType) => SalesAlert[];

  // ─── Preferences ───

  getPreferences: (storeId: string) => SalesAlertPreferences;
  updatePreferences: (storeId: string, prefs: Partial<SalesAlertPreferences>) => void;
  updateThresholds: (storeId: string, thresholds: Partial<AlertThresholdConfig>) => void;
  updateFrequency: (storeId: string, frequency: Partial<AlertFrequencyConfig>) => void;
  updateTypePreference: (storeId: string, type: SalesAlertType, pref: Partial<AlertTypePreference>) => void;
  resetPreferencesToDefaults: (storeId: string) => void;

  // ─── Throttling ───

  checkThrottle: (storeId: string) => { allowed: boolean; remaining: number };
  incrementThrottleCount: () => void;
  queueForBatch: (alert: SalesAlert) => void;
  flushBatchQueue: () => SalesAlert[];
  getBatchQueueSize: () => number;

  // ─── Deduplication ───

  checkDedup: (type: SalesAlertType, storeId: string, identifier: string) => { isDuplicate: boolean; existingAlertId?: string };
  recordDedup: (type: SalesAlertType, storeId: string, identifier: string, alertId: string) => void;

  // ─── Filters ───

  setFilters: (filters: AlertHistoryFilter) => void;
  setSort: (sort: AlertHistorySort) => void;
  clearFilters: () => void;
}

// ─── Default Preferences Factory ───

function createDefaultPreferences(storeId: string): SalesAlertPreferences {
  return {
    store_id: storeId,
    updated_at: new Date().toISOString(),
    thresholds: { ...DEFAULT_THRESHOLD_CONFIG },
    frequency: { ...DEFAULT_FREQUENCY_CONFIG },
    type_preferences: { ...DEFAULT_TYPE_PREFERENCES },
  };
}

// ─── Store Implementation ───

export const useSalesAlertStore = create<SalesAlertState>()(
  persist(
    (set, get) => ({
      // Initial state
      alerts: [],
      unreadCount: 0,
      preferencesMap: {},
      throttleState: {
        hourlyCount: 0,
        hourStart: getHourKey(),
        batchQueue: [],
        lastBatchSent: null,
      },
      activeFilters: {},
      activeSort: { field: 'created_at', direction: 'desc' },

      // ─── Alert Actions ───

      addAlert: (alert) =>
        set((state) => {
          // Check for duplicate by ID
          if (state.alerts.some((a) => a.id === alert.id)) {
            return state;
          }

          const newAlerts = [alert, ...state.alerts];
          const newUnreadCount = alert.read ? state.unreadCount : state.unreadCount + 1;

          return {
            alerts: newAlerts,
            unreadCount: newUnreadCount,
          };
        }),

      addAlerts: (alerts) =>
        set((state) => {
          const existingIds = new Set(state.alerts.map((a) => a.id));
          const newAlerts = alerts.filter((a) => !existingIds.has(a.id));
          if (newAlerts.length === 0) return state;

          const unreadNew = newAlerts.filter((a) => !a.read).length;

          return {
            alerts: [...newAlerts, ...state.alerts],
            unreadCount: state.unreadCount + unreadNew,
          };
        }),

      markRead: (alertId) =>
        set((state) => {
          const alert = state.alerts.find((a) => a.id === alertId);
          if (!alert || alert.read) return state;

          return {
            alerts: state.alerts.map((a) =>
              a.id === alertId ? { ...a, read: true } : a
            ),
            unreadCount: Math.max(0, state.unreadCount - 1),
          };
        }),

      markAllRead: () =>
        set((state) => ({
          alerts: state.alerts.map((a) => ({ ...a, read: true })),
          unreadCount: 0,
        })),

      dismissAlert: (alertId) =>
        set((state) => ({
          alerts: state.alerts.map((a) =>
            a.id === alertId ? { ...a, dismissed: true, status: 'dismissed' as AlertStatus } : a
          ),
        })),

      acknowledgeAlert: (alertId) =>
        set((state) => ({
          alerts: state.alerts.map((a) =>
            a.id === alertId
              ? { ...a, status: 'acknowledged' as AlertStatus, acknowledged_at: new Date().toISOString() }
              : a
          ),
        })),

      resolveAlert: (alertId) =>
        set((state) => ({
          alerts: state.alerts.map((a) =>
            a.id === alertId
              ? { ...a, status: 'resolved' as AlertStatus, resolved_at: new Date().toISOString() }
              : a
          ),
        })),

      deleteAlert: (alertId) =>
        set((state) => {
          const alert = state.alerts.find((a) => a.id === alertId);
          const wasUnread = alert && !alert.read;

          return {
            alerts: state.alerts.filter((a) => a.id !== alertId),
            unreadCount: wasUnread ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
          };
        }),

      clearAlerts: (storeId) =>
        set((state) => {
          const storeAlerts = state.alerts.filter((a) => a.store_id === storeId);
          const unreadDeleted = storeAlerts.filter((a) => !a.read).length;

          return {
            alerts: state.alerts.filter((a) => a.store_id !== storeId),
            unreadCount: Math.max(0, state.unreadCount - unreadDeleted),
          };
        }),

      // ─── Alert Retrieval ───

      getAlertsForStore: (storeId) =>
        get().alerts.filter((a) => a.store_id === storeId && !a.dismissed),

      getUnreadAlerts: (storeId) =>
        get().alerts.filter((a) => a.store_id === storeId && !a.read && !a.dismissed),

      getFilteredHistory: (storeId, filters, sort) => {
        let filtered = get().alerts.filter((a) => a.store_id === storeId);

        // Apply filters
        if (filters.types?.length) {
          filtered = filtered.filter((a) => filters.types!.includes(a.type));
        }
        if (filters.severities?.length) {
          filtered = filtered.filter((a) => filters.severities!.includes(a.severity));
        }
        if (filters.statuses?.length) {
          filtered = filtered.filter((a) => filters.statuses!.includes(a.status));
        }
        if (filters.date_from) {
          filtered = filtered.filter((a) => a.created_at >= filters.date_from!);
        }
        if (filters.date_to) {
          filtered = filtered.filter((a) => a.created_at <= filters.date_to!);
        }
        if (filters.read !== undefined) {
          filtered = filtered.filter((a) => a.read === filters.read);
        }
        if (filters.search) {
          const searchLower = filters.search.toLowerCase();
          filtered = filtered.filter((a) => {
            const titleMatch = a.title.toLowerCase().includes(searchLower);
            const previewMatch = a.rich_preview.toLowerCase().includes(searchLower);
            // Search in data fields
            const data = a.data as unknown as Record<string, unknown>;
            const dataMatch = Object.values(data).some((v) =>
              String(v).toLowerCase().includes(searchLower)
            );
            return titleMatch || previewMatch || dataMatch;
          });
        }

        // Apply sort
        const sorted = [...filtered].sort((a, b) => {
          let comparison = 0;
          switch (sort.field) {
            case 'created_at':
              comparison = a.created_at.localeCompare(b.created_at);
              break;
            case 'severity': {
              const severityOrder = { critical: 0, warning: 1, info: 2 };
              comparison = severityOrder[a.severity] - severityOrder[b.severity];
              break;
            }
            case 'type':
              comparison = a.type.localeCompare(b.type);
              break;
          }
          return sort.direction === 'desc' ? -comparison : comparison;
        });

        return sorted;
      },

      getAlertsBySeverity: (storeId, severity) =>
        get().alerts.filter((a) => a.store_id === storeId && a.severity === severity && !a.dismissed),

      getAlertsByType: (storeId, type) =>
        get().alerts.filter((a) => a.store_id === storeId && a.type === type && !a.dismissed),

      // ─── Preferences ───

      getPreferences: (storeId) => {
        const existing = get().preferencesMap[storeId];
        if (existing) return existing;
        return createDefaultPreferences(storeId);
      },

      updatePreferences: (storeId, prefs) =>
        set((state) => {
          const existing = state.preferencesMap[storeId] || createDefaultPreferences(storeId);
          return {
            preferencesMap: {
              ...state.preferencesMap,
              [storeId]: {
                ...existing,
                ...prefs,
                updated_at: new Date().toISOString(),
              },
            },
          };
        }),

      updateThresholds: (storeId, thresholds) => {
        const existing = get().getPreferences(storeId);
        get().updatePreferences(storeId, {
          thresholds: { ...existing.thresholds, ...thresholds },
        });
      },

      updateFrequency: (storeId, frequency) => {
        const existing = get().getPreferences(storeId);
        get().updatePreferences(storeId, {
          frequency: { ...existing.frequency, ...frequency },
        });
      },

      updateTypePreference: (storeId, type, pref) => {
        const existing = get().getPreferences(storeId);
        get().updatePreferences(storeId, {
          type_preferences: {
            ...existing.type_preferences,
            [type]: { ...existing.type_preferences[type], ...pref },
          },
        });
      },

      resetPreferencesToDefaults: (storeId) =>
        set((state) => ({
          preferencesMap: {
            ...state.preferencesMap,
            [storeId]: createDefaultPreferences(storeId),
          },
        })),

      // ─── Throttling ───

      checkThrottle: (storeId) => {
        const state = get();
        const prefs = state.getPreferences(storeId);
        const currentHourKey = getHourKey();

        // Reset counter if hour changed
        if (state.throttleState.hourStart !== currentHourKey) {
          set({
            throttleState: {
              ...state.throttleState,
              hourlyCount: 0,
              hourStart: currentHourKey,
            },
          });
          return { allowed: true, remaining: prefs.frequency.max_alerts_per_hour };
        }

        const remaining = Math.max(0, prefs.frequency.max_alerts_per_hour - state.throttleState.hourlyCount);
        return {
          allowed: state.throttleState.hourlyCount < prefs.frequency.max_alerts_per_hour,
          remaining,
        };
      },

      incrementThrottleCount: () =>
        set((state) => ({
          throttleState: {
            ...state.throttleState,
            hourlyCount: state.throttleState.hourlyCount + 1,
          },
        })),

      queueForBatch: (alert) =>
        set((state) => ({
          throttleState: {
            ...state.throttleState,
            batchQueue: [...state.throttleState.batchQueue, alert],
          },
        })),

      flushBatchQueue: () => {
        const queue = get().throttleState.batchQueue;
        set((state) => ({
          throttleState: {
            ...state.throttleState,
            batchQueue: [],
            lastBatchSent: new Date().toISOString(),
          },
        }));
        return queue;
      },

      getBatchQueueSize: () => get().throttleState.batchQueue.length,

      // ─── Deduplication ───

      checkDedup: (type, storeId, identifier) => {
        const prefs = get().getPreferences(storeId);
        const key = makeDedupKey(type, storeId, identifier);

        if (isWithinDedupWindow(key, prefs.frequency.dedup_window_minutes)) {
          const entry = dedupCache.get(key);
          return { isDuplicate: true, existingAlertId: entry?.alertId };
        }

        return { isDuplicate: false };
      },

      recordDedup: (type, storeId, identifier, alertId) => {
        const key = makeDedupKey(type, storeId, identifier);
        recordTrigger(key, alertId);
      },

      // ─── Filters ───

      setFilters: (filters) =>
        set({ activeFilters: filters }),

      setSort: (sort) =>
        set({ activeSort: sort }),

      clearFilters: () =>
        set({ activeFilters: {} }),
    }),
    {
      name: 'confit-sales-alerts',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        alerts: state.alerts,
        preferencesMap: state.preferencesMap,
        activeFilters: state.activeFilters,
        activeSort: state.activeSort,
      }),
    }
  )
);

// ─── Alert Factory Helper ───

export function createSalesAlert(
  type: SalesAlertType,
  severity: AlertSeverity,
  data: Parameters<typeof generateAlertTitle>[1],
  storeId: string,
  storeName: string
): SalesAlert {
  const id = `alert-${type}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  const now = new Date().toISOString();

  // Create dedup key based on alert type
  let identifier = '';
  switch (type) {
    case 'high_value_order':
      identifier = (data as { order_id: string }).order_id;
      break;
    case 'unusual_returns':
      identifier = (data as { product_id: string }).product_id;
      break;
    case 'inventory_depletion':
      identifier = (data as { product_id: string }).product_id;
      break;
    case 'conversion_anomaly':
      identifier = storeId; // Store-level alert
      break;
    case 'customer_segment_change':
      identifier = (data as { customer_id: string }).customer_id;
      break;
  }

  return {
    id,
    type,
    severity,
    status: 'active',
    title: generateAlertTitle(type, data),
    message: generateAlertTitle(type, data),
    rich_preview: generateRichPreview(type, data),
    data,
    actions: generateAlertActions(type, data),
    store_id: storeId,
    store_name: storeName,
    created_at: now,
    read: false,
    dismissed: false,
    dedup_key: makeDedupKey(type, storeId, identifier),
    first_triggered_at: now,
    trigger_count: 1,
    last_triggered_at: now,
  };
}

export default useSalesAlertStore;
