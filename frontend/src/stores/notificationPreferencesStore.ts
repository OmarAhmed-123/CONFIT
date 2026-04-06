/**
 * CONFIT — Notification Preferences Store
 * ========================================
 * Per-user notification preferences with granular control:
 * - Per-channel enable/disable (in_app, email, push)
 * - Per-type frequency (real_time, daily_digest, weekly_summary, disabled)
 * - Owner-specific batch delivery options
 * - Dual persona support (customer / store_owner)
 *
 * Persisted to localStorage, keyed per-user.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// ─── Types ───

export type NotificationChannel = 'in_app' | 'email' | 'push';

export type NotificationFrequency = 'real_time' | 'daily_digest' | 'weekly_summary' | 'disabled';

export type RecipientType = 'customer' | 'store_owner';

// Customer notification categories
export type CustomerNotificationCategory =
  | 'order_updates'
  | 'delivery_updates'
  | 'promotions'
  | 'style_recommendations'
  | 'restock_alerts';

// Owner notification categories
export type OwnerNotificationCategory =
  | 'new_orders'
  | 'status_updates'
  | 'customer_inquiries';

export type NotificationCategory = CustomerNotificationCategory | OwnerNotificationCategory;

// ─── Preference Shapes ───

export interface ChannelPreferences {
  in_app: boolean;
  email: boolean;
  push: boolean;
}

export type FrequencySettings = Record<string, NotificationFrequency>;

export interface NotificationPreferences {
  recipient_id: string;
  recipient_type: RecipientType;
  channel_preferences: ChannelPreferences;
  frequency_settings: FrequencySettings;
  notification_types: string[];
  batch_options: {
    enabled: boolean;
  };
}

// ─── Default Factories ───

const CUSTOMER_TYPES: CustomerNotificationCategory[] = [
  'order_updates',
  'delivery_updates',
  'promotions',
  'style_recommendations',
  'restock_alerts',
];

const OWNER_TYPES: OwnerNotificationCategory[] = [
  'new_orders',
  'status_updates',
  'customer_inquiries',
];

export function getDefaultPreferences(
  recipientId: string,
  recipientType: RecipientType
): NotificationPreferences {
  const types =
    recipientType === 'customer' ? CUSTOMER_TYPES : OWNER_TYPES;

  const frequencySettings: FrequencySettings = {};
  for (const t of types) {
    frequencySettings[t] = 'real_time';
  }

  return {
    recipient_id: recipientId,
    recipient_type: recipientType,
    channel_preferences: {
      in_app: true,
      email: true,
      push: true,
    },
    frequency_settings: frequencySettings,
    notification_types: [...types],
    batch_options: {
      enabled: false,
    },
  };
}

export function getTypesForRecipient(recipientType: RecipientType): string[] {
  return recipientType === 'customer'
    ? [...CUSTOMER_TYPES]
    : [...OWNER_TYPES];
}

// ─── Store ───

interface PreferencesMap {
  [compositeKey: string]: NotificationPreferences;
}

function makeKey(recipientId: string, recipientType: RecipientType): string {
  return `${recipientType}::${recipientId}`;
}

interface NotificationPreferencesState {
  preferencesMap: PreferencesMap;

  // Core accessors
  getPreferences: (recipientId: string, recipientType: RecipientType) => NotificationPreferences;

  // Channel operations
  isChannelEnabled: (recipientId: string, recipientType: RecipientType, channel: NotificationChannel) => boolean;
  setChannelEnabled: (recipientId: string, recipientType: RecipientType, channel: NotificationChannel, enabled: boolean) => void;
  toggleChannel: (recipientId: string, recipientType: RecipientType, channel: NotificationChannel) => void;

  // Type operations
  isTypeEnabled: (recipientId: string, recipientType: RecipientType, type: string) => boolean;
  setTypeEnabled: (recipientId: string, recipientType: RecipientType, type: string, enabled: boolean) => void;
  toggleType: (recipientId: string, recipientType: RecipientType, type: string) => void;

  // Frequency operations
  getFrequencyForType: (recipientId: string, recipientType: RecipientType, type: string) => NotificationFrequency;
  setFrequencyForType: (recipientId: string, recipientType: RecipientType, type: string, frequency: NotificationFrequency) => void;

  // Batch (owner)
  isBatchEnabled: (recipientId: string, recipientType: RecipientType) => boolean;
  setBatchEnabled: (recipientId: string, recipientType: RecipientType, enabled: boolean) => void;

  // Save / reset
  savePreferences: (prefs: NotificationPreferences) => void;
  resetToDefaults: (recipientId: string, recipientType: RecipientType) => void;
}

export const useNotificationPreferencesStore = create<NotificationPreferencesState>()(
  persist(
    (set, get) => {
      // Helper: get or initialise preferences
      const resolve = (recipientId: string, recipientType: RecipientType): NotificationPreferences => {
        const key = makeKey(recipientId, recipientType);
        const existing = get().preferencesMap[key];
        if (existing) return existing;
        return getDefaultPreferences(recipientId, recipientType);
      };

      // Helper: upsert preferences
      const upsert = (prefs: NotificationPreferences) => {
        const key = makeKey(prefs.recipient_id, prefs.recipient_type);
        set((state) => ({
          preferencesMap: {
            ...state.preferencesMap,
            [key]: { ...prefs },
          },
        }));
      };

      return {
        preferencesMap: {},

        getPreferences: (recipientId, recipientType) =>
          resolve(recipientId, recipientType),

        // ── Channels ──

        isChannelEnabled: (recipientId, recipientType, channel) =>
          resolve(recipientId, recipientType).channel_preferences[channel],

        setChannelEnabled: (recipientId, recipientType, channel, enabled) => {
          const prefs = resolve(recipientId, recipientType);
          upsert({
            ...prefs,
            channel_preferences: {
              ...prefs.channel_preferences,
              [channel]: enabled,
            },
          });
        },

        toggleChannel: (recipientId, recipientType, channel) => {
          const prefs = resolve(recipientId, recipientType);
          upsert({
            ...prefs,
            channel_preferences: {
              ...prefs.channel_preferences,
              [channel]: !prefs.channel_preferences[channel],
            },
          });
        },

        // ── Types ──

        isTypeEnabled: (recipientId, recipientType, type) =>
          resolve(recipientId, recipientType).notification_types.includes(type),

        setTypeEnabled: (recipientId, recipientType, type, enabled) => {
          const prefs = resolve(recipientId, recipientType);
          const types = new Set(prefs.notification_types);
          if (enabled) types.add(type);
          else types.delete(type);
          upsert({
            ...prefs,
            notification_types: [...types],
          });
        },

        toggleType: (recipientId, recipientType, type) => {
          const prefs = resolve(recipientId, recipientType);
          const types = new Set(prefs.notification_types);
          if (types.has(type)) types.delete(type);
          else types.add(type);
          upsert({
            ...prefs,
            notification_types: [...types],
          });
        },

        // ── Frequency ──

        getFrequencyForType: (recipientId, recipientType, type) =>
          resolve(recipientId, recipientType).frequency_settings[type] ?? 'real_time',

        setFrequencyForType: (recipientId, recipientType, type, frequency) => {
          const prefs = resolve(recipientId, recipientType);
          upsert({
            ...prefs,
            frequency_settings: {
              ...prefs.frequency_settings,
              [type]: frequency,
            },
          });
        },

        // ── Batch ──

        isBatchEnabled: (recipientId, recipientType) =>
          resolve(recipientId, recipientType).batch_options.enabled,

        setBatchEnabled: (recipientId, recipientType, enabled) => {
          const prefs = resolve(recipientId, recipientType);
          upsert({
            ...prefs,
            batch_options: { ...prefs.batch_options, enabled },
          });
        },

        // ── Persistence ──

        savePreferences: (prefs) => upsert(prefs),

        resetToDefaults: (recipientId, recipientType) => {
          upsert(getDefaultPreferences(recipientId, recipientType));
        },
      };
    },
    {
      name: 'confit-notification-preferences',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ preferencesMap: state.preferencesMap }),
    }
  )
);
