/**
 * Fawry Reference Number Display Component
 * Shows reference number with copy button and countdown timer
 * 
 * @version 1.0.0 - Phase C Implementation
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { 
  Copy, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  MapPin, 
  Phone, 
  RefreshCw,
  ExternalLink,
  QrCode,
  Wallet
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ===========================================
// Types
// ===========================================

export interface FawryReferenceProps {
  referenceNumber: string;
  amountEGP: number;
  expiryTime?: Date;
  orderId: string;
  merchantRef?: string;
  onExpire?: () => void;
  onRefresh?: () => void;
  onCopy?: () => void;
  className?: string;
  showQrCode?: boolean;
  compact?: boolean;
}

export type ExpiryStatus = 'active' | 'warning' | 'expired';

// ===========================================
// Helper Functions
// ===========================================

function formatTimeRemaining(minutes: number, seconds: number): string {
  const mins = Math.floor(minutes);
  const secs = Math.floor(seconds);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function calculateTimeRemaining(expiryTime: Date): { minutes: number; seconds: number; totalSeconds: number; status: ExpiryStatus } {
  const now = new Date();
  const diff = expiryTime.getTime() - now.getTime();
  const totalSeconds = Math.max(0, Math.floor(diff / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  let status: ExpiryStatus = 'active';
  if (totalSeconds <= 0) status = 'expired';
  else if (totalSeconds < 300) status = 'warning'; // Less than 5 minutes
  
  return { minutes, seconds, totalSeconds, status };
}

// ===========================================
// ProgressBar Sub-component (avoids inline styles)
// ===========================================

function ProgressBar({ progress, status }: { progress: number; status: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) {
      ref.current.style.width = `${progress}%`;
    }
  }, [progress]);
  return (
    <div
      ref={ref}
      className={cn(
        "h-full transition-all duration-1000",
        status === 'expired' ? "bg-destructive" :
        status === 'warning' ? "bg-amber-500" : "bg-green-500"
      )}
      data-progress={Math.round(progress)}
    />
  );
}

// ===========================================
// Component
// ===========================================

export function FawryReference({
  referenceNumber,
  amountEGP,
  expiryTime,
  orderId,
  merchantRef,
  onExpire,
  onRefresh,
  onCopy,
  className,
  showQrCode = true,
  compact = false,
}: FawryReferenceProps) {
  const [copied, setCopied] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState({ minutes: 24, seconds: 0, totalSeconds: 1440, status: 'active' as ExpiryStatus });
  const [hasExpired, setHasExpired] = useState(false);

  // Update timer
  useEffect(() => {
    if (!expiryTime) return;

    const updateTimer = () => {
      const remaining = calculateTimeRemaining(expiryTime);
      setTimeRemaining(remaining);
      
      if (remaining.status === 'expired' && !hasExpired) {
        setHasExpired(true);
        onExpire?.();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [expiryTime, hasExpired, onExpire]);

  // Handle copy
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(referenceNumber);
      setCopied(true);
      onCopy?.();
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [referenceNumber, onCopy]);

  // Format reference number for display (add spaces for readability)
  const formattedReference = referenceNumber.length > 8 
    ? referenceNumber.replace(/(.{4})/g, '$1 ').trim()
    : referenceNumber;

  const expiryProgress = expiryTime 
    ? Math.max(0, Math.min(100, (timeRemaining.totalSeconds / (24 * 60 * 60)) * 100))
    : 100;

  if (compact) {
    return (
      <div className={cn("flex items-center gap-3 p-3 bg-muted rounded-lg", className)}>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-mono font-medium truncate">
            {formattedReference}
          </p>
          <p className="text-xs text-muted-foreground">
            {amountEGP.toFixed(2)} EGP
          </p>
        </div>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCopy}
                className="shrink-0"
              >
                {copied ? <CheckCircle2 className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{copied ? 'Copied!' : 'Copy reference number'}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        {timeRemaining.status !== 'expired' && (
          <div className={cn(
            "text-xs font-mono shrink-0",
            timeRemaining.status === 'warning' && "text-amber-600"
          )}>
            <Clock className="h-3 w-3 inline mr-1" />
            {formatTimeRemaining(timeRemaining.minutes, timeRemaining.seconds)}
          </div>
        )}
      </div>
    );
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Wallet className="h-5 w-5 text-blue-600" />
              Fawry Reference Number
            </CardTitle>
            <CardDescription>
              Pay at any Fawry kiosk, ATM, or authorized retailer
            </CardDescription>
          </div>
          {timeRemaining.status !== 'expired' ? (
            <Badge 
              variant={timeRemaining.status === 'warning' ? 'destructive' : 'default'}
              className="font-mono"
            >
              <Clock className="h-3 w-3 mr-1" />
              {formatTimeRemaining(timeRemaining.minutes, timeRemaining.seconds)}
            </Badge>
          ) : (
            <Badge variant="destructive">Expired</Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Expiry warning */}
        {timeRemaining.status === 'warning' && !hasExpired && (
          <Alert variant="destructive" className="bg-amber-50 border-amber-200 text-amber-900">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-800">
              This reference number expires soon! Complete your payment to avoid order cancellation.
            </AlertDescription>
          </Alert>
        )}

        {hasExpired && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              This reference number has expired. Please refresh to generate a new one.
            </AlertDescription>
          </Alert>
        )}

        {/* Reference Number Display */}
        <div className="bg-muted p-6 rounded-lg text-center">
          <p className="text-sm text-muted-foreground mb-2">Reference Number</p>
          <div className="flex items-center justify-center gap-3">
            <Input
              value={formattedReference}
              readOnly
              className="text-center font-mono text-xl tracking-wider max-w-[280px] bg-background"
            />
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleCopy}
                    className="shrink-0"
                  >
                    {copied ? <CheckCircle2 className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{copied ? 'Copied!' : 'Copy to clipboard'}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          
          {/* Amount display */}
          <p className="text-2xl font-bold mt-4">
            {amountEGP.toFixed(2)} <span className="text-lg font-normal">EGP</span>
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Exact amount required
          </p>
        </div>

        {/* Progress bar for expiry */}
        {expiryTime && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Time remaining</span>
              <span>{Math.round(expiryProgress)}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <ProgressBar 
                progress={expiryProgress}
                status={timeRemaining.status}
              />
            </div>
          </div>
        )}

        {/* QR Code placeholder */}
        {showQrCode && (
          <div className="flex justify-center">
            <div className="bg-white p-4 rounded-lg border">
              <QrCode className="h-32 w-32 text-muted-foreground" />
              <p className="text-xs text-center text-muted-foreground mt-2">
                Scan at Fawry POS
              </p>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <h4 className="font-medium text-blue-900 mb-2 flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            How to Pay
          </h4>
          <ol className="text-sm text-blue-800 space-y-2 list-decimal list-inside">
            <li>Visit any Fawry kiosk, ATM, or authorized retailer</li>
            <li>Provide this reference number: <strong className="font-mono">{referenceNumber.slice(-8)}</strong></li>
            <li>Pay exactly <strong>{amountEGP.toFixed(2)} EGP</strong></li>
            <li>Keep your receipt as proof of payment</li>
            <li>Order will be confirmed automatically</li>
          </ol>
        </div>

        {/* Payment locations */}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span>30,000+ Locations</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Phone className="h-4 w-4" />
            <span>Fawry App</span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="flex gap-2">
        {hasExpired ? (
          <Button 
            onClick={onRefresh} 
            className="flex-1"
            variant="default"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Generate New Reference
          </Button>
        ) : (
          <>
            <Button 
              onClick={handleCopy} 
              variant="outline" 
              className="flex-1"
            >
              {copied ? (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy Number
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => window.open('https://fawry.com/store-locator', '_blank')}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Find Location
            </Button>
          </>
        )}
      </CardFooter>
    </Card>
  );
}

// Hook for managing Fawry reference
export function useFawryReference(
  referenceNumber: string,
  expiryMinutes: number = 24 * 60
) {
  const [expiryTime, setExpiryTime] = useState<Date>(() => {
    const expiry = new Date();
    expiry.setMinutes(expiry.getMinutes() + expiryMinutes);
    return expiry;
  });
  
  const [status, setStatus] = useState<ExpiryStatus>('active');

  const refresh = useCallback(() => {
    const newExpiry = new Date();
    newExpiry.setMinutes(newExpiry.getMinutes() + expiryMinutes);
    setExpiryTime(newExpiry);
    setStatus('active');
  }, [expiryMinutes]);

  useEffect(() => {
    const checkExpiry = () => {
      const remaining = calculateTimeRemaining(expiryTime);
      setStatus(remaining.status);
    };

    checkExpiry();
    const interval = setInterval(checkExpiry, 1000);
    return () => clearInterval(interval);
  }, [expiryTime]);

  return {
    expiryTime,
    status,
    refresh,
    isExpired: status === 'expired',
  };
}

export default FawryReference;
