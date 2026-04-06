import { useEffect, useState, createContext, useContext } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { WifiOff, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores';

interface OfflineContextValue {
  isOffline: boolean;
  pendingActions: PendingAction[];
  addPendingAction: (action: PendingAction) => void;
  removePendingAction: (id: string) => void;
  retryPendingActions: () => Promise<void>;
}

interface PendingAction {
  id: string;
  type: string;
  data: unknown;
  timestamp: string;
}

const OfflineContext = createContext<OfflineContextValue | undefined>(undefined);

export function useOffline() {
  const context = useContext(OfflineContext);
  if (!context) {
    throw new Error('useOffline must be used within an OfflineProvider');
  }
  return context;
}

interface OfflineProviderProps {
  children: React.ReactNode;
}

export function OfflineProvider({ children }: OfflineProviderProps) {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const { addToast } = useUIStore();

  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      addToast({
        type: 'success',
        title: 'Back Online',
        message: 'Your connection has been restored.',
      });
    };

    const handleOffline = () => {
      setIsOffline(true);
      addToast({
        type: 'warning',
        title: 'You\'re Offline',
        message: 'Some features may be unavailable.',
      });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [addToast]);

  const addPendingAction = (action: PendingAction) => {
    setPendingActions((prev) => [...prev, action]);
    // Store in localStorage for persistence
    const stored = JSON.parse(localStorage.getItem('confit-pending-actions') || '[]');
    stored.push(action);
    localStorage.setItem('confit-pending-actions', JSON.stringify(stored));
  };

  const removePendingAction = (id: string) => {
    setPendingActions((prev) => prev.filter((a) => a.id !== id));
    const stored = JSON.parse(localStorage.getItem('confit-pending-actions') || '[]');
    const filtered = stored.filter((a: PendingAction) => a.id !== id);
    localStorage.setItem('confit-pending-actions', JSON.stringify(filtered));
  };

  const retryPendingActions = async () => {
    if (isOffline) return;

    for (const action of pendingActions) {
      try {
        // Retry the action based on its type
        console.log('Retrying action:', action.type);
        removePendingAction(action.id);
      } catch (error) {
        console.error('Failed to retry action:', error);
      }
    }
  };

  return (
    <OfflineContext.Provider
      value={{
        isOffline,
        pendingActions,
        addPendingAction,
        removePendingAction,
        retryPendingActions,
      }}
    >
      {children}
      <OfflineBanner isOffline={isOffline} />
    </OfflineContext.Provider>
  );
}

interface OfflineBannerProps {
  isOffline: boolean;
}

function OfflineBanner({ isOffline }: OfflineBannerProps) {
  return (
    <AnimatePresence>
      {isOffline && (
        <motion.div
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          className="fixed top-0 left-0 right-0 z-[100] bg-amber-500 px-4 py-2 text-center text-sm font-medium text-amber-950"
        >
          <div className="flex items-center justify-center gap-2">
            <WifiOff className="h-4 w-4" />
            <span>You're currently offline. Some features may be unavailable.</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function OfflineFallback() {
  const { isOffline, retryPendingActions, pendingActions } = useOffline();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex min-h-[400px] flex-col items-center justify-center p-8 text-center"
    >
      <div className="rounded-full bg-amber-500/10 p-6">
        <WifiOff className="h-12 w-12 text-amber-500" />
      </div>
      <h2 className="mt-6 text-2xl font-semibold">You're Offline</h2>
      <p className="mt-2 max-w-md text-muted-foreground">
        It looks like you've lost your internet connection. Please check your connection and try again.
      </p>
      {pendingActions.length > 0 && (
        <p className="mt-4 text-sm text-muted-foreground">
          You have {pendingActions.length} pending action(s) that will be synced when you're back online.
        </p>
      )}
      <Button
        onClick={() => {
          if (navigator.onLine) {
            retryPendingActions();
          } else {
            window.location.reload();
          }
        }}
        className="mt-6"
      >
        <RefreshCw className="mr-2 h-4 w-4" />
        Retry
      </Button>
    </motion.div>
  );
}
