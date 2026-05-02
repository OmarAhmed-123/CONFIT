/**
 * Paymob Iframe Payment Component
 * Handles iframe load, error, success callbacks for Paymob payments
 * 
 * @version 1.0.0 - Phase C Implementation
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  XCircle, 
  RefreshCw,
  Shield,
  Clock,
  Lock
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ===========================================
// Types
// ===========================================

export type PaymobPaymentStatus = 
  | 'loading' 
  | 'ready' 
  | 'processing' 
  | 'success' 
  | 'error' 
  | 'cancelled';

export interface PaymobIframeProps {
  iframeUrl: string;
  paymentKey: string;
  orderId: string;
  amountEGP: number;
  onSuccess?: (data: { transactionId: string; orderId: string }) => void;
  onError?: (error: { message: string; code?: string }) => void;
  onCancel?: () => void;
  onLoad?: () => void;
  className?: string;
  height?: string | number;
  showSecurityBadges?: boolean;
  timeoutMinutes?: number;
}

export interface PaymobCallbackData {
  id: number;
  success: boolean;
  amount_cents: number;
  order: { id: number };
  pending: boolean;
  transaction?: {
    id: number;
    success: boolean;
    amount_cents: number;
  };
}

// ===========================================
// Component
// ===========================================

export function PaymobIframe({
  iframeUrl,
  paymentKey,
  orderId,
  amountEGP,
  onSuccess,
  onError,
  onCancel,
  onLoad,
  className,
  height = '600px',
  showSecurityBadges = true,
  timeoutMinutes = 15,
}: PaymobIframeProps) {
  const [status, setStatus] = useState<PaymobPaymentStatus>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState(timeoutMinutes * 60);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Format time remaining
  const formatTime = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }, []);

  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    setStatus('ready');
    onLoad?.();
  }, [onLoad]);

  // Handle iframe error
  const handleIframeError = useCallback(() => {
    setStatus('error');
    setErrorMessage('Failed to load payment form. Please try again.');
    onError?.({ message: 'Iframe load failed', code: 'IFRAME_ERROR' });
  }, [onError]);

  // Handle payment success from postMessage
  const handlePaymentSuccess = useCallback((data: PaymobCallbackData) => {
    setStatus('success');
    onSuccess?.({
      transactionId: data.transaction?.id?.toString() || data.id?.toString(),
      orderId: data.order?.id?.toString() || orderId,
    });
  }, [onSuccess, orderId]);

  // Handle payment error from postMessage
  const handlePaymentError = useCallback((data: Partial<PaymobCallbackData>) => {
    setStatus('error');
    const message = data.pending ? 'Payment is pending verification' : 'Payment failed or was declined';
    setErrorMessage(message);
    onError?.({ message, code: data.pending ? 'PENDING' : 'PAYMENT_FAILED' });
  }, [onError]);

  // Listen for Paymob postMessage callbacks
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Validate origin - Paymob iframe messages
      const allowedOrigins = [
        'https://accept.paymob.com',
        'https://accept.paymobsolutions.com',
        window.location.origin,
      ];
      
      if (!allowedOrigins.includes(event.origin)) {
        return;
      }

      try {
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
        
        // Handle Paymob callback
        if (data.id && data.order) {
          if (data.success === true && !data.pending) {
            handlePaymentSuccess(data as PaymobCallbackData);
          } else if (data.success === false || data.pending === true) {
            handlePaymentError(data);
          }
        }
      } catch (error) {
        // Not a JSON message, ignore
        console.debug('Paymob iframe message (non-JSON):', event.data);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [handlePaymentSuccess, handlePaymentError]);

  // Session timeout timer
  useEffect(() => {
    if (status === 'ready' || status === 'processing') {
      timerRef.current = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            setStatus('error');
            setErrorMessage('Payment session expired. Please refresh and try again.');
            onError?.({ message: 'Session timeout', code: 'TIMEOUT' });
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [status, onError]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const handleRetry = () => {
    setStatus('loading');
    setErrorMessage(null);
    setTimeRemaining(timeoutMinutes * 60);
    // Reload iframe
    if (iframeRef.current) {
      iframeRef.current.src = iframeUrl;
    }
  };

  const handleCancel = () => {
    setStatus('cancelled');
    onCancel?.();
  };

  // Construct iframe URL with payment token
  const fullIframeUrl = iframeUrl.includes('?') 
    ? `${iframeUrl}&payment_token=${paymentKey}` 
    : `${iframeUrl}?payment_token=${paymentKey}`;

  return (
    <Card className={cn("w-full overflow-hidden", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Lock className="h-4 w-4 text-green-600" />
              Secure Payment
            </CardTitle>
            <CardDescription>
              Amount: <span className="font-medium">{amountEGP.toFixed(2)} EGP</span>
            </CardDescription>
          </div>
          {(status === 'ready' || status === 'processing') && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span className={cn(timeRemaining < 60 && "text-destructive font-medium")}>
                {formatTime(timeRemaining)}
              </span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {/* Loading State */}
        {status === 'loading' && (
          <div className="p-6 space-y-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-12 w-2/3 mx-auto" />
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading secure payment form...
            </div>
          </div>
        )}

        {/* Error State */}
        {status === 'error' && (
          <div className="p-6">
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Payment Error</AlertTitle>
              <AlertDescription>{errorMessage || 'An error occurred'}</AlertDescription>
            </Alert>
            <div className="flex gap-2">
              <Button onClick={handleRetry} className="flex-1">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button variant="outline" onClick={handleCancel}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Success State */}
        {status === 'success' && (
          <div className="p-6 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-green-600 mb-2">
              Payment Successful!
            </h3>
            <p className="text-muted-foreground text-sm mb-4">
              Your payment has been processed successfully.
            </p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Continue
            </Button>
          </div>
        )}

        {/* Cancelled State */}
        {status === 'cancelled' && (
          <div className="p-6 text-center">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <XCircle className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">
              Payment Cancelled
            </h3>
            <p className="text-muted-foreground text-sm mb-4">
              You have cancelled the payment process.
            </p>
            <div className="flex gap-2 justify-center">
              <Button onClick={handleRetry}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button variant="outline" onClick={() => window.history.back()}>
                Go Back
              </Button>
            </div>
          </div>
        )}

        {/* Ready/Processing - Show Iframe */}
        {(status === 'ready' || status === 'processing') && (
          <>
            <div className="relative">
              <iframe
                ref={iframeRef}
                src={fullIframeUrl}
                onLoad={handleIframeLoad}
                onError={handleIframeError}
                className="w-full border-none"
                data-height={typeof height === 'number' ? `${height}px` : height}
                title="Paymob Secure Payment"
                allow="payment *"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              />
              
              {/* Processing overlay */}
              {status === 'processing' && (
                <div className="absolute inset-0 bg-background/80 flex items-center justify-center">
                  <div className="text-center">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
                    <p className="text-sm font-medium">Processing payment...</p>
                  </div>
                </div>
              )}
            </div>

            {/* Security badges */}
            {showSecurityBadges && (
              <div className="p-4 bg-muted/50 border-t">
                <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Shield className="h-3 w-3" />
                    <span>256-bit SSL Encrypted</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Lock className="h-3 w-3" />
                    <span>PCI DSS Compliant</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>Verified by Visa/Mastercard</span>
                  </div>
                </div>
              </div>
            )}

            {/* Cancel button */}
            <div className="p-4 border-t flex justify-between items-center">
              <p className="text-xs text-muted-foreground">
                Order: {orderId.slice(0, 8)}... • Paymob Payment
              </p>
              <Button variant="ghost" size="sm" onClick={handleCancel}>
                Cancel Payment
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// Hook for managing Paymob payment flow
export function usePaymobPayment() {
  const [status, setStatus] = useState<PaymobPaymentStatus>('loading');
  const [paymentData, setPaymentData] = useState<{
    transactionId?: string;
    orderId?: string;
  } | null>(null);
  const [error, setError] = useState<{ message: string; code?: string } | null>(null);

  const reset = useCallback(() => {
    setStatus('loading');
    setPaymentData(null);
    setError(null);
  }, []);

  const handleSuccess = useCallback((data: { transactionId: string; orderId: string }) => {
    setStatus('success');
    setPaymentData(data);
    setError(null);
  }, []);

  const handleError = useCallback((err: { message: string; code?: string }) => {
    setStatus('error');
    setError(err);
  }, []);

  const handleCancel = useCallback(() => {
    setStatus('cancelled');
  }, []);

  return {
    status,
    paymentData,
    error,
    reset,
    handleSuccess,
    handleError,
    handleCancel,
  };
}

export default PaymobIframe;
