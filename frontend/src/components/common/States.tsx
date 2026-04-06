import { motion } from 'framer-motion';
import { type LucideIcon, Package, Search, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { transitionLinearLoop } from '@/motion';

// Loading State
interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = 'Loading...', className }: LoadingStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn('flex flex-col items-center justify-center p-8 text-center', className)}
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={transitionLinearLoop}
      >
        <Loader2 className="h-10 w-10 text-primary" />
      </motion.div>
      <p className="mt-4 text-sm text-muted-foreground">{message}</p>
    </motion.div>
  );
}

// Empty State
interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon = Package,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('flex flex-col items-center justify-center p-8 text-center', className)}
    >
      <div className="rounded-full bg-muted p-4">
        <Icon className="h-10 w-10 text-muted-foreground" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      {description && (
        <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      {action && (
        <Button onClick={action.onClick} className="mt-4">
          {action.label}
        </Button>
      )}
    </motion.div>
  );
}

// Error State
interface ErrorStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function ErrorState({
  icon: Icon = AlertCircle,
  title,
  description,
  action,
  className,
}: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('flex flex-col items-center justify-center p-8 text-center', className)}
    >
      <div className="rounded-full bg-destructive/10 p-4">
        <Icon className="h-10 w-10 text-destructive" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      {description && (
        <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      {action && (
        <Button onClick={action.onClick} variant="outline" className="mt-4">
          {action.label}
        </Button>
      )}
    </motion.div>
  );
}

// No Results State
interface NoResultsProps {
  query?: string;
  onClear?: () => void;
  className?: string;
}

export function NoResults({ query, onClear, className }: NoResultsProps) {
  return (
    <EmptyState
      icon={Search}
      title="No Results Found"
      description={
        query
          ? `We couldn't find any results for "${query}"`
          : 'Try adjusting your search or filters'
      }
      action={onClear ? { label: 'Clear Filters', onClick: onClear } : undefined}
      className={className}
    />
  );
}
