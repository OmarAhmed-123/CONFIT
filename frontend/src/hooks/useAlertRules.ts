/**
 * CONFIT — Alert Rules Configuration Hook
 * =======================================
 * React hook for managing alert rules configuration with real-time validation.
 */

import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiUrl } from '@/lib/api';

// ─── Types ─────────────────────────────────────────────────────────────────────

export type AlertFrequency = 'real_time' | 'batched_15m' | 'batched_30m' | 'batched_1h' | 'disabled';
export type DeliveryMode = 'real_time' | 'hourly_digest' | 'daily_summary';
export type SensitivityPreset = 'conservative' | 'moderate' | 'aggressive';
export type InventoryVelocityPreset = 'fast_mover' | 'balanced' | 'slow_mover';

export interface AlertTypeConfig {
  enabled: boolean;
  frequency: AlertFrequency;
  channels: string[];
}

export interface ThresholdConfig {
  // High-Value Orders
  high_value_aov_multiplier: number;
  high_value_min_order_value: number | null;
  
  // Inventory
  inventory_threshold_units: number;
  inventory_threshold_percent: number;
  inventory_velocity_preset: InventoryVelocityPreset;
  
  // Conversion
  conversion_drop_threshold_percent: number;
  conversion_rise_threshold_percent: number;
  conversion_baseline_days: number;
  conversion_sensitivity_preset: SensitivityPreset;
  
  // Returns
  returns_spike_multiplier: number;
  returns_spike_window_hours: number;
  returns_sensitivity_preset: SensitivityPreset;
  
  // Customer Segment
  vip_inactive_days: number;
  returning_inactive_days: number;
  customer_sensitivity_preset: SensitivityPreset;
}

export interface DoNotDisturbConfig {
  enabled: boolean;
  start_time: string | null; // "HH:MM" format
  end_time: string | null;
  timezone: string;
  allow_critical: boolean;
}

export interface FrequencyConfig {
  delivery_mode: DeliveryMode;
  max_alerts_per_hour: number;
  max_alerts_per_day: number;
  dedup_window_minutes: number;
  critical_delivery_mode: AlertFrequency;
  warning_delivery_mode: AlertFrequency;
  info_delivery_mode: AlertFrequency;
}

export interface AlertRulesConfig {
  store_id: string;
  
  // Alert type toggles
  high_value_order: AlertTypeConfig;
  unusual_returns: AlertTypeConfig;
  inventory_depletion: AlertTypeConfig;
  conversion_anomaly: AlertTypeConfig;
  customer_segment: AlertTypeConfig;
  
  // Configuration sections
  thresholds: ThresholdConfig;
  frequency: FrequencyConfig;
  do_not_disturb: DoNotDisturbConfig;
  
  // Metadata
  is_customized: boolean;
  version: number;
}

export interface ValidationWarning {
  field: string;
  message: string;
  current_value: number;
  benchmark_value: number;
  severity: 'info' | 'warning' | 'critical';
}

export interface AlertRulesResponse {
  success: boolean;
  data: AlertRulesConfig | null;
  warnings: ValidationWarning[];
  error?: string;
}

export interface PresetInfo {
  label: string;
  description: string;
  values: Record<string, string | number>;
}

// ─── Default Configurations ────────────────────────────────────────────────────

export const DEFAULT_ALERT_TYPE_CONFIG: AlertTypeConfig = {
  enabled: true,
  frequency: 'real_time',
  channels: ['in_app'],
};

export const DEFAULT_THRESHOLDS: ThresholdConfig = {
  high_value_aov_multiplier: 1.5,
  high_value_min_order_value: null,
  inventory_threshold_units: 10,
  inventory_threshold_percent: 20,
  inventory_velocity_preset: 'balanced',
  conversion_drop_threshold_percent: 15,
  conversion_rise_threshold_percent: 20,
  conversion_baseline_days: 7,
  conversion_sensitivity_preset: 'moderate',
  returns_spike_multiplier: 3,
  returns_spike_window_hours: 24,
  returns_sensitivity_preset: 'moderate',
  vip_inactive_days: 30,
  returning_inactive_days: 45,
  customer_sensitivity_preset: 'moderate',
};

export const DEFAULT_FREQUENCY_CONFIG: FrequencyConfig = {
  delivery_mode: 'real_time',
  max_alerts_per_hour: 10,
  max_alerts_per_day: 50,
  dedup_window_minutes: 60,
  critical_delivery_mode: 'real_time',
  warning_delivery_mode: 'batched_30m',
  info_delivery_mode: 'batched_1h',
};

export const DEFAULT_DND_CONFIG: DoNotDisturbConfig = {
  enabled: false,
  start_time: null,
  end_time: null,
  timezone: 'UTC',
  allow_critical: true,
};

// ─── Hook Interface ────────────────────────────────────────────────────────────

interface UseAlertRulesOptions {
  storeId: string;
  enabled?: boolean;
}

interface UseAlertRulesReturn {
  // Data
  config: AlertRulesConfig | null;
  warnings: ValidationWarning[];
  presets: Record<string, PresetInfo>;
  
  // Loading states
  isLoading: boolean;
  isSaving: boolean;
  isResetting: boolean;
  error: string | null;
  
  // Dirty state tracking
  isDirty: boolean;
  hasChanges: (section?: string) => boolean;
  
  // Actions
  updateAlertType: (type: keyof Pick<AlertRulesConfig, 'high_value_order' | 'unusual_returns' | 'inventory_depletion' | 'conversion_anomaly' | 'customer_segment'>, config: Partial<AlertTypeConfig>) => void;
  updateThresholds: (thresholds: Partial<ThresholdConfig>) => void;
  updateFrequency: (frequency: Partial<FrequencyConfig>) => void;
  updateDND: (dnd: Partial<DoNotDisturbConfig>) => void;
  applyPreset: (presetType: SensitivityPreset) => Promise<void>;
  save: () => Promise<void>;
  reset: () => Promise<void>;
  refresh: () => Promise<void>;
  discardChanges: () => void;
}

// ─── Helper Functions ──────────────────────────────────────────────────────────

function getAuthToken(): string | null {
  return localStorage.getItem('confit_token');
}

async function fetchAlertRules(storeId: string): Promise<AlertRulesResponse> {
  const token = getAuthToken();
  const response = await fetch(apiUrl(`/api/alert-rules/${storeId}`), {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch alert rules' }));
    throw new Error(error.detail || 'Failed to fetch alert rules');
  }
  
  return response.json();
}

async function updateAlertRules(storeId: string, data: Partial<AlertRulesConfig>, version: number): Promise<AlertRulesResponse> {
  const token = getAuthToken();
  const response = await fetch(apiUrl(`/api/alert-rules/${storeId}`), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      ...data,
      version,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update alert rules' }));
    if (response.status === 409) {
      throw new Error('Configuration was modified by another session. Please refresh and try again.');
    }
    throw new Error(error.detail || 'Failed to update alert rules');
  }
  
  return response.json();
}

async function resetAlertRules(storeId: string): Promise<AlertRulesResponse> {
  const token = getAuthToken();
  const response = await fetch(apiUrl(`/api/alert-rules/${storeId}/reset`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to reset alert rules' }));
    throw new Error(error.detail || 'Failed to reset alert rules');
  }
  
  return response.json();
}

async function applyPresetToAlertRules(storeId: string, presetType: SensitivityPreset): Promise<AlertRulesResponse> {
  const token = getAuthToken();
  const response = await fetch(apiUrl(`/api/alert-rules/${storeId}/apply-preset`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ preset_type: presetType }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to apply preset' }));
    throw new Error(error.detail || 'Failed to apply preset');
  }
  
  return response.json();
}

async function fetchPresets(storeId: string): Promise<Record<string, PresetInfo>> {
  const token = getAuthToken();
  const response = await fetch(apiUrl(`/api/alert-rules/${storeId}/presets`), {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  
  if (!response.ok) {
    return {};
  }
  
  return response.json();
}

// ─── Hook Implementation ──────────────────────────────────────────────────────

export function useAlertRules({ storeId, enabled = true }: UseAlertRulesOptions): UseAlertRulesReturn {
  const queryClient = useQueryClient();
  
  // Local state for optimistic updates
  const [localConfig, setLocalConfig] = useState<AlertRulesConfig | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  
  // Fetch config
  const {
    data: response,
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: ['alert-rules', storeId],
    queryFn: () => fetchAlertRules(storeId),
    enabled: enabled && !!storeId,
    staleTime: 30000, // 30 seconds
  });
  
  // Fetch presets
  const { data: presets = {} } = useQuery({
    queryKey: ['alert-rules-presets', storeId],
    queryFn: () => fetchPresets(storeId),
    enabled: enabled && !!storeId,
    staleTime: 300000, // 5 minutes
  });
  
  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (data: { config: Partial<AlertRulesConfig>; version: number }) =>
      updateAlertRules(storeId, data.config, data.version),
    onSuccess: (data) => {
      if (data.success && data.data) {
        setLocalConfig(data.data);
        setIsDirty(false);
        queryClient.setQueryData(['alert-rules', storeId], data);
        toast.success('Alert configuration saved successfully');
        
        if (data.warnings.length > 0) {
          data.warnings.forEach((w) => {
            if (w.severity === 'warning') {
              toast.warning(w.message);
            } else {
              toast.info(w.message);
            }
          });
        }
      }
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });
  
  // Reset mutation
  const resetMutation = useMutation({
    mutationFn: () => resetAlertRules(storeId),
    onSuccess: (data) => {
      if (data.success && data.data) {
        setLocalConfig(data.data);
        setIsDirty(false);
        queryClient.setQueryData(['alert-rules', storeId], data);
        toast.success('Alert configuration reset to defaults');
      }
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });
  
  // Apply preset mutation
  const applyPresetMutation = useMutation({
    mutationFn: (presetType: SensitivityPreset) => applyPresetToAlertRules(storeId, presetType),
    onSuccess: (data) => {
      if (data.success && data.data) {
        setLocalConfig(data.data);
        setIsDirty(false);
        queryClient.setQueryData(['alert-rules', storeId], data);
        toast.success('Preset applied successfully');
      }
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });
  
  // Sync local config with server config
  useEffect(() => {
    if (response?.data && !isDirty) {
      setLocalConfig(response.data);
    }
  }, [response?.data, isDirty]);
  
  // Update functions
  const updateAlertType = useCallback((
    type: keyof Pick<AlertRulesConfig, 'high_value_order' | 'unusual_returns' | 'inventory_depletion' | 'conversion_anomaly' | 'customer_segment'>,
    config: Partial<AlertTypeConfig>
  ) => {
    if (!localConfig) return;
    
    setLocalConfig((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        [type]: { ...prev[type], ...config },
      };
    });
    setIsDirty(true);
  }, [localConfig]);
  
  const updateThresholds = useCallback((thresholds: Partial<ThresholdConfig>) => {
    if (!localConfig) return;
    
    setLocalConfig((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        thresholds: { ...prev.thresholds, ...thresholds },
      };
    });
    setIsDirty(true);
  }, [localConfig]);
  
  const updateFrequency = useCallback((frequency: Partial<FrequencyConfig>) => {
    if (!localConfig) return;
    
    setLocalConfig((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        frequency: { ...prev.frequency, ...frequency },
      };
    });
    setIsDirty(true);
  }, [localConfig]);
  
  const updateDND = useCallback((dnd: Partial<DoNotDisturbConfig>) => {
    if (!localConfig) return;
    
    setLocalConfig((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        do_not_disturb: { ...prev.do_not_disturb, ...dnd },
      };
    });
    setIsDirty(true);
  }, [localConfig]);
  
  // Save function
  const save = useCallback(async () => {
    if (!localConfig || !isDirty) return;
    
    // Build the update payload
    const updatePayload: Partial<AlertRulesConfig> = {
      high_value_order: localConfig.high_value_order,
      unusual_returns: localConfig.unusual_returns,
      inventory_depletion: localConfig.inventory_depletion,
      conversion_anomaly: localConfig.conversion_anomaly,
      customer_segment: localConfig.customer_segment,
      thresholds: localConfig.thresholds,
      frequency: localConfig.frequency,
      do_not_disturb: localConfig.do_not_disturb,
    };
    
    await saveMutation.mutateAsync({
      config: updatePayload,
      version: localConfig.version,
    });
  }, [localConfig, isDirty, saveMutation]);
  
  // Reset function
  const reset = useCallback(async () => {
    await resetMutation.mutateAsync();
  }, [resetMutation]);
  
  // Apply preset function
  const applyPreset = useCallback(async (presetType: SensitivityPreset) => {
    await applyPresetMutation.mutateAsync(presetType);
  }, [applyPresetMutation]);
  
  // Refresh function
  const refresh = useCallback(async () => {
    setIsDirty(false);
    await refetch();
  }, [refetch]);
  
  // Discard changes
  const discardChanges = useCallback(() => {
    if (response?.data) {
      setLocalConfig(response.data);
      setIsDirty(false);
    }
  }, [response?.data]);
  
  // Check for changes in specific section
  const hasChanges = useCallback((section?: string): boolean => {
    if (!isDirty || !localConfig || !response?.data) return false;
    
    if (!section) return isDirty;
    
    switch (section) {
      case 'thresholds':
        return JSON.stringify(localConfig.thresholds) !== JSON.stringify(response.data.thresholds);
      case 'frequency':
        return JSON.stringify(localConfig.frequency) !== JSON.stringify(response.data.frequency);
      case 'dnd':
        return JSON.stringify(localConfig.do_not_disturb) !== JSON.stringify(response.data.do_not_disturb);
      case 'types':
        const types = ['high_value_order', 'unusual_returns', 'inventory_depletion', 'conversion_anomaly', 'customer_segment'] as const;
        return types.some(t => JSON.stringify(localConfig[t]) !== JSON.stringify(response.data[t]));
      default:
        return isDirty;
    }
  }, [isDirty, localConfig, response?.data]);
  
  return {
    config: localConfig,
    warnings: response?.warnings ?? [],
    presets,
    
    isLoading,
    isSaving: saveMutation.isPending,
    isResetting: resetMutation.isPending,
    error: queryError?.message ?? null,
    
    isDirty,
    hasChanges,
    
    updateAlertType,
    updateThresholds,
    updateFrequency,
    updateDND,
    applyPreset,
    save,
    reset,
    refresh,
    discardChanges,
  };
}

export default useAlertRules;
