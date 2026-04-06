import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, RefreshCw, Wifi, WifiOff, Search, FileQuestion, ShieldX, type LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// Base Error State Props
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

// Generic Error State
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
        <Button onClick={action.onClick} className="mt-4" variant="outline">
          {action.label}
        </Button>
      )}
    </motion.div>
  );
}

// Network Error
interface NetworkErrorProps {
  onRetry?: () => void;
  className?: string;
}

export function NetworkError({ onRetry, className }: NetworkErrorProps) {
  return (
    <ErrorState
      icon={WifiOff}
      title="Connection Lost"
      description="Please check your internet connection and try again."
      action={onRetry ? { label: 'Retry', onClick: onRetry } : undefined}
      className={className}
    />
  );
}

// Offline Banner
interface OfflineBannerProps {
  isOffline: boolean;
}

export function OfflineBanner({ isOffline }: OfflineBannerProps) {
  return (
    <AnimatePresence>
      {isOffline && (
        <motion.div
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          className="fixed top-0 left-0 right-0 z-50 bg-amber-500 px-4 py-2 text-center text-sm font-medium text-amber-950"
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

// API Error
interface APIErrorProps {
  statusCode?: number;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function APIError({ statusCode, message, onRetry, className }: APIErrorProps) {
  const getTitle = () => {
    switch (statusCode) {
      case 400:
        return 'Invalid Request';
      case 401:
        return 'Authentication Required';
      case 403:
        return 'Access Denied';
      case 404:
        return 'Not Found';
      case 429:
        return 'Too Many Requests';
      case 500:
        return 'Server Error';
      case 502:
      case 503:
        return 'Service Unavailable';
      default:
        return 'Something Went Wrong';
    }
  };

  const getDescription = () => {
    if (message) return message;
    switch (statusCode) {
      case 401:
        return 'Please sign in to access this content.';
      case 403:
        return "You don't have permission to access this resource.";
      case 404:
        return 'The requested resource could not be found.';
      case 429:
        return 'Please wait a moment before trying again.';
      case 500:
        return 'Our servers are experiencing issues. Please try again later.';
      default:
        return 'An unexpected error occurred. Please try again.';
    }
  };

  return (
    <ErrorState
      icon={AlertCircle}
      title={getTitle()}
      description={getDescription()}
      action={onRetry ? { label: 'Try Again', onClick: onRetry } : undefined}
      className={className}
    />
  );
}

// Not Found Error (404)
interface NotFoundErrorProps {
  title?: string;
  description?: string;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  className?: string;
}

export function NotFoundError({
  title = 'Page Not Found',
  description = "The page you're looking for doesn't exist or has been moved.",
  action = { label: 'Go Home', href: '/' },
  className,
}: NotFoundErrorProps) {
  return (
    <ErrorState
      icon={FileQuestion}
      title={title}
      description={description}
      action={action?.onClick ? { label: action.label, onClick: action.onClick } : undefined}
      className={className}
    />
  );
}

// Search No Results
interface NoResultsProps {
  query?: string;
  onClear?: () => void;
  suggestions?: string[];
  className?: string;
}

export function NoResults({ query, onClear, suggestions, className }: NoResultsProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-8 text-center', className)}>
      <div className="rounded-full bg-muted p-4">
        <Search className="h-10 w-10 text-muted-foreground" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">No Results Found</h3>
      {query && (
        <p className="mt-2 text-sm text-muted-foreground">
          We couldn't find any results for "{query}"
        </p>
      )}
      {suggestions && suggestions.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-medium">Try searching for:</p>
          <div className="mt-2 flex flex-wrap justify-center gap-2">
            {suggestions.map((suggestion) => (
              <span
                key={suggestion}
                className="rounded-full bg-muted px-3 py-1 text-xs"
              >
                {suggestion}
              </span>
            ))}
          </div>
        </div>
      )}
      {onClear && (
        <Button onClick={onClear} variant="outline" className="mt-4">
          Clear Filters
        </Button>
      )}
    </div>
  );
}

// Permission Denied
interface PermissionDeniedProps {
  resource?: string;
  onGoBack?: () => void;
  className?: string;
}

export function PermissionDenied({ resource, onGoBack, className }: PermissionDeniedProps) {
  return (
    <ErrorState
      icon={ShieldX}
      title="Access Denied"
      description={
        resource
          ? `You don't have permission to access this ${resource}.`
          : "You don't have permission to access this resource."
      }
      action={onGoBack ? { label: 'Go Back', onClick: onGoBack } : undefined}
      className={className}
    />
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
  icon: Icon = FileQuestion,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
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

// Error Boundary Fallback
interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary?: () => void;
}

export function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  return (
    <div className="flex min-h-[400px] items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-4 rounded-full bg-destructive/10 p-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
        </div>
        <h2 className="text-xl font-semibold">Something went wrong</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          We encountered an unexpected error. Please try refreshing the page.
        </p>
        {process.env.NODE_ENV === 'development' && (
          <pre className="mt-4 max-h-40 overflow-auto rounded-lg bg-muted p-4 text-left text-xs">
            {error.message}
          </pre>
        )}
        <div className="mt-6 flex justify-center gap-3">
          <Button onClick={() => window.location.reload()} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh Page
          </Button>
          {resetErrorBoundary && (
            <Button onClick={resetErrorBoundary}>Try Again</Button>
          )}
        </div>
      </div>
    </div>
  );
}

// Toast Error
interface ToastErrorProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ToastError({ message, onRetry, onDismiss }: ToastErrorProps) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-destructive/20 bg-destructive/5 p-4">
      <AlertCircle className="h-5 w-5 flex-shrink-0 text-destructive" />
      <div className="flex-1">
        <p className="text-sm font-medium text-destructive">{message}</p>
      </div>
      <div className="flex gap-2">
        {onRetry && (
          <Button size="sm" variant="ghost" onClick={onRetry}>
            Retry
          </Button>
        )}
        {onDismiss && (
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Dismiss
          </Button>
        )}
      </div>
    </div>
  );
}

// Form Error
interface FormErrorProps {
  errors: Record<string, string>;
  className?: string;
}

export function FormError({ errors, className }: FormErrorProps) {
  const errorKeys = Object.keys(errors);
  if (errorKeys.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'rounded-lg border border-destructive/20 bg-destructive/5 p-4',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 flex-shrink-0 text-destructive" />
        <div className="flex-1">
          <p className="text-sm font-medium text-destructive">
            Please fix the following errors:
          </p>
          <ul className="mt-2 list-inside list-disc text-sm text-muted-foreground">
            {errorKeys.map((key) => (
              <li key={key}>{errors[key]}</li>
            ))}
          </ul>
        </div>
      </div>
    </motion.div>
  );
}

// Inline Error
interface InlineErrorProps {
  message: string;
  className?: string;
}

export function InlineError({ message, className }: InlineErrorProps) {
  return (
    <motion.p
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn('flex items-center gap-1 text-sm text-destructive', className)}
    >
      <AlertCircle className="h-3 w-3" />
      {message}
    </motion.p>
  );
}
