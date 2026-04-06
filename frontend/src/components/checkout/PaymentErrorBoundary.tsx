/**
 * Payment Error Boundary
 * ======================
 * Specialized Error Boundary for payment page components.
 * Captures JS runtime errors, iframe failures, PayPal SDK errors, and DOM failures.
 * Reports all errors to backend /debug/client-errors endpoint.
 */

import { Component, type ErrorInfo, type ReactNode, useCallback, useEffect, useState } from 'react';
import { AlertCircle, RefreshCw, Home, Bug } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getPublicApiBaseUrl } from '@/lib/env';

// Types of errors we capture
export type PaymentErrorType = 
  | 'render'       // JS runtime error during rendering
  | 'iframe'       // Paymob iframe load failure
  | 'sdk'          // PayPal JS SDK initialization error
  | 'dom';         // DOM-level failure

export interface PaymentErrorDetails {
  error_type: PaymentErrorType;
  message: string;
  stack?: string;
  component_stack?: string;
  url: string;
  line?: number;
  column?: number;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

interface Props {
  children: ReactNode;
  provider?: 'paymob' | 'paypal' | 'stripe' | 'general';
  fallback?: ReactNode;
  onReport?: (error: PaymentErrorDetails) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorType: PaymentErrorType;
  reportId: string | null;
}

const getApiUrl = () => getPublicApiBaseUrl();

/**
 * Report an error to the backend debug endpoint
 */
async function reportErrorToBackend(details: PaymentErrorDetails): Promise<{ id: string } | null> {
  try {
    const response = await fetch(`${getApiUrl()}/debug/client-errors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(details),
    });
    
    if (response.ok) {
      const data = await response.json();
      return data;
    }
    console.error('Failed to report error:', response.status);
    return null;
  } catch (e) {
    console.error('Error reporting to backend:', e);
    return null;
  }
}

/**
 * Parse error stack to extract line/column info
 */
function parseErrorLocation(error: Error): { line?: number; column?: number } {
  const stack = error.stack || '';
  // Chrome/Firefox format: "at <fn> (<url>:<line>:<col>)"
  const match = stack.match(/:(\d+):(\d+)/);
  if (match) {
    return { line: parseInt(match[1], 10), column: parseInt(match[2], 10) };
  }
  return {};
}

/**
 * Payment Error Boundary Component
 */
export class PaymentErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: 'render',
      reportId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { provider = 'general', onReport } = this.props;
    
    // Determine error type based on error message/stack
    let errorType: PaymentErrorType = 'render';
    const errorMsg = error.message.toLowerCase();
    const errorStack = error.stack?.toLowerCase() || '';
    
    if (
      errorMsg.includes('iframe') ||
      errorStack.includes('iframe') ||
      errorMsg.includes('paymob')
    ) {
      errorType = 'iframe';
    } else if (
      errorMsg.includes('paypal') ||
      errorMsg.includes('sdk') ||
      errorStack.includes('paypal') ||
      errorStack.includes('zoid')
    ) {
      errorType = 'sdk';
    } else if (
      errorMsg.includes('dom') ||
      errorMsg.includes('element') ||
      errorMsg.includes('node')
    ) {
      errorType = 'dom';
    }
    
    const location = parseErrorLocation(error);
    
    const details: PaymentErrorDetails = {
      error_type: errorType,
      message: error.message,
      stack: error.stack,
      component_stack: errorInfo.componentStack || undefined,
      url: window.location.href,
      line: location.line,
      column: location.column,
      timestamp: new Date().toISOString(),
      metadata: {
        provider,
        userAgent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
      },
    };
    
    // Report to backend
    reportErrorToBackend(details).then((result) => {
      if (result?.id) {
        this.setState({ reportId: result.id });
      }
    });
    
    // Call optional callback
    if (onReport) {
      onReport(details);
    }
    
    this.setState({ errorInfo, errorType });
    
    // Log to console with full details
    console.group(`🔴 Payment Error [${errorType}]`);
    console.error('Error:', error);
    console.error('Component Stack:', errorInfo.componentStack);
    console.error('Provider:', provider);
    console.groupEnd();
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, reportId: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      const { errorType, reportId } = this.state;
      
      const errorTypeLabels: Record<PaymentErrorType, string> = {
        render: 'Rendering Error',
        iframe: 'Payment Iframe Error',
        sdk: 'Payment SDK Error',
        dom: 'DOM Error',
      };
      
      return (
        <div className="min-h-[400px] flex flex-col items-center justify-center p-8 bg-background">
          <AlertCircle className="h-16 w-16 text-destructive mb-4" />
          <h2 className="text-xl font-semibold mb-2">
            {errorTypeLabels[errorType]}
          </h2>
          <p className="text-sm text-muted-foreground text-center max-w-md mb-2">
            {this.state.error.message}
          </p>
          {reportId && (
            <p className="text-xs text-muted-foreground mb-4">
              Error ID: <code className="font-mono">{reportId}</code>
            </p>
          )}
          <div className="flex gap-3">
            <Button variant="outline" onClick={this.handleRetry}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
            <Button variant="hero" onClick={() => (window.location.href = '/')}>
              <Home className="h-4 w-4 mr-2" />
              Go Home
            </Button>
          </div>
          {process.env.NODE_ENV === 'development' && this.state.error.stack && (
            <details className="mt-6 w-full max-w-lg">
              <summary className="cursor-pointer text-sm text-muted-foreground flex items-center gap-2">
                <Bug className="h-4 w-4" />
                View Stack Trace
              </summary>
              <pre className="mt-2 p-4 bg-muted rounded-lg text-xs overflow-auto max-h-48">
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }
    
    return this.props.children;
  }
}

/**
 * Hook to manually report payment errors (for iframe/SDK errors that don't throw)
 */
export function usePaymentErrorReporter() {
  const reportError = useCallback(async (
    errorType: PaymentErrorType,
    message: string,
    metadata?: Record<string, unknown>
  ) => {
    const details: PaymentErrorDetails = {
      error_type: errorType,
      message,
      url: window.location.href,
      timestamp: new Date().toISOString(),
      metadata: {
        ...metadata,
        userAgent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
      },
    };
    
    const result = await reportErrorToBackend(details);
    console.log(`[Payment Error Reporter] ${errorType}: ${message}`, result);
    return result;
  }, []);
  
  return reportError;
}

/**
 * Iframe load error detector
 * Wrap Paymob iframe with this to detect load failures
 */
export function PaymobIframeMonitor({
  iframeUrl,
  onLoad,
  onError,
  timeout = 15000,
  children,
}: {
  iframeUrl: string;
  onLoad?: () => void;
  onError?: (error: Error) => void;
  timeout?: number;
  children: (props: { onIframeLoad: () => void }) => ReactNode;
}) {
  const reportError = usePaymentErrorReporter();
  const [loadStartTime] = useState(() => Date.now());
  
  useEffect(() => {
    // Set up timeout detection
    const timeoutId = setTimeout(() => {
      const elapsed = Date.now() - loadStartTime;
      reportError('iframe', `Paymob iframe load timeout after ${elapsed}ms`, {
        iframeUrl,
        timeout,
      });
      onError?.(new Error(`Iframe load timeout after ${timeout}ms`));
    }, timeout);
    
    return () => clearTimeout(timeoutId);
  }, [iframeUrl, timeout, reportError, onError, loadStartTime]);
  
  const onIframeLoad = useCallback(() => {
    const loadTime = Date.now() - loadStartTime;
    
    // Report performance metric
    fetch(`${getApiUrl()}/debug/perf-metrics?metric_type=iframe_load&value_ms=${loadTime}`, {
      method: 'POST',
    }).catch(() => {});
    
    // Check if iframe actually loaded content (not error page)
    try {
      // This may fail due to cross-origin, but we can detect some failures
      const iframe = document.querySelector('iframe[src*="paymob"]');
      if (iframe) {
        // Report successful load
        onLoad?.();
      }
    } catch {
      // Cross-origin - assume success if load event fired
      onLoad?.();
    }
  }, [loadStartTime, onLoad]);
  
  return <>{children({ onIframeLoad })}</>;
}

/**
 * PayPal SDK load monitor
 */
export function usePayPalSdkMonitor() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const reportError = usePaymentErrorReporter();
  const [loadStartTime] = useState(() => Date.now());
  
  useEffect(() => {
    // Check if PayPal SDK is loaded
    const checkSdk = () => {
      if ((window as unknown as { paypal?: unknown }).paypal) {
        const loadTime = Date.now() - loadStartTime;
        setIsLoading(false);
        
        // Report performance
        fetch(`${getApiUrl()}/debug/perf-metrics?metric_type=sdk_init&value_ms=${loadTime}`, {
          method: 'POST',
        }).catch(() => {});
        
        return true;
      }
      return false;
    };
    
    if (checkSdk()) {
      return;
    }
    
    // Poll for SDK load with timeout
    const maxAttempts = 30;
    let attempts = 0;
    
    const intervalId = setInterval(() => {
      attempts++;
      if (checkSdk()) {
        clearInterval(intervalId);
      } else if (attempts >= maxAttempts) {
        clearInterval(intervalId);
        const err = new Error('PayPal SDK failed to load within timeout');
        setError(err);
        setIsLoading(false);
        reportError('sdk', 'PayPal SDK failed to load', {
          attempts,
          timeout: attempts * 500,
        });
      }
    }, 500);
    
    return () => clearInterval(intervalId);
  }, [reportError, loadStartTime]);
  
  // Listen for PayPal script errors
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      if (event.filename?.includes('paypal') || event.message?.toLowerCase().includes('paypal')) {
        const err = new Error(`PayPal SDK error: ${event.message}`);
        setError(err);
        setIsLoading(false);
        reportError('sdk', event.message, {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        });
      }
    };
    
    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, [reportError]);
  
  return { isLoading, error };
}

export default PaymentErrorBoundary;
