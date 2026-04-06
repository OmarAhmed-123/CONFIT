/**
 * CONFIT — Notification Preferences
 * ===================================
 * Comprehensive preferences interface for customers and store owners.
 * Dual-view: customer types/frequency vs. owner types/frequency + batch.
 * Luxury dark theme with gold accents, micro-animations, glass surfaces.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Mail,
  Smartphone,
  Monitor,
  Package,
  Tag,
  Sparkles,
  RefreshCw,
  Zap,
  Calendar,
  CalendarDays,
  RotateCcw,
  Save,
  CheckCircle,
  XCircle,
  ShoppingBag,
  TrendingUp,
  MessageSquare,
  Layers,
  ChevronDown,
  Loader2,
  Ban,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useNotificationPreferences } from '@/hooks/useNotificationPreferences';
import { ResetConfirmDialog } from './ResetConfirmDialog';
import type {
  NotificationChannel,
  NotificationFrequency,
  RecipientType,
} from '@/stores/notificationPreferencesStore';

// ─── Toggle Switch ───

function ToggleSwitch({
  enabled,
  onToggle,
  label,
  description,
  icon,
  id,
}: {
  enabled: boolean;
  onToggle: () => void;
  label: string;
  description: string;
  icon: React.ReactNode;
  id?: string;
}) {
  return (
    <motion.div
      layout
      className="flex items-center justify-between p-4 border border-border rounded-xl hover:bg-muted/20 transition-all duration-200"
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300',
            enabled
              ? 'bg-accent/15 text-accent shadow-[0_0_12px_rgba(212,175,55,0.15)]'
              : 'bg-muted text-muted-foreground'
          )}
        >
          {icon}
        </div>
        <div>
          <p className="font-medium text-sm">{label}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        id={id || `toggle-${label.toLowerCase().replace(/\s+/g, '-')}`}
        aria-checked={enabled ? "true" : "false"}
        aria-label={`Toggle ${label}`}
        onClick={onToggle}
        className={cn(
          'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2',
          enabled ? 'bg-accent' : 'bg-muted'
        )}
      >
        <motion.span
          layout
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          className={cn(
            'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg',
            enabled ? 'translate-x-5' : 'translate-x-0'
          )}
        />
      </button>
    </motion.div>
  );
}

// ─── Frequency Selector ───

const FREQUENCY_OPTIONS: {
  value: NotificationFrequency;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
}[] = [
  {
    value: 'real_time',
    label: 'Real-Time',
    shortLabel: 'Real-Time',
    icon: <Zap className="h-3.5 w-3.5" />,
  },
  {
    value: 'daily_digest',
    label: 'Daily Digest',
    shortLabel: 'Daily',
    icon: <Calendar className="h-3.5 w-3.5" />,
  },
  {
    value: 'weekly_summary',
    label: 'Weekly Summary',
    shortLabel: 'Weekly',
    icon: <CalendarDays className="h-3.5 w-3.5" />,
  },
  {
    value: 'disabled',
    label: 'Disabled',
    shortLabel: 'Off',
    icon: <Ban className="h-3.5 w-3.5" />,
  },
];

function FrequencyDropdown({
  value,
  onChange,
  id,
}: {
  value: NotificationFrequency;
  onChange: (v: NotificationFrequency) => void;
  id?: string;
}) {
  const [open, setOpen] = useState(false);
  const selected = FREQUENCY_OPTIONS.find((o) => o.value === value) || FREQUENCY_OPTIONS[0];

  return (
    <div className="relative">
      <button
        type="button"
        id={id}
        onClick={() => setOpen(!open)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all',
          value === 'disabled'
            ? 'border-destructive/30 text-destructive/80 bg-destructive/5'
            : 'border-border text-foreground bg-card hover:border-accent/40'
        )}
      >
        {selected.icon}
        <span>{selected.shortLabel}</span>
        <ChevronDown
          className={cn(
            'h-3 w-3 transition-transform',
            open && 'rotate-180'
          )}
        />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-full mt-1 z-50 w-48 rounded-xl border border-border bg-card shadow-xl overflow-hidden"
            >
              {FREQUENCY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-3 py-2.5 text-xs text-left transition-colors',
                    opt.value === value
                      ? 'bg-accent/10 text-accent font-medium'
                      : 'text-foreground hover:bg-muted/50'
                  )}
                >
                  {opt.icon}
                  <div>
                    <p className="font-medium">{opt.label}</p>
                  </div>
                  {opt.value === value && (
                    <CheckCircle className="h-3.5 w-3.5 ml-auto text-accent" />
                  )}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Type Config ───

interface TypeConfig {
  key: string;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const CUSTOMER_TYPE_CONFIG: TypeConfig[] = [
  {
    key: 'order_updates',
    label: 'Order Updates',
    description: 'Status changes, shipping, and delivery updates',
    icon: <Package className="h-5 w-5" />,
  },
  {
    key: 'delivery_updates',
    label: 'Delivery Updates',
    description: 'Real-time tracking and delivery notifications',
    icon: <Package className="h-5 w-5" />,
  },
  {
    key: 'promotions',
    label: 'Promotional Alerts',
    description: 'Sales, discounts, and exclusive offers',
    icon: <Tag className="h-5 w-5" />,
  },
  {
    key: 'style_recommendations',
    label: 'Style Recommendations',
    description: 'AI-curated looks and trending styles',
    icon: <Sparkles className="h-5 w-5" />,
  },
  {
    key: 'restock_alerts',
    label: 'Restock Alerts',
    description: 'Notify when sold-out items are available again',
    icon: <RefreshCw className="h-5 w-5" />,
  },
];

const OWNER_TYPE_CONFIG: TypeConfig[] = [
  {
    key: 'new_orders',
    label: 'New Orders',
    description: 'Instant alerts when new orders are placed',
    icon: <ShoppingBag className="h-5 w-5" />,
  },
  {
    key: 'status_updates',
    label: 'Order Status Updates',
    description: 'Shipping, delivery, and return status changes',
    icon: <TrendingUp className="h-5 w-5" />,
  },
  {
    key: 'customer_inquiries',
    label: 'Customer Inquiries',
    description: 'Messages, questions, and support requests',
    icon: <MessageSquare className="h-5 w-5" />,
  },
];

// ─── Channel Config ───

const CHANNEL_CONFIG: {
  key: NotificationChannel;
  label: string;
  description: string;
  icon: React.ReactNode;
}[] = [
  {
    key: 'in_app',
    label: 'In-App Notifications',
    description: 'See updates in the notification center and toasts',
    icon: <Monitor className="h-5 w-5" />,
  },
  {
    key: 'email',
    label: 'Email Notifications',
    description: 'Receive order confirmations and updates via email',
    icon: <Mail className="h-5 w-5" />,
  },
  {
    key: 'push',
    label: 'Push Notifications',
    description: 'Get instant alerts on your device',
    icon: <Smartphone className="h-5 w-5" />,
  },
];

// ─── Section Wrapper ───

function Section({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-card rounded-2xl border border-border p-6 hover:border-border/80 transition-colors"
    >
      <div className="flex items-center gap-2.5 mb-1">
        <div className="text-accent">{icon}</div>
        <h2 className="font-display font-semibold text-base">{title}</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-5">{description}</p>
      {children}
    </motion.div>
  );
}

// ─── Main Component ───

interface NotificationPreferencesProps {
  recipientId: string;
  recipientType: RecipientType;
}

export function NotificationPreferences({
  recipientId,
  recipientType,
}: NotificationPreferencesProps) {
  const {
    preferences,
    isLoading,
    isSaving,
    saveError,
    saveSuccess,
    toggleChannel,
    toggleType,
    updateTypeFrequency,
    updateBatchOption,
    save,
    resetToDefaults,
    clearSaveStatus,
  } = useNotificationPreferences({ recipientId, recipientType });

  const [showResetDialog, setShowResetDialog] = useState(false);

  const typeConfig =
    recipientType === 'customer' ? CUSTOMER_TYPE_CONFIG : OWNER_TYPE_CONFIG;

  const handleSave = useCallback(async () => {
    clearSaveStatus();
    await save();
    if (!saveError) {
      toast.success('Preferences saved successfully');
    }
  }, [save, clearSaveStatus, saveError]);

  const handleReset = useCallback(async () => {
    await resetToDefaults();
    setShowResetDialog(false);
    toast.success('Preferences reset to defaults');
  }, [resetToDefaults]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
        <span className="ml-3 text-muted-foreground">Loading preferences...</span>
      </div>
    );
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        {/* ═══ Channel Toggles ═══ */}
        <Section
          icon={<Bell className="h-5 w-5" />}
          title="Notification Channels"
          description="Choose how you want to receive notifications"
        >
          <div className="space-y-3">
            {CHANNEL_CONFIG.map((ch) => (
              <ToggleSwitch
                key={ch.key}
                id={`channel-${ch.key}`}
                enabled={preferences.channel_preferences[ch.key]}
                onToggle={() => toggleChannel(ch.key)}
                label={ch.label}
                description={ch.description}
                icon={ch.icon}
              />
            ))}
          </div>
        </Section>

        {/* ═══ Notification Types with Per-Type Frequency ═══ */}
        <Section
          icon={<Tag className="h-5 w-5" />}
          title="Notification Types & Frequency"
          description="Select which notifications you'd like to receive and how often"
        >
          <div className="space-y-3">
            <AnimatePresence initial={false}>
              {typeConfig.map((tp) => {
                const isEnabled = preferences.notification_types.includes(tp.key);
                const frequency = preferences.frequency_settings[tp.key] ?? 'real_time';

                return (
                  <motion.div
                    key={tp.key}
                    layout
                    className="border border-border rounded-xl overflow-hidden transition-colors hover:bg-muted/10"
                  >
                    {/* Type toggle row */}
                    <div className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            'w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300',
                            isEnabled
                              ? 'bg-accent/15 text-accent shadow-[0_0_12px_rgba(212,175,55,0.15)]'
                              : 'bg-muted text-muted-foreground'
                          )}
                        >
                          {tp.icon}
                        </div>
                        <div>
                          <p className="font-medium text-sm">{tp.label}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">{tp.description}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {/* Frequency dropdown (visible only when enabled) */}
                        {isEnabled && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                          >
                            <FrequencyDropdown
                              id={`freq-${tp.key}`}
                              value={frequency}
                              onChange={(v) => updateTypeFrequency(tp.key, v)}
                            />
                          </motion.div>
                        )}

                        {/* Toggle */}
                        <button
                          type="button"
                          role="switch"
                          id={`type-toggle-${tp.key}`}
                          aria-checked={isEnabled ? "true" : "false"}
                          aria-label={`Toggle ${tp.label}`}
                          onClick={() => toggleType(tp.key)}
                          className={cn(
                            'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200',
                            isEnabled ? 'bg-accent' : 'bg-muted'
                          )}
                        >
                          <motion.span
                            layout
                            transition={{
                              type: 'spring',
                              stiffness: 500,
                              damping: 30,
                            }}
                            className={cn(
                              'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg',
                              isEnabled ? 'translate-x-5' : 'translate-x-0'
                            )}
                          />
                        </button>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </Section>

        {/* ═══ Batch Options (Owner Only) ═══ */}
        {recipientType === 'store_owner' && (
          <Section
            icon={<Layers className="h-5 w-5" />}
            title="Batch Notifications"
            description="Group related notifications into summary digests"
          >
            <ToggleSwitch
              id="batch-toggle"
              enabled={preferences.batch_options.enabled}
              onToggle={() =>
                updateBatchOption(!preferences.batch_options.enabled)
              }
              label="Enable Batch Delivery"
              description="Combine multiple notifications of the same type into a single summary message"
              icon={<Layers className="h-5 w-5" />}
            />
            {preferences.batch_options.enabled && (
              <motion.p
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="text-xs text-muted-foreground mt-3 px-4 py-2 rounded-lg bg-accent/5 border border-accent/10"
              >
                When batch delivery is enabled, notifications set to daily or weekly
                frequency will be grouped and sent as a consolidated summary.
              </motion.p>
            )}
          </Section>
        )}

        {/* ═══ Actions ═══ */}
        <div className="flex items-center justify-between pt-2">
          {/* Reset */}
          <Button
            variant="ghost"
            size="sm"
            className="gap-2 text-muted-foreground hover:text-foreground"
            onClick={() => setShowResetDialog(true)}
            id="reset-preferences-btn"
          >
            <RotateCcw className="h-4 w-4" />
            Reset to Defaults
          </Button>

          {/* Save */}
          <div className="flex items-center gap-3">
            {/* Status indicators */}
            <AnimatePresence mode="wait">
              {saveSuccess && (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="flex items-center gap-1.5 text-xs text-green-500"
                >
                  <CheckCircle className="h-3.5 w-3.5" />
                  Saved
                </motion.div>
              )}
              {saveError && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="flex items-center gap-1.5 text-xs text-destructive"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  {saveError}
                </motion.div>
              )}
            </AnimatePresence>

            <Button
              onClick={handleSave}
              disabled={isSaving}
              className="gap-2 bg-accent text-accent-foreground hover:bg-accent/90 shadow-[0_0_16px_rgba(212,175,55,0.2)]"
              id="save-preferences-btn"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {isSaving ? 'Saving...' : 'Save Preferences'}
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Reset Confirmation Dialog */}
      <ResetConfirmDialog
        open={showResetDialog}
        onConfirm={handleReset}
        onCancel={() => setShowResetDialog(false)}
      />
    </>
  );
}

export default NotificationPreferences;
