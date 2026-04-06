/**
 * CONFIT — Alert Preferences Panel
 * ==================================
 * Settings panel for configuring alert thresholds, frequency, and types.
 * Accessible from dashboard settings.
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings,
  Bell,
  BellOff,
  DollarSign,
  RotateCcw,
  Package,
  TrendingUp,
  Users,
  Clock,
  AlertTriangle,
  Info,
  AlertCircle,
  Save,
  RotateCcw as ResetIcon,
  ChevronDown,
  ChevronUp,
  Check,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  type SalesAlertType,
  type AlertTypePreference,
  type AlertThresholdConfig,
  type AlertFrequencyConfig,
  DEFAULT_THRESHOLD_CONFIG,
  DEFAULT_FREQUENCY_CONFIG,
  DEFAULT_TYPE_PREFERENCES,
  getAlertTypeConfig,
} from '@/types/salesAlertTypes';
import { useSalesAlertStore } from '@/stores/salesAlertStore';
import { createTransition } from '@/motion';

// ─── Type Icon Map ────────────────────────────────────────────────────────────

const TYPE_ICONS: Record<SalesAlertType, React.ReactNode> = {
  high_value_order: <DollarSign className="h-4 w-4" />,
  unusual_returns: <RotateCcw className="h-4 w-4" />,
  inventory_depletion: <Package className="h-4 w-4" />,
  conversion_anomaly: <TrendingUp className="h-4 w-4" />,
  customer_segment_change: <Users className="h-4 w-4" />,
};

// ─── Frequency Options ────────────────────────────────────────────────────────

const FREQUENCY_OPTIONS = [
  { value: 'real_time', label: 'Real-time', description: 'Instant notification' },
  { value: 'batched_15m', label: 'Every 15 min', description: 'Batched delivery' },
  { value: 'batched_30m', label: 'Every 30 min', description: 'Batched delivery' },
  { value: 'batched_1h', label: 'Every hour', description: 'Batched delivery' },
  { value: 'disabled', label: 'Disabled', description: 'No notifications' },
];

// ─── Threshold Section Component ─────────────────────────────────────────────

interface ThresholdSectionProps {
  thresholds: AlertThresholdConfig;
  onChange: (thresholds: Partial<AlertThresholdConfig>) => void;
}

function ThresholdSection({ thresholds, onChange }: ThresholdSectionProps) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="border-0 bg-transparent shadow-none">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/30 rounded-lg p-4 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <Settings className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <CardTitle className="text-base">Alert Thresholds</CardTitle>
                  <CardDescription className="text-xs">
                    Configure when alerts are triggered
                  </CardDescription>
                </div>
              </div>
              <motion.div
                animate={{ rotate: open ? 180 : 0 }}
                transition={createTransition({ duration: 0.2 })}
              >
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              </motion.div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-6 pt-4">
            {/* High Value Order */}
            <div className="space-y-3">
              <Label className="text-sm font-medium flex items-center gap-2">
                {TYPE_ICONS.high_value_order}
                High-Value Order Threshold
              </Label>
              <p className="text-xs text-muted-foreground">
                Alert when order value exceeds AOV × multiplier
              </p>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    AOV Multiplier: {thresholds.high_value_aov_multiplier.toFixed(1)}x
                  </Label>
                  <Slider
                    value={[thresholds.high_value_aov_multiplier]}
                    onValueChange={([v]) => onChange({ high_value_aov_multiplier: v })}
                    min={1.1}
                    max={3}
                    step={0.1}
                    className="w-full"
                  />
                </div>
                <Input
                  type="number"
                  value={thresholds.high_value_aov_multiplier}
                  onChange={(e) => onChange({ high_value_aov_multiplier: parseFloat(e.target.value) || 1.5 })}
                  className="w-20 text-center"
                  step={0.1}
                  min={1}
                />
              </div>
            </div>

            {/* Inventory Threshold */}
            <div className="space-y-3">
              <Label className="text-sm font-medium flex items-center gap-2">
                {TYPE_ICONS.inventory_depletion}
                Inventory Threshold
              </Label>
              <p className="text-xs text-muted-foreground">
                Alert when stock drops below this level
              </p>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    Units: {thresholds.inventory_threshold_units}
                  </Label>
                  <Slider
                    value={[thresholds.inventory_threshold_units]}
                    onValueChange={([v]) => onChange({ inventory_threshold_units: v })}
                    min={1}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>
                <Input
                  type="number"
                  value={thresholds.inventory_threshold_units}
                  onChange={(e) => onChange({ inventory_threshold_units: parseInt(e.target.value) || 10 })}
                  className="w-20 text-center"
                  min={1}
                />
              </div>
            </div>

            {/* Conversion Anomaly */}
            <div className="space-y-3">
              <Label className="text-sm font-medium flex items-center gap-2">
                {TYPE_ICONS.conversion_anomaly}
                Conversion Anomaly Sensitivity
              </Label>
              <p className="text-xs text-muted-foreground">
                Alert when conversion rate deviates from baseline
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    Drop Threshold: {thresholds.conversion_drop_threshold_percent}%
                  </Label>
                  <Slider
                    value={[thresholds.conversion_drop_threshold_percent]}
                    onValueChange={([v]) => onChange({ conversion_drop_threshold_percent: v })}
                    min={5}
                    max={50}
                    step={5}
                    className="w-full"
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    Rise Threshold: {thresholds.conversion_rise_threshold_percent}%
                  </Label>
                  <Slider
                    value={[thresholds.conversion_rise_threshold_percent]}
                    onValueChange={([v]) => onChange({ conversion_rise_threshold_percent: v })}
                    min={10}
                    max={100}
                    step={5}
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Returns Pattern */}
            <div className="space-y-3">
              <Label className="text-sm font-medium flex items-center gap-2">
                {TYPE_ICONS.unusual_returns}
                Returns Pattern Detection
              </Label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    Spike Count (in {thresholds.returns_spike_window_hours}h)
                  </Label>
                  <Input
                    type="number"
                    value={thresholds.returns_spike_count}
                    onChange={(e) => onChange({ returns_spike_count: parseInt(e.target.value) || 5 })}
                    className="w-full"
                    min={1}
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    Rate Increase: {thresholds.returns_rate_increase_percent}%
                  </Label>
                  <Slider
                    value={[thresholds.returns_rate_increase_percent]}
                    onValueChange={([v]) => onChange({ returns_rate_increase_percent: v })}
                    min={20}
                    max={100}
                    step={10}
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Customer Segment */}
            <div className="space-y-3">
              <Label className="text-sm font-medium flex items-center gap-2">
                {TYPE_ICONS.customer_segment_change}
                Customer Inactivity Thresholds
              </Label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    VIP Inactive (days)
                  </Label>
                  <Input
                    type="number"
                    value={thresholds.vip_inactive_days}
                    onChange={(e) => onChange({ vip_inactive_days: parseInt(e.target.value) || 30 })}
                    className="w-full"
                    min={7}
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground mb-1.5 block">
                    Returning → Inactive (days)
                  </Label>
                  <Input
                    type="number"
                    value={thresholds.returning_to_inactive_days}
                    onChange={(e) => onChange({ returning_to_inactive_days: parseInt(e.target.value) || 60 })}
                    className="w-full"
                    min={14}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

// ─── Frequency Section Component ─────────────────────────────────────────────

interface FrequencySectionProps {
  frequency: AlertFrequencyConfig;
  onChange: (frequency: Partial<AlertFrequencyConfig>) => void;
}

function FrequencySection({ frequency, onChange }: FrequencySectionProps) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="border-0 bg-transparent shadow-none">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/30 rounded-lg p-4 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <Clock className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <CardTitle className="text-base">Frequency & Throttling</CardTitle>
                  <CardDescription className="text-xs">
                    Control how often you receive alerts
                  </CardDescription>
                </div>
              </div>
              <motion.div
                animate={{ rotate: open ? 180 : 0 }}
                transition={createTransition({ duration: 0.2 })}
              >
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              </motion.div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-6 pt-4">
            {/* Max Alerts Per Hour */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Maximum Alerts Per Hour</Label>
              <p className="text-xs text-muted-foreground">
                Prevent notification fatigue by limiting hourly alerts
              </p>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <Slider
                    value={[frequency.max_alerts_per_hour]}
                    onValueChange={([v]) => onChange({ max_alerts_per_hour: v })}
                    min={1}
                    max={50}
                    step={1}
                    className="w-full"
                  />
                </div>
                <Input
                  type="number"
                  value={frequency.max_alerts_per_hour}
                  onChange={(e) => onChange({ max_alerts_per_hour: parseInt(e.target.value) || 10 })}
                  className="w-20 text-center"
                  min={1}
                />
              </div>
            </div>

            {/* Deduplication Window */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Deduplication Window</Label>
              <p className="text-xs text-muted-foreground">
                Prevent duplicate alerts for the same event within this window
              </p>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <Slider
                    value={[frequency.dedup_window_minutes]}
                    onValueChange={([v]) => onChange({ dedup_window_minutes: v })}
                    min={15}
                    max={240}
                    step={15}
                    className="w-full"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={frequency.dedup_window_minutes}
                    onChange={(e) => onChange({ dedup_window_minutes: parseInt(e.target.value) || 60 })}
                    className="w-20 text-center"
                    min={15}
                  />
                  <span className="text-xs text-muted-foreground">min</span>
                </div>
              </div>
            </div>

            {/* Severity-Based Mode */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Delivery Mode by Severity</Label>
              <div className="grid grid-cols-3 gap-3">
                {(['critical', 'warning', 'info'] as const).map((severity) => {
                  const modeKey = `${severity}_mode` as keyof AlertFrequencyConfig;
                  const icons = {
                    critical: <AlertTriangle className="h-4 w-4 text-red-400" />,
                    warning: <AlertCircle className="h-4 w-4 text-amber-400" />,
                    info: <Info className="h-4 w-4 text-blue-400" />,
                  };
                  const colors = {
                    critical: 'bg-red-500/10 border-red-500/30',
                    warning: 'bg-amber-500/10 border-amber-500/30',
                    info: 'bg-blue-500/10 border-blue-500/30',
                  };

                  return (
                    <div key={severity} className={cn('p-3 rounded-lg border', colors[severity])}>
                      <div className="flex items-center gap-2 mb-2">
                        {icons[severity]}
                        <span className="text-xs font-medium capitalize">{severity}</span>
                      </div>
                      <Select
                        value={frequency[modeKey] as string}
                        onValueChange={(v) => onChange({ [modeKey]: v })}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="real_time">Real-time</SelectItem>
                          <SelectItem value="batched">Batched</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

// ─── Type Preferences Section ─────────────────────────────────────────────────

interface TypePreferencesSectionProps {
  preferences: Record<SalesAlertType, AlertTypePreference>;
  onChange: (type: SalesAlertType, pref: Partial<AlertTypePreference>) => void;
}

function TypePreferencesSection({ preferences, onChange }: TypePreferencesSectionProps) {
  const [open, setOpen] = useState(false);

  const types: SalesAlertType[] = [
    'high_value_order',
    'unusual_returns',
    'inventory_depletion',
    'conversion_anomaly',
    'customer_segment_change',
  ];

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="border-0 bg-transparent shadow-none">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/30 rounded-lg p-4 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                  <Bell className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <CardTitle className="text-base">Alert Types</CardTitle>
                  <CardDescription className="text-xs">
                    Enable/disable individual alert types
                  </CardDescription>
                </div>
              </div>
              <motion.div
                animate={{ rotate: open ? 180 : 0 }}
                transition={createTransition({ duration: 0.2 })}
              >
                <ChevronDown className="h-5 w-5 text-muted-foreground" />
              </motion.div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-4 pt-4">
            {types.map((type) => {
              const pref = preferences[type];
              const config = getAlertTypeConfig(type);

              return (
                <div
                  key={type}
                  className={cn(
                    'flex items-center justify-between p-4 rounded-lg border transition-colors',
                    pref.enabled ? 'bg-muted/20 border-border' : 'bg-muted/10 border-border/50 opacity-60'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'w-10 h-10 rounded-lg flex items-center justify-center',
                      pref.enabled ? 'bg-purple-500/10' : 'bg-muted'
                    )}>
                      {TYPE_ICONS[type]}
                    </div>
                    <div>
                      <h4 className="text-sm font-medium">{config.label}</h4>
                      <p className="text-xs text-muted-foreground">{config.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <Select
                      value={pref.frequency}
                      onValueChange={(v) => onChange(type, { frequency: v as AlertTypePreference['frequency'] })}
                      disabled={!pref.enabled}
                    >
                      <SelectTrigger className="w-[130px] h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {FREQUENCY_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Switch
                      checked={pref.enabled}
                      onCheckedChange={(enabled) => onChange(type, { enabled })}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

// ─── Main Preferences Panel ───────────────────────────────────────────────────

interface AlertPreferencesPanelProps {
  storeId: string;
  onSave?: () => void;
  className?: string;
}

export function AlertPreferencesPanel({ storeId, onSave, className }: AlertPreferencesPanelProps) {
  const store = useSalesAlertStore((s) => ({
    preferences: s.getPreferences(storeId),
    updateThresholds: (t) => s.updateThresholds(storeId, t),
    updateFrequency: (f) => s.updateFrequency(storeId, f),
    updateTypePreference: (type, pref) => s.updateTypePreference(storeId, type, pref),
    resetPreferencesToDefaults: () => s.resetPreferencesToDefaults(storeId),
  }));

  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleThresholdChange = (thresholds: Partial<AlertThresholdConfig>) => {
    store.updateThresholds(thresholds);
    setHasChanges(true);
  };

  const handleFrequencyChange = (frequency: Partial<AlertFrequencyConfig>) => {
    store.updateFrequency(frequency);
    setHasChanges(true);
  };

  const handleTypePreferenceChange = (type: SalesAlertType, pref: Partial<AlertTypePreference>) => {
    store.updateTypePreference(type, pref);
    setHasChanges(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate save delay
    await new Promise((r) => setTimeout(r, 500));
    setIsSaving(false);
    setHasChanges(false);
    onSave?.();
  };

  const handleReset = () => {
    store.resetPreferencesToDefaults();
    setHasChanges(true);
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Alert Preferences</h2>
          <p className="text-sm text-muted-foreground">
            Configure when and how you receive sales alerts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            className="gap-1"
          >
            <ResetIcon className="h-4 w-4" />
            Reset
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className="gap-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
          >
            {isSaving ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <RotateCcw className="h-4 w-4" />
                </motion.div>
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Status Banner */}
      {hasChanges && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg"
        >
          <AlertCircle className="h-4 w-4 text-amber-400" />
          <span className="text-sm text-amber-400">You have unsaved changes</span>
        </motion.div>
      )}

      {/* Sections */}
      <div className="space-y-2">
        <TypePreferencesSection
          preferences={store.preferences.type_preferences}
          onChange={handleTypePreferenceChange}
        />
        <ThresholdSection
          thresholds={store.preferences.thresholds}
          onChange={handleThresholdChange}
        />
        <FrequencySection
          frequency={store.preferences.frequency}
          onChange={handleFrequencyChange}
        />
      </div>

      {/* Throttling Status */}
      <Card className="bg-muted/30">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <Info className="h-4 w-4 text-blue-400" />
            </div>
            <div>
              <p className="text-sm font-medium">Current Throttling Status</p>
              <p className="text-xs text-muted-foreground">
                Max {store.preferences.frequency.max_alerts_per_hour} alerts/hour • 
                Dedup window: {store.preferences.frequency.dedup_window_minutes} min • 
                Critical: {store.preferences.frequency.critical_mode}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default AlertPreferencesPanel;
