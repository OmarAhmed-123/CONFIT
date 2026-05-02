/**
 * CONFIT — Alert Rules Configuration Dashboard
 * =============================================
 * A dedicated UI for store owners to customize their Real-Time Sales Alert System.
 * Features alert type toggles, threshold configuration, frequency preferences,
 * do-not-disturb windows, and live alert previews.
 */

import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Settings,
  Save,
  RotateCcw,
  AlertTriangle,
  Check,
  ChevronRight,
  Info,
  Sparkles,
  Clock,
  Moon,
  Zap,
  TrendingUp,
  Package,
  DollarSign,
  Users,
  RotateCcw as Returns,
  Shield,
  Eye,
  X,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { MainLayout } from '@/components/layout/MainLayout';
import { useAlertRules, type AlertFrequency, type SensitivityPreset } from '@/hooks/useAlertRules';
import { createTransition } from '@/motion';

type InventoryVelocityPreset = SensitivityPreset;
type DeliveryMode = AlertFrequency['delivery_mode'];

// ─── Constants ─────────────────────────────────────────────────────────────────

const ALERT_TYPE_CONFIG = {
  high_value_order: {
    icon: DollarSign,
    label: 'High-Value Orders',
    description: 'Orders exceeding your AOV threshold',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
  },
  unusual_returns: {
    icon: Returns,
    label: 'Unusual Return Patterns',
    description: 'Products with spike in returns',
    color: 'text-rose-400',
    bgColor: 'bg-rose-500/10',
    borderColor: 'border-rose-500/30',
  },
  inventory_depletion: {
    icon: Package,
    label: 'Inventory Depletion',
    description: 'Stock dropping below threshold',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
  },
  conversion_anomaly: {
    icon: TrendingUp,
    label: 'Conversion Anomalies',
    description: 'Significant rate changes',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
  customer_segment: {
    icon: Users,
    label: 'Customer Segment Changes',
    description: 'VIP/inactive status transitions',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
} as const;

const FREQUENCY_OPTIONS: { value: AlertFrequency; label: string; description: string }[] = [
  { value: 'real_time', label: 'Real-time', description: 'Instant notification' },
  { value: 'batched_15m', label: 'Every 15 min', description: 'Batched delivery' },
  { value: 'batched_30m', label: 'Every 30 min', description: 'Batched delivery' },
  { value: 'batched_1h', label: 'Every hour', description: 'Batched delivery' },
  { value: 'disabled', label: 'Disabled', description: 'No notifications' },
];

const SENSITIVITY_PRESETS: { value: SensitivityPreset; label: string; description: string; icon: typeof Zap }[] = [
  { value: 'conservative', label: 'Conservative', description: 'Fewer alerts, higher thresholds', icon: Shield },
  { value: 'moderate', label: 'Moderate', description: 'Balanced alert frequency', icon: Zap },
  { value: 'aggressive', label: 'Aggressive', description: 'More alerts, lower thresholds', icon: Sparkles },
];

const TIMEZONE_OPTIONS = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Paris (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
];

// ─── Sub-Components ───────────────────────────────────────────────────────────

interface AlertTypeCardProps {
  type: keyof typeof ALERT_TYPE_CONFIG;
  config: { enabled: boolean; frequency: AlertFrequency; channels: string[] };
  onChange: (config: { enabled?: boolean; frequency?: AlertFrequency; channels?: string[] }) => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

function AlertTypeCard({ type, config, onChange, isExpanded, onToggleExpand }: AlertTypeCardProps) {
  const typeConfig = ALERT_TYPE_CONFIG[type];
  const Icon = typeConfig.icon;
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={cn(
        "rounded-xl border transition-all duration-300",
        config.enabled ? typeConfig.borderColor : "border-border/50",
        config.enabled ? typeConfig.bgColor : "bg-card/50"
      )}
    >
      <Collapsible open={isExpanded} onOpenChange={onToggleExpand}>
        <CollapsibleTrigger asChild>
          <div className="p-4 cursor-pointer hover:bg-muted/30 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={cn(
                  "p-2.5 rounded-lg transition-colors",
                  config.enabled ? typeConfig.bgColor : "bg-muted/50"
                )}>
                  <Icon className={cn("h-5 w-5", config.enabled ? typeConfig.color : "text-muted-foreground")} />
                </div>
                <div>
                  <h3 className="font-medium text-sm">{typeConfig.label}</h3>
                  <p className="text-xs text-muted-foreground">{typeConfig.description}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                {config.enabled && (
                  <Badge variant="outline" className="text-xs">
                    {FREQUENCY_OPTIONS.find(f => f.value === config.frequency)?.label || config.frequency}
                  </Badge>
                )}
                <Switch
                  checked={config.enabled}
                  onCheckedChange={(enabled) => {
                    onChange({ enabled });
                    if (enabled) {
                      toast.success(`${typeConfig.label} alerts enabled`);
                    }
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-purple-600 data-[state=checked]:to-amber-500"
                />
              </div>
            </div>
          </div>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <div className="px-4 pb-4 pt-0 border-t border-border/30">
            <div className="pt-4 space-y-4">
              {/* Frequency Selection */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Notification Frequency</Label>
                <Select
                  value={config.frequency}
                  onValueChange={(value: AlertFrequency) => onChange({ frequency: value })}
                >
                  <SelectTrigger className="bg-background/50 border-border/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {FREQUENCY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div className="flex flex-col">
                          <span>{option.label}</span>
                          <span className="text-xs text-muted-foreground">{option.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Channel Selection */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Delivery Channels</Label>
                <div className="flex flex-wrap gap-2">
                  {['in_app', 'email', 'push'].map((channel) => (
                    <Badge
                      key={channel}
                      variant={config.channels.includes(channel) ? "default" : "outline"}
                      className={cn(
                        "cursor-pointer transition-all",
                        config.channels.includes(channel) && 
                          "bg-gradient-to-r from-purple-600 to-amber-500 text-white"
                      )}
                      onClick={() => {
                        const newChannels = config.channels.includes(channel)
                          ? config.channels.filter(c => c !== channel)
                          : [...config.channels, channel];
                        onChange({ channels: newChannels });
                      }}
                    >
                      {channel.replace('_', ' ').replace('app', 'App')}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </motion.div>
  );
}

interface ThresholdSliderProps {
  label: string;
  description: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  warning?: { message: string; severity: 'info' | 'warning' | 'critical' } | null;
}

function ThresholdSlider({
  label,
  description,
  value,
  onChange,
  min,
  max,
  step = 1,
  unit = '',
  warning,
}: ThresholdSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <Label className="text-sm font-medium">{label}</Label>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            min={min}
            max={max}
            step={step}
            className="w-20 h-8 text-center bg-background/50 border-border/50"
          />
          {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
        </div>
      </div>
      
      <Slider
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={min}
        max={max}
        step={step}
        className="w-full"
      />
      
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
      
      {warning && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className={cn(
            "flex items-start gap-2 p-2 rounded-lg text-xs",
            warning.severity === 'warning' && "bg-amber-500/10 text-amber-400",
            warning.severity === 'info' && "bg-blue-500/10 text-blue-400",
            warning.severity === 'critical' && "bg-red-500/10 text-red-400"
          )}
        >
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{warning.message}</span>
        </motion.div>
      )}
    </div>
  );
}

interface AlertPreviewProps {
  type: keyof typeof ALERT_TYPE_CONFIG;
  threshold: number;
}

function AlertPreview({ type, threshold }: AlertPreviewProps) {
  const config = ALERT_TYPE_CONFIG[type];
  const Icon = config.icon;
  
  const previewData = useMemo(() => {
    switch (type) {
      case 'high_value_order':
        return {
          title: `High-Value Order: $${(threshold * 150).toFixed(0)}`,
          preview: 'Customer: Jane D. | Order: #ORD-1234 | 3 items',
          severity: 'warning' as const,
        };
      case 'inventory_depletion':
        return {
          title: `Low Stock Alert: Premium Blazer`,
          preview: `Stock: ${threshold} units | Threshold: ${threshold} units | ~5 days to stockout`,
          severity: 'critical' as const,
        };
      case 'conversion_anomaly':
        return {
          title: `Conversion Drop: ${threshold}%`,
          preview: 'Current: 2.1% | Baseline: 2.8% | Sessions: 1,250',
          severity: 'warning' as const,
        };
      case 'unusual_returns':
        return {
          title: 'Unusual Return Pattern: Silk Dress',
          preview: `SKU: SD-001 | ${threshold}x normal returns | Rate: 15.2%`,
          severity: 'warning' as const,
        };
      case 'customer_segment':
        return {
          title: `VIP Customer Inactive: ${threshold} days`,
          preview: 'Customer: Sarah M. | Last purchase: 32 days ago | LTV: $2,450',
          severity: 'info' as const,
        };
      default:
        return { title: 'Alert Preview', preview: 'Preview data', severity: 'info' as const };
    }
  }, [type, threshold]);
  
  const severityStyles = {
    critical: 'border-l-red-500 bg-red-500/5',
    warning: 'border-l-amber-500 bg-amber-500/5',
    info: 'border-l-blue-500 bg-blue-500/5',
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "rounded-lg border border-l-4 p-3 transition-all",
        severityStyles[previewData.severity]
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn("p-1.5 rounded", config.bgColor)}>
          <Icon className={cn("h-4 w-4", config.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{previewData.title}</p>
          <p className="text-xs text-muted-foreground truncate">{previewData.preview}</p>
        </div>
        <Badge variant="outline" className="text-xs shrink-0">
          {previewData.severity}
        </Badge>
      </div>
    </motion.div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

interface AlertRulesConfigPageProps {
  storeId?: string;
}

export function AlertRulesConfigPage({ storeId = 'brand-1' }: AlertRulesConfigPageProps) {
  const [expandedType, setExpandedType] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('types');
  const [showPreview, setShowPreview] = useState(true);
  
  const {
    config,
    warnings,
    presets,
    isLoading,
    isSaving,
    isResetting,
    isDirty,
    hasChanges,
    updateAlertType,
    updateThresholds,
    updateFrequency,
    updateDND,
    applyPreset,
    save,
    reset,
    discardChanges,
  } = useAlertRules({ storeId });
  
  // Get warnings for specific fields
  const getFieldWarning = useCallback((field: string) => {
    const warning = warnings.find(w => w.field === field);
    return warning ? { message: warning.message, severity: warning.severity } : null;
  }, [warnings]);
  
  // Handle save
  const handleSave = useCallback(async () => {
    await save();
  }, [save]);
  
  // Handle reset
  const handleReset = useCallback(async () => {
    if (window.confirm('Reset all alert settings to recommended defaults? This cannot be undone.')) {
      await reset();
    }
  }, [reset]);
  
  // Handle preset application
  const handleApplyPreset = useCallback(async (preset: SensitivityPreset) => {
    await applyPreset(preset);
  }, [applyPreset]);
  
  // Loading state
  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-4">
            <div className="h-8 w-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground">Loading alert configuration...</p>
          </div>
        </div>
      </MainLayout>
    );
  }
  
  // Error state
  if (!config) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-4 text-center">
            <AlertTriangle className="h-12 w-12 text-amber-500" />
            <div>
              <h2 className="text-lg font-semibold">Unable to Load Configuration</h2>
              <p className="text-sm text-muted-foreground">Please try again or contact support.</p>
            </div>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </div>
      </MainLayout>
    );
  }
  
  return (
    <MainLayout>
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ duration: 0.4 })}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-amber-500/20 border border-purple-500/30">
                <Bell className="h-6 w-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Alert Rules Configuration</h1>
                <p className="text-sm text-muted-foreground">
                  Customize your Real-Time Sales Alert System with precision and control.
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {isDirty && (
                <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30">
                  Unsaved Changes
                </Badge>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowPreview(!showPreview)}
                className="gap-2"
              >
                <Eye className="h-4 w-4" />
                Preview
              </Button>
            </div>
          </div>
        </motion.div>
        
        {/* Main Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ duration: 0.4, delay: 0.1 })}
          className="grid grid-cols-1 lg:grid-cols-3 gap-6"
        >
          {/* Left Column - Configuration */}
          <div className="lg:col-span-2 space-y-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="types" className="gap-2">
                  <Bell className="h-4 w-4" />
                  Alert Types
                </TabsTrigger>
                <TabsTrigger value="thresholds" className="gap-2">
                  <Settings className="h-4 w-4" />
                  Thresholds
                </TabsTrigger>
                <TabsTrigger value="frequency" className="gap-2">
                  <Clock className="h-4 w-4" />
                  Delivery
                </TabsTrigger>
              </TabsList>
              
              {/* Alert Types Tab */}
              <TabsContent value="types" className="mt-6 space-y-4">
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-purple-400" />
                      Alert Type Toggles
                    </CardTitle>
                    <CardDescription>
                      Enable or disable specific alert types and configure their delivery preferences.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {(Object.keys(ALERT_TYPE_CONFIG) as Array<keyof typeof ALERT_TYPE_CONFIG>).map((type) => (
                      <AlertTypeCard
                        key={type}
                        type={type}
                        config={config[type]}
                        onChange={(updates) => updateAlertType(type, updates)}
                        isExpanded={expandedType === type}
                        onToggleExpand={() => setExpandedType(expandedType === type ? null : type)}
                      />
                    ))}
                  </CardContent>
                </Card>
              </TabsContent>
              
              {/* Thresholds Tab */}
              <TabsContent value="thresholds" className="mt-6 space-y-6">
                {/* Preset Selector */}
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Zap className="h-5 w-5 text-amber-400" />
                      Sensitivity Presets
                    </CardTitle>
                    <CardDescription>
                      Apply a preset configuration or customize individual thresholds.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-3">
                      {SENSITIVITY_PRESETS.map((preset) => (
                        <motion.button
                          key={preset.value}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => handleApplyPreset(preset.value)}
                          className={cn(
                            "flex flex-col items-center gap-2 p-4 rounded-xl border transition-all",
                            "hover:border-purple-500/50 hover:bg-purple-500/5",
                            config.thresholds.conversion_sensitivity_preset === preset.value && 
                              "border-purple-500/50 bg-purple-500/10"
                          )}
                        >
                          <preset.icon className="h-5 w-5 text-purple-400" />
                          <span className="text-sm font-medium">{preset.label}</span>
                          <span className="text-xs text-muted-foreground text-center">{preset.description}</span>
                        </motion.button>
                      ))}
                    </div>
                  </CardContent>
                </Card>
                
                {/* High-Value Orders */}
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3">
                      <DollarSign className="h-5 w-5 text-amber-400" />
                      <div>
                        <CardTitle className="text-lg">High-Value Orders</CardTitle>
                        <CardDescription>Configure thresholds for detecting significant orders.</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <ThresholdSlider
                      label="AOV Multiplier"
                      description="Alert when order value exceeds AOV × this multiplier"
                      value={config.thresholds.high_value_aov_multiplier}
                      onChange={(v) => updateThresholds({ high_value_aov_multiplier: v })}
                      min={1}
                      max={5}
                      step={0.1}
                      unit="×"
                      warning={getFieldWarning('high_value_aov_multiplier')}
                    />
                    <ThresholdSlider
                      label="Minimum Order Value"
                      description="Optional absolute minimum (leave 0 to use multiplier only)"
                      value={config.thresholds.high_value_min_order_value || 0}
                      onChange={(v) => updateThresholds({ high_value_min_order_value: v || null })}
                      min={0}
                      max={10000}
                      step={50}
                      unit="$"
                    />
                  </CardContent>
                </Card>
                
                {/* Inventory */}
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3">
                      <Package className="h-5 w-5 text-orange-400" />
                      <div>
                        <CardTitle className="text-lg">Inventory Depletion</CardTitle>
                        <CardDescription>Set stock level thresholds for low inventory alerts.</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <ThresholdSlider
                      label="Units Threshold"
                      description="Alert when stock falls below this number of units"
                      value={config.thresholds.inventory_threshold_units}
                      onChange={(v) => updateThresholds({ inventory_threshold_units: v })}
                      min={1}
                      max={100}
                      step={1}
                      unit="units"
                      warning={getFieldWarning('inventory_threshold_units')}
                    />
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Inventory Velocity</Label>
                      <Select
                        value={config.thresholds.inventory_velocity_preset}
                        onValueChange={(v) => updateThresholds({ inventory_velocity_preset: v as InventoryVelocityPreset })}
                      >
                        <SelectTrigger className="bg-background/50 border-border/50">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="fast_mover">Fast-moving (adjust thresholds lower)</SelectItem>
                          <SelectItem value="balanced">Balanced</SelectItem>
                          <SelectItem value="slow_mover">Slow-moving (adjust thresholds higher)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>
                
                {/* Conversion */}
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3">
                      <TrendingUp className="h-5 w-5 text-purple-400" />
                      <div>
                        <CardTitle className="text-lg">Conversion Anomalies</CardTitle>
                        <CardDescription>Detect significant changes in conversion rates.</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <ThresholdSlider
                      label="Drop Threshold"
                      description="Alert when conversion drops by this percentage"
                      value={config.thresholds.conversion_drop_threshold_percent}
                      onChange={(v) => updateThresholds({ conversion_drop_threshold_percent: v })}
                      min={5}
                      max={50}
                      step={1}
                      unit="%"
                      warning={getFieldWarning('conversion_drop_threshold_percent')}
                    />
                    <ThresholdSlider
                      label="Rise Threshold"
                      description="Alert when conversion increases by this percentage"
                      value={config.thresholds.conversion_rise_threshold_percent}
                      onChange={(v) => updateThresholds({ conversion_rise_threshold_percent: v })}
                      min={10}
                      max={100}
                      step={5}
                      unit="%"
                    />
                    <ThresholdSlider
                      label="Baseline Window"
                      description="Days to average for baseline calculation"
                      value={config.thresholds.conversion_baseline_days}
                      onChange={(v) => updateThresholds({ conversion_baseline_days: v })}
                      min={1}
                      max={30}
                      step={1}
                      unit="days"
                    />
                  </CardContent>
                </Card>
                
                {/* Customer Segments */}
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3">
                      <Users className="h-5 w-5 text-blue-400" />
                      <div>
                        <CardTitle className="text-lg">Customer Segments</CardTitle>
                        <CardDescription>Configure inactivity thresholds for customer segments.</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <ThresholdSlider
                      label="VIP Inactive Days"
                      description="Alert when VIP customer is inactive for this many days"
                      value={config.thresholds.vip_inactive_days}
                      onChange={(v) => updateThresholds({ vip_inactive_days: v })}
                      min={7}
                      max={180}
                      step={1}
                      unit="days"
                      warning={getFieldWarning('vip_inactive_days')}
                    />
                    <ThresholdSlider
                      label="Returning Customer Inactive Days"
                      description="Alert when returning customer becomes inactive"
                      value={config.thresholds.returning_inactive_days}
                      onChange={(v) => updateThresholds({ returning_inactive_days: v })}
                      min={14}
                      max={365}
                      step={1}
                      unit="days"
                      warning={getFieldWarning('returning_inactive_days')}
                    />
                  </CardContent>
                </Card>
              </TabsContent>
              
              {/* Frequency Tab */}
              <TabsContent value="frequency" className="mt-6 space-y-6">
                {/* Global Delivery */}
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Clock className="h-5 w-5 text-purple-400" />
                      Global Delivery Settings
                    </CardTitle>
                    <CardDescription>
                      Configure how alerts are delivered to you.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Delivery Mode</Label>
                      <Select
                        value={config.frequency.delivery_mode}
                        onValueChange={(v) => updateFrequency({ delivery_mode: v as DeliveryMode })}
                      >
                        <SelectTrigger className="bg-background/50 border-border/50">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="real_time">Real-time (instant delivery)</SelectItem>
                          <SelectItem value="hourly_digest">Hourly Digest</SelectItem>
                          <SelectItem value="daily_summary">Daily Summary</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <Separator />
                    
                    <ThresholdSlider
                      label="Max Alerts Per Hour"
                      description="Throttle to prevent notification fatigue"
                      value={config.frequency.max_alerts_per_hour}
                      onChange={(v) => updateFrequency({ max_alerts_per_hour: v })}
                      min={1}
                      max={100}
                      step={1}
                      unit="alerts"
                    />
                    
                    <ThresholdSlider
                      label="Deduplication Window"
                      description="Minutes before similar alerts are grouped"
                      value={config.frequency.dedup_window_minutes}
                      onChange={(v) => updateFrequency({ dedup_window_minutes: v })}
                      min={15}
                      max={480}
                      step={15}
                      unit="min"
                    />
                    
                    <Separator />
                    
                    <div className="space-y-4">
                      <Label className="text-sm font-medium">Severity-Based Delivery</Label>
                      <div className="grid grid-cols-3 gap-4">
                        {(['critical', 'warning', 'info'] as const).map((severity) => (
                          <div key={severity} className="space-y-2">
                            <Label className="text-xs text-muted-foreground capitalize">{severity}</Label>
                            <Select
                              value={config.frequency[`${severity}_delivery_mode` as keyof typeof config.frequency] as AlertFrequency}
                              onValueChange={(v) => updateFrequency({ [`${severity}_delivery_mode`]: v })}
                            >
                              <SelectTrigger className="bg-background/50 border-border/50 h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="real_time">Real-time</SelectItem>
                                <SelectItem value="batched_30m">Batched</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                {/* Do Not Disturb */}
                <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Moon className="h-5 w-5 text-indigo-400" />
                        <div>
                          <CardTitle className="text-lg">Do-Not-Disturb</CardTitle>
                          <CardDescription>Schedule quiet hours for non-critical alerts.</CardDescription>
                        </div>
                      </div>
                      <Switch
                        checked={config.do_not_disturb.enabled}
                        onCheckedChange={(enabled) => updateDND({ enabled })}
                        className="data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-purple-600 data-[state=checked]:to-indigo-500"
                      />
                    </div>
                  </CardHeader>
                  
                  <AnimatePresence>
                    {config.do_not_disturb.enabled && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={createTransition({ duration: 0.3 })}
                      >
                        <CardContent className="space-y-4 pt-4 border-t border-border/30">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label className="text-xs text-muted-foreground">Start Time</Label>
                              <Input
                                type="time"
                                value={config.do_not_disturb.start_time || '20:00'}
                                onChange={(e) => updateDND({ start_time: e.target.value })}
                                className="bg-background/50 border-border/50"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label className="text-xs text-muted-foreground">End Time</Label>
                              <Input
                                type="time"
                                value={config.do_not_disturb.end_time || '08:00'}
                                onChange={(e) => updateDND({ end_time: e.target.value })}
                                className="bg-background/50 border-border/50"
                              />
                            </div>
                          </div>
                          
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">Timezone</Label>
                            <Select
                              value={config.do_not_disturb.timezone}
                              onValueChange={(v) => updateDND({ timezone: v })}
                            >
                              <SelectTrigger className="bg-background/50 border-border/50">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {TIMEZONE_OPTIONS.map((tz) => (
                                  <SelectItem key={tz.value} value={tz.value}>
                                    {tz.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                            <div className="flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4 text-amber-400" />
                              <span className="text-sm">Allow critical alerts during DND</span>
                            </div>
                            <Switch
                              checked={config.do_not_disturb.allow_critical}
                              onCheckedChange={(allow_critical) => updateDND({ allow_critical })}
                              className="data-[state=checked]:bg-amber-500"
                            />
                          </div>
                        </CardContent>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
          
          {/* Right Column - Preview */}
          {showPreview && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={createTransition({ duration: 0.4, delay: 0.2 })}
              className="space-y-6"
            >
              {/* Live Preview Card */}
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm sticky top-4">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Eye className="h-5 w-5 text-purple-400" />
                    Live Preview
                  </CardTitle>
                  <CardDescription>
                    See how your alerts will appear.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(Object.keys(ALERT_TYPE_CONFIG) as Array<keyof typeof ALERT_TYPE_CONFIG>).map((type) => {
                    const typeConfig = config[type];
                    if (!typeConfig.enabled) return null;
                    
                    let threshold = 0;
                    switch (type) {
                      case 'high_value_order':
                        threshold = config.thresholds.high_value_aov_multiplier;
                        break;
                      case 'inventory_depletion':
                        threshold = config.thresholds.inventory_threshold_units;
                        break;
                      case 'conversion_anomaly':
                        threshold = config.thresholds.conversion_drop_threshold_percent;
                        break;
                      case 'unusual_returns':
                        threshold = config.thresholds.returns_spike_multiplier;
                        break;
                      case 'customer_segment':
                        threshold = config.thresholds.vip_inactive_days;
                        break;
                    }
                    
                    return (
                      <AlertPreview
                        key={type}
                        type={type}
                        threshold={threshold}
                      />
                    );
                  })}
                  
                  {Object.values(config).every((c: any) => !c?.enabled) && (
                    <div className="text-center py-8 text-muted-foreground">
                      <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No alerts enabled</p>
                      <p className="text-xs">Enable alert types to see previews</p>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Quick Stats */}
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Configuration Status</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Alerts Enabled</span>
                    <span className="font-medium">
                      {Object.values(ALERT_TYPE_CONFIG).filter((_, i) => {
                        const types = Object.keys(ALERT_TYPE_CONFIG) as Array<keyof typeof ALERT_TYPE_CONFIG>;
                        return config[types[i]]?.enabled;
                      }).length} / 5
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Customized</span>
                    <Badge variant={config.is_customized ? "default" : "outline"} className="text-xs">
                      {config.is_customized ? 'Yes' : 'Using Defaults'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">DND Active</span>
                    <Badge variant={config.do_not_disturb.enabled ? "default" : "outline"} className="text-xs">
                      {config.do_not_disturb.enabled ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </motion.div>
        
        {/* Footer Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ duration: 0.4, delay: 0.3 })}
          className="flex items-center justify-between pt-6 border-t border-border/50"
        >
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={isResetting}
              className="gap-2"
            >
              <RotateCcw className="h-4 w-4" />
              Reset to Defaults
            </Button>
            
            {isDirty && (
              <Button
                variant="ghost"
                onClick={discardChanges}
                className="text-muted-foreground"
              >
                Discard Changes
              </Button>
            )}
          </div>
          
          <div className="flex items-center gap-3">
            {warnings.length > 0 && (
              <div className="flex items-center gap-2 text-sm text-amber-400">
                <AlertCircle className="h-4 w-4" />
                <span>{warnings.length} suggestion{warnings.length !== 1 ? 's' : ''}</span>
              </div>
            )}
            
            <Button
              onClick={handleSave}
              disabled={!isDirty || isSaving}
              className={cn(
                "gap-2 min-w-[160px]",
                "bg-gradient-to-r from-purple-600 to-amber-500 hover:from-purple-700 hover:to-amber-600",
                "disabled:opacity-50 disabled:from-gray-400 disabled:to-gray-500"
              )}
            >
              {isSaving ? (
                <>
                  <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Configuration
                </>
              )}
            </Button>
          </div>
        </motion.div>
      </div>
    </MainLayout>
  );
}

export default AlertRulesConfigPage;
