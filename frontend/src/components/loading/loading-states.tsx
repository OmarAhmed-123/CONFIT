import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { createLoopTransition, transitionLinearLoop, transitionStandard } from '@/motion';

// Spinner Component
interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const spinnerSizes = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12',
};

export function Spinner({ size = 'md', className }: SpinnerProps) {
  return (
    <Loader2 className={cn('animate-spin text-primary', spinnerSizes[size], className)} />
  );
}

// Loading Overlay
interface LoadingOverlayProps {
  isLoading: boolean;
  message?: string;
}

export function LoadingOverlay({ isLoading, message = 'Loading...' }: LoadingOverlayProps) {
  return (
    <AnimatePresence>
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
        >
          <div className="flex flex-col items-center gap-4">
            <Spinner size="xl" />
            <p className="text-sm text-muted-foreground">{message}</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Page Loading State
interface PageLoadingProps {
  message?: string;
}

export function PageLoading({ message = 'Loading page...' }: PageLoadingProps) {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <motion.div
          animate={{ rotate: 360 }}
          transition={transitionLinearLoop}
        >
          <Spinner size="xl" />
        </motion.div>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

// Button Loading State
interface ButtonLoadingProps {
  isLoading: boolean;
  children: React.ReactNode;
  loadingText?: string;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export function ButtonLoading({
  isLoading,
  children,
  loadingText,
  className,
  disabled,
  ...props
}: ButtonLoadingProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors',
        'bg-primary text-primary-foreground hover:bg-primary/90',
        'disabled:pointer-events-none disabled:opacity-50',
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      <AnimatePresence mode="wait">
        {isLoading ? (
          <motion.span
            key="loading"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center gap-2"
          >
            <Spinner size="sm" />
            {loadingText || children}
          </motion.span>
        ) : (
          <motion.span
            key="content"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
          >
            {children}
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}

// Skeleton Pulse Animation
interface SkeletonPulseProps {
  className?: string;
}

export function SkeletonPulse({ className }: SkeletonPulseProps) {
  return (
    <div className={cn('animate-pulse rounded-md bg-muted', className)} />
  );
}

// Dots Loading Animation
interface DotsLoadingProps {
  size?: 'sm' | 'md' | 'lg';
  color?: string;
}

export function DotsLoading({ size = 'md', color = 'currentColor' }: DotsLoadingProps) {
  const dotSizes = {
    sm: 'h-1.5 w-1.5',
    md: 'h-2 w-2',
    lg: 'h-3 w-3',
  };

  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className={cn('rounded-full', dotSizes[size])}
          style={{ backgroundColor: color }}
          animate={{
            y: [0, -6, 0],
            opacity: [0.5, 1, 0.5],
          }}
          transition={createLoopTransition(i * 0.15, 0.6)}
        />
      ))}
    </div>
  );
}

// Progress Bar Loading
interface ProgressLoadingProps {
  progress: number;
  className?: string;
  showPercentage?: boolean;
}

export function ProgressLoading({ progress, className, showPercentage = true }: ProgressLoadingProps) {
  return (
    <div className={cn('w-full', className)}>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full bg-primary"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={transitionStandard}
        />
      </div>
      {showPercentage && (
        <p className="mt-1 text-right text-xs text-muted-foreground">{Math.round(progress)}%</p>
      )}
    </div>
  );
}

// Card Loading State
interface CardLoadingProps {
  icon?: LucideIcon;
  title?: string;
  description?: string;
  className?: string;
}

export function CardLoading({
  icon: Icon = Loader2,
  title = 'Loading...',
  description = 'Please wait while we fetch your data.',
  className,
}: CardLoadingProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-8 text-center', className)}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={transitionLinearLoop}
      >
        <Icon className="h-10 w-10 text-primary" />
      </motion.div>
      <h3 className="mt-4 text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

// Inline Loading
interface InlineLoadingProps {
  text?: string;
  className?: string;
}

export function InlineLoading({ text = 'Loading...', className }: InlineLoadingProps) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <Spinner size="sm" />
      <span>{text}</span>
    </span>
  );
}

// Image Loading
interface ImageLoadingProps {
  src: string;
  alt: string;
  className?: string;
  containerClassName?: string;
  onLoad?: () => void;
}

export function ImageLoading({
  src,
  alt,
  className,
  containerClassName,
  onLoad,
}: ImageLoadingProps) {
  return (
    <div className={cn('relative overflow-hidden', containerClassName)}>
      <SkeletonPulse className="absolute inset-0" />
      <motion.img
        src={src}
        alt={alt}
        className={cn('relative z-10', className)}
        onLoad={onLoad}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={transitionStandard}
      />
    </div>
  );
}

// Skeleton Group
interface SkeletonGroupProps {
  count: number;
  skeleton: React.ReactNode;
  className?: string;
}

export function SkeletonGroup({ count, skeleton, className }: SkeletonGroupProps) {
  return (
    <div className={className}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i}>{skeleton}</div>
      ))}
    </div>
  );
}
