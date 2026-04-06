/**
 * CONFIT — PreferenceToggle Component
 * =====================================
 * Toggle switch for notification preferences with optimistic updates
 * and sync status indicator.
 */

import { useCallback } from 'react';
import { cn } from '@/lib/utils';
import { usePreferenceSync } from '@/hooks/usePreferenceSync';
import { SyncIndicator } from './SyncIndicator';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { AlertCircle, RefreshCw } from 'lucide-react';
import type { ChannelType, FrequencySetting } from '@/hooks/usePreferenceSync';

// ─────────────────────────────────────────────────────────────────────────────
// PREFERENCE TOGGLE
// ─────────────────────────────────────────────────────────────────────────────

interface PreferenceToggleProps {
  field: 'global_enabled' | `channels.${ChannelType}.enabled` | `notification_types.${string}.enabled`;
  label: string;
  description?: string;
  disabled?: boolean;
  recipientType: 'customer' | 'owner';
  className?: string;
}

export function PreferenceToggle({
  field,
  label,
  description,
  disabled = false,
  recipientType,
  className,
}: PreferenceToggleProps) {
  const {
    preferences,
    updatePreference,
    isPending,
    hasFailedOperations,
    syncError,
    clearError,
    retryFailedOperations,
  } = usePreferenceSync({
    recipientType,
  });
  
  // Get current value from preferences
  const getValue = useCallback(() => {
    if (field === 'global_enabled') {
      return preferences.global_enabled;
    }
    
    if (field.startsWith('channels.')) {
      const channel = field.split('.')[1] as ChannelType;
      return preferences.channels[channel]?.enabled ?? true;
    }
    
    if (field.startsWith('notification_types.')) {
      const type = field.split('.')[1];
      return preferences.notification_types[type]?.enabled ?? true;
    }
    
    return true;
  }, [field, preferences]);
  
  const value = getValue();
  
  // Handle toggle change
  const handleToggle = useCallback(
    (newValue: boolean) => {
      if (field === 'global_enabled') {
        updatePreference({ global_enabled: newValue });
      } else if (field.startsWith('channels.')) {
        const channel = field.split('.')[1] as ChannelType;
        updatePreference({
          channels: {
            ...preferences.channels,
            [channel]: {
              ...preferences.channels[channel],
              enabled: newValue,
            },
          },
        });
      } else if (field.startsWith('notification_types.')) {
        const type = field.split('.')[1];
        updatePreference({
          notification_types: {
            ...preferences.notification_types,
            [type]: {
              ...preferences.notification_types[type],
              enabled: newValue,
            },
          },
        });
      }
    },
    [field, preferences, updatePreference]
  );
  
  return (
    <div className={cn('preference-toggle', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <Label 
            htmlFor={field} 
            className={cn(
              'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
              disabled && 'opacity-50'
            )}
          >
            {label}
          </Label>
          {description && (
            <p className="text-sm text-muted-foreground mt-1">
              {description}
            </p>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <SyncIndicator 
            isPending={isPending}
            hasError={!!syncError || hasFailedOperations}
          />
          
          <Switch
            id={field}
            checked={value}
            onCheckedChange={handleToggle}
            disabled={disabled || isPending}
            aria-label={label}
          />
        </div>
      </div>
      
      {/* Error message */}
      {(syncError || hasFailedOperations) && (
        <div className="mt-2 flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>{syncError?.message || 'Some changes failed to sync'}</span>
          <button
            onClick={retryFailedOperations}
            className="ml-auto flex items-center gap-1 text-primary hover:underline"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FREQUENCY SELECTOR
// ─────────────────────────────────────────────────────────────────────────────

interface FrequencySelectorProps {
  channel: ChannelType;
  recipientType: 'customer' | 'owner';
  className?: string;
}

export function FrequencySelector({
  channel,
  recipientType,
  className,
}: FrequencySelectorProps) {
  const {
    preferences,
    updatePreference,
    isPending,
  } = usePreferenceSync({
    recipientType,
  });
  
  const frequency = preferences.channels[channel]?.frequency ?? 'real_time';
  const isEnabled = preferences.channels[channel]?.enabled ?? true;
  
  const handleFrequencyChange = useCallback(
    (newFrequency: FrequencySetting) => {
      updatePreference({
        channels: {
          ...preferences.channels,
          [channel]: {
            ...preferences.channels[channel],
            frequency: newFrequency,
          },
        },
      });
    },
    [channel, preferences, updatePreference]
  );
  
  const frequencyOptions: { value: FrequencySetting; label: string; description: string }[] = [
    { value: 'real_time', label: 'Real-time', description: 'Receive immediately' },
    { value: 'daily_digest', label: 'Daily digest', description: 'Once per day summary' },
    { value: 'weekly_summary', label: 'Weekly summary', description: 'Once per week summary' },
    { value: 'disabled', label: 'Disabled', description: 'Do not send' },
  ];
  
  return (
    <div className={cn('frequency-selector', className)}>
      <label className="text-sm font-medium mb-2 block">
        Delivery frequency
      </label>
      
      <div className="grid grid-cols-2 gap-2">
        {frequencyOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => handleFrequencyChange(option.value)}
            disabled={isPending || !isEnabled}
            className={cn(
              'flex flex-col items-start p-3 rounded-lg border text-left transition-colors',
              frequency === option.value
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50',
              (!isEnabled || isPending) && 'opacity-50 cursor-not-allowed'
            )}
          >
            <span className="font-medium text-sm">{option.label}</span>
            <span className="text-xs text-muted-foreground">{option.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NOTIFICATION TYPE TOGGLE
// ─────────────────────────────────────────────────────────────────────────────

interface NotificationTypeToggleProps {
  typeKey: string;
  label: string;
  description: string;
  recipientType: 'customer' | 'owner';
  channels?: ChannelType[];
  className?: string;
}

export function NotificationTypeToggle({
  typeKey,
  label,
  description,
  recipientType,
  channels,
  className,
}: NotificationTypeToggleProps) {
  const {
    preferences,
    updatePreference,
    isPending,
  } = usePreferenceSync({
    recipientType,
  });
  
  const isEnabled = preferences.notification_types[typeKey]?.enabled ?? true;
  
  const handleToggle = useCallback(
    (enabled: boolean) => {
      updatePreference({
        notification_types: {
          ...preferences.notification_types,
          [typeKey]: {
            ...preferences.notification_types[typeKey],
            enabled,
          },
        },
      });
    },
    [typeKey, preferences, updatePreference]
  );
  
  const handleChannelToggle = useCallback(
    (channel: ChannelType, enabled: boolean) => {
      const currentChannels = preferences.notification_types[typeKey]?.channels ?? {};
      
      updatePreference({
        notification_types: {
          ...preferences.notification_types,
          [typeKey]: {
            ...preferences.notification_types[typeKey],
            enabled: preferences.notification_types[typeKey]?.enabled ?? true,
            channels: {
              ...currentChannels,
              [channel]: { enabled },
            },
          },
        },
      });
    },
    [typeKey, preferences, updatePreference]
  );
  
  return (
    <div className={cn('notification-type-toggle', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <Label className="text-sm font-medium">{label}</Label>
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        </div>
        
        <Switch
          checked={isEnabled}
          onCheckedChange={handleToggle}
          disabled={isPending}
          aria-label={label}
        />
      </div>
      
      {/* Channel overrides */}
      {isEnabled && channels && channels.length > 0 && (
        <div className="mt-3 pl-4 border-l-2 border-border">
          <p className="text-xs text-muted-foreground mb-2">Channel overrides</p>
          <div className="flex flex-wrap gap-4">
            {channels.map((channel) => {
              const channelEnabled = preferences.notification_types[typeKey]?.channels?.[channel]?.enabled ?? true;
              
              return (
                <label
                  key={channel}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={channelEnabled}
                    onChange={(e) => handleChannelToggle(channel, e.target.checked)}
                    disabled={isPending}
                    className="rounded border-gray-300"
                  />
                  <span className="capitalize">{channel.replace('_', ' ')}</span>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// GLOBAL TOGGLE
// ─────────────────────────────────────────────────────────────────────────────

interface GlobalToggleProps {
  recipientType: 'customer' | 'owner';
  className?: string;
}

export function GlobalToggle({ recipientType, className }: GlobalToggleProps) {
  const {
    preferences,
    updatePreference,
    isPending,
    syncError,
    hasFailedOperations,
    retryFailedOperations,
  } = usePreferenceSync({
    recipientType,
  });
  
  const handleToggle = useCallback(
    (enabled: boolean) => {
      updatePreference({ global_enabled: enabled });
    },
    [updatePreference]
  );
  
  return (
    <div className={cn('global-toggle p-4 rounded-lg border-2', className)}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">
            {preferences.global_enabled ? 'Notifications enabled' : 'All notifications disabled'}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {preferences.global_enabled
              ? 'You will receive notifications based on your preferences below.'
              : 'Enable notifications to receive updates about your orders, promotions, and more.'}
          </p>
        </div>
        
        <Switch
          checked={preferences.global_enabled}
          onCheckedChange={handleToggle}
          disabled={isPending}
          aria-label="Enable all notifications"
          className="data-[state=checked]:bg-green-500 data-[state=unchecked]:bg-gray-300"
        />
      </div>
      
      {/* Error state */}
      {(syncError || hasFailedOperations) && (
        <div className="mt-3 p-2 bg-destructive/10 rounded text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          <span>Failed to save changes</span>
          <button
            onClick={retryFailedOperations}
            className="ml-auto underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

export default PreferenceToggle;
