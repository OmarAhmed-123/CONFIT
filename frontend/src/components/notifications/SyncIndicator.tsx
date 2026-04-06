/**
 * CONFIT — SyncIndicator Component
 * =================================
 * Visual indicator for preference sync status.
 */

import { cn } from '@/lib/utils';
import { Loader2, Check, AlertCircle, Wifi, WifiOff } from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// SYNC INDICATOR
// ─────────────────────────────────────────────────────────────────────────────

interface SyncIndicatorProps {
  isPending?: boolean;
  hasError?: boolean;
  isOffline?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function SyncIndicator({
  isPending = false,
  hasError = false,
  isOffline = false,
  size = 'sm',
  showLabel = false,
  className,
}: SyncIndicatorProps) {
  const sizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };
  
  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };
  
  // Offline state takes priority
  if (isOffline) {
    return (
      <div className={cn('sync-indicator flex items-center gap-1.5 text-muted-foreground', className)}>
        <WifiOff className={cn(sizeClasses[size])} />
        {showLabel && (
          <span className={cn(textSizeClasses[size])}>Offline</span>
        )}
      </div>
    );
  }
  
  // Error state
  if (hasError) {
    return (
      <div className={cn('sync-indicator flex items-center gap-1.5 text-destructive', className)}>
        <AlertCircle className={cn(sizeClasses[size])} />
        {showLabel && (
          <span className={cn(textSizeClasses[size])}>Sync failed</span>
        )}
      </div>
    );
  }
  
  // Pending/syncing state
  if (isPending) {
    return (
      <div className={cn('sync-indicator flex items-center gap-1.5 text-primary', className)}>
        <Loader2 className={cn(sizeClasses[size], 'animate-spin')} />
        {showLabel && (
          <span className={cn(textSizeClasses[size])}>Syncing...</span>
        )}
      </div>
    );
  }
  
  // Success/online state (show nothing or minimal indicator)
  return (
    <div className={cn('sync-indicator flex items-center gap-1.5 text-green-500 opacity-0 transition-opacity', className)}>
      <Check className={cn(sizeClasses[size])} />
      {showLabel && (
        <span className={cn(textSizeClasses[size])}>Saved</span>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SYNC STATUS BAR
// ─────────────────────────────────────────────────────────────────────────────

interface SyncStatusBarProps {
  isOnline: boolean;
  pendingCount: number;
  lastSyncAt?: Date;
  onRetry?: () => void;
  className?: string;
}

export function SyncStatusBar({
  isOnline,
  pendingCount,
  lastSyncAt,
  onRetry,
  className,
}: SyncStatusBarProps) {
  const formatLastSync = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };
  
  if (!isOnline) {
    return (
      <div className={cn(
        'sync-status-bar flex items-center justify-between p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800',
        className
      )}>
        <div className="flex items-center gap-2">
          <WifiOff className="h-4 w-4" />
          <span className="text-sm font-medium">You're offline</span>
          {pendingCount > 0 && (
            <span className="text-sm">
              • {pendingCount} change{pendingCount !== 1 ? 's' : ''} pending
            </span>
          )}
        </div>
      </div>
    );
  }
  
  if (pendingCount > 0) {
    return (
      <div className={cn(
        'sync-status-bar flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800',
        className
      )}>
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm font-medium">
            {pendingCount} change{pendingCount !== 1 ? 's' : ''} syncing...
          </span>
        </div>
      </div>
    );
  }
  
  if (lastSyncAt) {
    return (
      <div className={cn(
        'sync-status-bar flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg text-green-800',
        className
      )}>
        <div className="flex items-center gap-2">
          <Wifi className="h-4 w-4" />
          <span className="text-sm">
            Last synced {formatLastSync(lastSyncAt)}
          </span>
        </div>
      </div>
    );
  }
  
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// CONFLICT RESOLUTION DIALOG
// ─────────────────────────────────────────────────────────────────────────────

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import type { PreferenceState, ConflictType } from '@/hooks/usePreferenceSync';

interface ConflictResolutionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conflictType: ConflictType;
  serverState: PreferenceState;
  localState: PreferenceState;
  onAcceptServer: () => void;
  onKeepLocal: () => void;
  onMerge: () => void;
}

export function ConflictResolutionDialog({
  open,
  onOpenChange,
  conflictType,
  serverState,
  localState,
  onAcceptServer,
  onKeepLocal,
  onMerge,
}: ConflictResolutionDialogProps) {
  const conflictMessages: Record<ConflictType, { title: string; description: string }> = {
    VERSION_STALE: {
      title: 'Your settings are outdated',
      description: 'Your settings were updated on another device. Your local changes have been discarded.',
    },
    CONCURRENT_UPDATE: {
      title: 'Conflicting changes detected',
      description: 'You made changes on another device at the same time. Choose which version to keep.',
    },
    CHECKSUM_MISMATCH: {
      title: 'Settings out of sync',
      description: 'Your local settings don\'t match the server. Please review and choose which version to keep.',
    },
  };
  
  const { title, description } = conflictMessages[conflictType];
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-500" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          {/* Server version */}
          <div className="rounded-lg border p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium">Server version</h4>
              <span className="text-xs text-muted-foreground">Most recent</span>
            </div>
            <div className="text-sm text-muted-foreground">
              <p>Global notifications: {serverState.global_enabled ? 'Enabled' : 'Disabled'}</p>
              <p>Email: {serverState.channels.email.enabled ? 'Enabled' : 'Disabled'}</p>
              <p>Push: {serverState.channels.push.enabled ? 'Enabled' : 'Disabled'}</p>
            </div>
          </div>
          
          {/* Local version */}
          <div className="rounded-lg border p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium">Your changes</h4>
              <span className="text-xs text-muted-foreground">Pending</span>
            </div>
            <div className="text-sm text-muted-foreground">
              <p>Global notifications: {localState.global_enabled ? 'Enabled' : 'Disabled'}</p>
              <p>Email: {localState.channels.email.enabled ? 'Enabled' : 'Disabled'}</p>
              <p>Push: {localState.channels.push.enabled ? 'Enabled' : 'Disabled'}</p>
            </div>
          </div>
        </div>
        
        <DialogFooter className="flex-col gap-2 sm:flex-row">
          <Button variant="outline" onClick={onAcceptServer}>
            Use server version
          </Button>
          {conflictType === 'CONCURRENT_UPDATE' && (
            <>
              <Button variant="outline" onClick={onKeepLocal}>
                Keep my changes
              </Button>
              <Button onClick={onMerge}>
                Merge both
              </Button>
            </>
          )}
          {conflictType !== 'CONCURRENT_UPDATE' && (
            <Button onClick={onAcceptServer}>
              Accept server version
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default SyncIndicator;
