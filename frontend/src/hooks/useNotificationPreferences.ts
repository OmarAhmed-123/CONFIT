/**
 * CONFIT — useNotificationPreferences Hook
 * ==========================================
 * React hook wrapping the preferences store for component use.
 * Provides reactive state and actions for the NotificationPreferences UI.
 * Syncs with backend API for persistence.
 */

import { useCallback, useMemo, useState, useEffect } from 'react';
import {
  useNotificationPreferencesStore,
  getDefaultPreferences,
  getTypesForRecipient,
  type NotificationChannel,
  type NotificationFrequency,
  type RecipientType,
  type NotificationPreferences,
} from '@/stores/notificationPreferencesStore';
import { apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';

interface UseNotificationPreferencesOptions {
  recipientId: string;
  recipientType: RecipientType;
}

interface APIPreferences {
  id: string;
  recipient_id: string;
  recipient_type: string;
  channel_preferences: { in_app: boolean; email: boolean; push: boolean };
  frequency_settings: Record<string, NotificationFrequency>;
  notification_types: string[];
  batch_options: { enabled: boolean };
  version: number;
}

async function fetchPreferences(recipientType: RecipientType): Promise<APIPreferences | null> {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const res = await fetch(apiUrl(`/api/notification-preferences?recipient_type=${recipientType}`), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function savePreferencesToAPI(
  recipientType: RecipientType,
  data: Partial<NotificationPreferences>
): Promise<boolean> {
  const token = getAuthToken();
  if (!token) return false;

  try {
    const res = await fetch(apiUrl(`/api/notification-preferences?recipient_type=${recipientType}`), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    return res.ok;
  } catch {
    return false;
  }
}

async function resetPreferencesOnAPI(recipientType: RecipientType): Promise<APIPreferences | null> {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const res = await fetch(apiUrl(`/api/notification-preferences/reset?recipient_type=${recipientType}`), {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export function useNotificationPreferences({
  recipientId,
  recipientType,
}: UseNotificationPreferencesOptions) {
  const store = useNotificationPreferencesStore();
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const preferences = useMemo(
    () => store.getPreferences(recipientId, recipientType),
    [store, recipientId, recipientType]
  );

  const availableTypes = useMemo(
    () => getTypesForRecipient(recipientType),
    [recipientType]
  );

  // Load preferences from API on mount
  useEffect(() => {
    let mounted = true;
    async function loadPreferences() {
      setIsLoading(true);
      const apiPrefs = await fetchPreferences(recipientType);
      if (mounted && apiPrefs) {
        // Sync store with API data
        store.savePreferences({
          recipient_id: apiPrefs.recipient_id,
          recipient_type: apiPrefs.recipient_type as RecipientType,
          channel_preferences: apiPrefs.channel_preferences,
          frequency_settings: apiPrefs.frequency_settings,
          notification_types: apiPrefs.notification_types,
          batch_options: apiPrefs.batch_options,
        });
      }
      if (mounted) setIsLoading(false);
    }
    loadPreferences();
    return () => { mounted = false; };
  }, [recipientType, store]);

  // ── Channel helpers ──

  const updateChannelPreference = useCallback(
    (channel: NotificationChannel, enabled: boolean) => {
      store.setChannelEnabled(recipientId, recipientType, channel, enabled);
      setSaveSuccess(false);
    },
    [store, recipientId, recipientType]
  );

  const toggleChannel = useCallback(
    (channel: NotificationChannel) => {
      store.toggleChannel(recipientId, recipientType, channel);
      setSaveSuccess(false);
    },
    [store, recipientId, recipientType]
  );

  // ── Type helpers ──

  const toggleType = useCallback(
    (type: string) => {
      store.toggleType(recipientId, recipientType, type);
      setSaveSuccess(false);
    },
    [store, recipientId, recipientType]
  );

  // ── Frequency helpers ──

  const updateTypeFrequency = useCallback(
    (type: string, frequency: NotificationFrequency) => {
      store.setFrequencyForType(recipientId, recipientType, type, frequency);
      setSaveSuccess(false);
    },
    [store, recipientId, recipientType]
  );

  // ── Batch helpers (owner) ──

  const updateBatchOption = useCallback(
    (enabled: boolean) => {
      store.setBatchEnabled(recipientId, recipientType, enabled);
      setSaveSuccess(false);
    },
    [store, recipientId, recipientType]
  );

  // ── Save ──

  const save = useCallback(async () => {
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      // Get current preferences from store
      const currentPrefs = store.getPreferences(recipientId, recipientType);
      
      // Save to API
      const success = await savePreferencesToAPI(recipientType, {
        channel_preferences: currentPrefs.channel_preferences,
        frequency_settings: currentPrefs.frequency_settings,
        notification_types: currentPrefs.notification_types,
        batch_options: currentPrefs.batch_options,
      });

      if (success) {
        // Also persist to localStorage via store
        store.savePreferences(currentPrefs);
        setSaveSuccess(true);
      } else {
        setSaveError('Failed to save preferences to server');
      }
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save preferences');
    } finally {
      setIsSaving(false);
    }
  }, [store, recipientId, recipientType]);

  // ── Reset ──

  const resetToDefaults = useCallback(async () => {
    setSaveError(null);
    const apiPrefs = await resetPreferencesOnAPI(recipientType);
    if (apiPrefs) {
      store.savePreferences({
        recipient_id: apiPrefs.recipient_id,
        recipient_type: apiPrefs.recipient_type as RecipientType,
        channel_preferences: apiPrefs.channel_preferences,
        frequency_settings: apiPrefs.frequency_settings,
        notification_types: apiPrefs.notification_types,
        batch_options: apiPrefs.batch_options,
      });
      setSaveSuccess(true);
    } else {
      // Fallback to local defaults if API fails
      store.resetToDefaults(recipientId, recipientType);
      setSaveError('Failed to reset preferences on server');
    }
  }, [store, recipientId, recipientType]);

  return {
    preferences,
    availableTypes,
    isLoading,
    isSaving,
    saveError,
    saveSuccess,

    // Actions
    updateChannelPreference,
    toggleChannel,
    toggleType,
    updateTypeFrequency,
    updateBatchOption,
    save,
    resetToDefaults,
    clearSaveStatus: () => { setSaveSuccess(false); setSaveError(null); },
  };
}

/**
 * Dispatch-time preference checker.
 * Called by NotificationService before sending any notification.
 */
export function checkDispatchPreferences(
  recipientId: string,
  recipientType: RecipientType,
  notificationType: string,
  channel: NotificationChannel
): { shouldDispatch: boolean; frequency: NotificationFrequency } {
  const store = useNotificationPreferencesStore.getState();
  const prefs = store.getPreferences(recipientId, recipientType === 'customer' ? 'customer' : 'store_owner');

  // Channel disabled → skip
  if (!prefs.channel_preferences[channel]) {
    return { shouldDispatch: false, frequency: 'disabled' };
  }

  // Map dispatch notification types to preference categories
  const categoryMap: Record<string, string> = {
    // Customer mappings
    order_confirmed: 'order_updates',
    order_placed: 'order_updates',
    order_shipped: 'delivery_updates',
    order_delivered: 'delivery_updates',
    order_cancelled: 'order_updates',
    payment_success: 'order_updates',
    promotion: 'promotions',
    price_drop: 'promotions',
    styling_suggestion: 'style_recommendations',
    back_in_stock: 'restock_alerts',
    wishlist_available: 'restock_alerts',
    delivery_tracking: 'delivery_updates',
    // Owner mappings
    new_order: 'new_orders',
    status_update: 'status_updates',
    customer_inquiry: 'customer_inquiries',
  };

  const category = categoryMap[notificationType] || notificationType;

  // Type disabled → skip
  if (!prefs.notification_types.includes(category)) {
    return { shouldDispatch: false, frequency: 'disabled' };
  }

  // Check frequency
  const frequency = prefs.frequency_settings[category] ?? 'real_time';
  if (frequency === 'disabled') {
    return { shouldDispatch: false, frequency: 'disabled' };
  }

  return { shouldDispatch: true, frequency };
}

export default useNotificationPreferences;
