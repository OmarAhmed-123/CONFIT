/**
 * CONFIT — Sales Alert Card
 * ===========================
 * Individual alert notification card with severity styling,
 * rich preview, and one-click actions.
 */

import { useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  DollarSign,
  RotateCcw,
  Package,
  TrendingUp,
  Users,
  ExternalLink,
  Check,
  X,
  Clock,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  type SalesAlert,
  type AlertSeverity,
  type SalesAlertType,
  type AlertAction,
  getSeverityConfig,
  getAlertTypeConfig,
} from '@/types/salesAlertTypes';
import { useSalesAlertStore } from '@/stores/salesAlertStore';
import { createTransition } from '@/motion';

// ─── Time Formatting ───────────────────────────────────────────────────────────

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

// ─── Severity Icon Component ───────────────────────────────────────────────────

function SeverityIcon({ severity, className }: { severity: AlertSeverity; className?: string }) {
  const config = getSeverityConfig(severity);
  const iconClass = cn(className, config.color);

  switch (config.icon) {
    case 'AlertTriangle':
      return (
        <motion.span
          className={iconClass}
          animate={config.pulseAnimation ? { scale: [1, 1.1, 1] } : {}}
          transition={{ duration: 1.5, repeat: config.pulseAnimation ? Infinity : 0 }}
        >
          <AlertTriangle className="h-4 w-4" />
        </motion.span>
      );
    case 'AlertCircle':
      return <AlertCircle className={iconClass} />;
    case 'Info':
      return <Info className={iconClass} />;
    default:
      return <Info className={iconClass} />;
  }
}

// ─── Alert Type Icon Component ─────────────────────────────────────────────────

function AlertTypeIcon({ type, className }: { type: SalesAlertType; className?: string }) {
  const config = getAlertTypeConfig(type);

  switch (config.icon) {
    case 'DollarSign':
      return <DollarSign className={className} />;
    case 'RotateCcw':
      return <RotateCcw className={className} />;
    case 'Package':
      return <Package className={className} />;
    case 'TrendingUp':
      return <TrendingUp className={className} />;
    case 'Users':
      return <Users className={className} />;
    default:
      return <Info className={className} />;
  }
}

// ─── Severity Badge Component ───────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  const config = getSeverityConfig(severity);

  const variantStyles = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  };

  return (
    <Badge
      variant="outline"
      className={cn(
        'text-[10px] font-medium uppercase tracking-wider',
        variantStyles[severity]
      )}
    >
      {severity}
    </Badge>
  );
}

// ─── Action Button Component ───────────────────────────────────────────────────

function AlertActionButton({
  action,
  onAction,
  compact = false,
}: {
  action: AlertAction;
  onAction: () => void;
  compact?: boolean;
}) {
  if (action.type === 'dismiss') {
    return (
      <Button
        variant="ghost"
        size={compact ? 'icon' : 'sm'}
        className={cn('h-7', compact ? 'w-7' : 'px-2')}
        onClick={onAction}
        title="Dismiss"
      >
        <X className="h-3.5 w-3.5" />
      </Button>
    );
  }

  if (action.target_path) {
    return (
      <Link href={action.target_path} onClick={onAction}>
        <Button
          variant={action.primary ? 'default' : 'ghost'}
          size={compact ? 'icon' : 'sm'}
          className={cn(
            action.primary
              ? 'h-7 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
              : 'h-7',
            compact ? 'w-7' : 'px-3 text-xs'
          )}
          title={action.label}
        >
          {compact ? <ExternalLink className="h-3.5 w-3.5" /> : action.label}
        </Button>
      </Link>
    );
  }

  return (
    <Button
      variant={action.primary ? 'default' : 'ghost'}
      size={compact ? 'icon' : 'sm'}
      className={cn(
        action.primary
          ? 'h-7 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
          : 'h-7',
        compact ? 'w-7' : 'px-3 text-xs'
      )}
      onClick={onAction}
      title={action.label}
    >
      {compact ? <ChevronRight className="h-3.5 w-3.5" /> : action.label}
    </Button>
  );
}

// ─── Main Alert Card Component ─────────────────────────────────────────────────

interface SalesAlertCardProps {
  alert: SalesAlert;
  compact?: boolean;
  showActions?: boolean;
  onMarkRead?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function SalesAlertCard({
  alert,
  compact = false,
  showActions = true,
  onMarkRead,
  onDismiss,
  className,
}: SalesAlertCardProps) {
  const router = useRouter();
  const storeActions = useSalesAlertStore((s) => ({
    markRead: s.markRead,
    dismissAlert: s.dismissAlert,
  }));

  const severityConfig = getSeverityConfig(alert.severity);
  const typeConfig = getAlertTypeConfig(alert.type);

  const handleMarkRead = () => {
    storeActions.markRead(alert.id);
    onMarkRead?.();
  };

  const handleDismiss = () => {
    storeActions.dismissAlert(alert.id);
    onDismiss?.();
  };

  const handleActionClick = (action: AlertAction) => {
    // Mark as read when taking action
    handleMarkRead();

    if (action.type === 'dismiss') {
      handleDismiss();
    }
  };

  // Get primary and secondary actions
  const primaryAction = alert.actions.find((a) => a.primary);
  const secondaryActions = alert.actions.filter((a) => !a.primary && a.type !== 'dismiss');
  const dismissAction = alert.actions.find((a) => a.type === 'dismiss');

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={createTransition({ duration: 0.15 })}
      className={cn(
        'group relative rounded-xl border-l-2 transition-all',
        severityConfig.bgColor,
        severityConfig.borderColor,
        alert.read ? 'opacity-60' : 'shadow-sm',
        !compact && 'p-4',
        compact && 'p-3',
        className
      )}
    >
      <div className={cn('flex gap-3', compact && 'gap-2')}>
        {/* Severity Icon */}
        <div
          className={cn(
            'flex-shrink-0 rounded-lg bg-background/50 flex items-center justify-center',
            compact ? 'w-8 h-8' : 'w-10 h-10'
          )}
        >
          <SeverityIcon severity={alert.severity} className={severityConfig.color} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <SeverityBadge severity={alert.severity} />
                {!alert.read && (
                  <span className="flex-shrink-0 w-2 h-2 rounded-full bg-gradient-to-r from-purple-500 to-blue-500" />
                )}
              </div>
              <h4
                className={cn(
                  'text-sm font-medium mt-1 truncate',
                  !alert.read && 'text-foreground'
                )}
                title={alert.title}
              >
                {alert.title}
              </h4>
            </div>
          </div>

          {/* Rich Preview */}
          {!compact && (
            <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2">
              {alert.rich_preview}
            </p>
          )}

          {/* Compact Preview */}
          {compact && (
            <p className="mt-0.5 text-xs text-muted-foreground truncate">
              {alert.rich_preview}
            </p>
          )}

          {/* Footer */}
          <div className={cn('flex items-center justify-between mt-3', compact && 'mt-2')}>
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{formatTimeAgo(alert.created_at)}</span>
              {!compact && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <AlertTypeIcon type={alert.type} className="h-3 w-3" />
                    {typeConfig.label}
                  </span>
                </>
              )}
            </div>

            {/* Actions */}
            {showActions && (
              <div className="flex items-center gap-1">
                {!alert.read && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={handleMarkRead}
                    title="Mark as read"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </Button>
                )}
                {primaryAction && (
                  <AlertActionButton
                    action={primaryAction}
                    onAction={() => handleActionClick(primaryAction)}
                    compact={compact}
                  />
                )}
                {dismissAction && (
                  <AlertActionButton
                    action={dismissAction}
                    onAction={() => handleActionClick(dismissAction)}
                    compact
                  />
                )}
              </div>
            )}
          </div>

          {/* Expanded Actions (non-compact) */}
          {!compact && secondaryActions.length > 0 && (
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
              {secondaryActions.map((action, idx) => (
                <AlertActionButton
                  key={idx}
                  action={action}
                  onAction={() => handleActionClick(action)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Alert Toast Component ─────────────────────────────────────────────────────

export function SalesAlertToast({
  alert,
  onDismiss,
}: {
  alert: SalesAlert;
  onDismiss?: () => void;
}) {
  const storeActions = useSalesAlertStore((s) => ({
    markRead: s.markRead,
    dismissAlert: s.dismissAlert,
  }));

  const severityConfig = getSeverityConfig(alert.severity);

  const handleDismiss = () => {
    storeActions.dismissAlert(alert.id);
    onDismiss?.();
  };

  const primaryAction = alert.actions.find((a) => a.primary);

  return (
    <motion.div
      initial={{ opacity: 0, x: 100, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.95 }}
      transition={createTransition({ duration: 0.15 })}
      className={cn(
        'w-full max-w-sm rounded-xl border-l-2 p-4 shadow-lg',
        'bg-slate-900/95 backdrop-blur-sm',
        severityConfig.borderColor
      )}
    >
      <div className="flex gap-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-background/50 flex items-center justify-center">
          <SeverityIcon severity={alert.severity} className={severityConfig.color} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <SeverityBadge severity={alert.severity} />
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              onClick={handleDismiss}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>

          <h4 className="text-sm font-medium mt-1">{alert.title}</h4>
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {alert.rich_preview}
          </p>

          {primaryAction && primaryAction.target_path && (
            <Link
              href={primaryAction.target_path}
              onClick={() => storeActions.markRead(alert.id)}
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-purple-400 hover:text-purple-300 transition-colors"
            >
              {primaryAction.label}
              <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default SalesAlertCard;
