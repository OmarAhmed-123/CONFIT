/**
 * Egypt Payment Method Selector
 * Supports: Paymob (cards, Meeza, Instapay), Fawry (COD, cards, wallets, kiosk), Valu BNPL
 * 
 * @version 2.0.0 - Phase C Implementation
 */
import { useState, useMemo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  CreditCard, 
  Truck, 
  Wallet, 
  Building2, 
  Smartphone,
  Clock,
  CheckCircle2,
  Info,
  AlertCircle,
  Shield,
  Zap,
  Percent,
  Banknote,
  MapPin,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ===========================================
// Types
// ===========================================

export type EgyptPaymentMethod = 
  | 'paymob_card'
  | 'paymob_meeza'
  | 'paymob_instapay'
  | 'paymob_valu'
  | 'fawry_card'
  | 'fawry_cod'
  | 'fawry_wallet'
  | 'fawry_ref_number';

export type PaymentProvider = 'paymob' | 'fawry';
export type PaymentCategory = 'card' | 'bnpl' | 'cod' | 'wallet' | 'bank' | 'kiosk';

export interface PaymentMethodOption {
  id: EgyptPaymentMethod;
  name: string;
  description: string;
  icon: React.ReactNode;
  provider: PaymentProvider;
  category: PaymentCategory;
  badge?: string;
  badgeVariant?: 'default' | 'secondary' | 'destructive' | 'outline';
  available: boolean;
  requiresPhone?: boolean;
  processingFee?: number; // in piastres
  minAmountPiastres?: number;
  maxAmountPiastres?: number;
}

export interface PaymentMethodSelectorProps {
  amountPiastres: number;
  currency: string;
  customerPhone?: string;
  customerEmail?: string;
  onMethodSelect: (method: EgyptPaymentMethod, metadata?: Record<string, unknown>) => void;
  selectedMethod?: EgyptPaymentMethod;
  loading?: boolean;
  error?: string | null;
  availableMethods?: EgyptPaymentMethod[]; // If provided, only show these methods
  disabledMethods?: EgyptPaymentMethod[]; // Methods to disable
  showFees?: boolean;
  className?: string;
}

// ===========================================
// Payment Methods Configuration
// ===========================================

const ALL_PAYMENT_METHODS: PaymentMethodOption[] = [
  // Paymob Methods
  {
    id: 'paymob_card',
    name: 'Credit / Debit Card',
    description: 'Visa, Mastercard - Secure 3DS authentication',
    icon: <CreditCard className="h-5 w-5" />,
    provider: 'paymob',
    category: 'card',
    badge: 'Secure',
    badgeVariant: 'secondary',
    available: true,
    processingFee: 0,
  },
  {
    id: 'paymob_meeza',
    name: 'Meeza Card',
    description: 'Egypt domestic card scheme - Lower fees',
    icon: <Shield className="h-5 w-5" />,
    provider: 'paymob',
    category: 'card',
    badge: 'Egypt',
    badgeVariant: 'default',
    available: true,
    processingFee: 0,
  },
  {
    id: 'paymob_instapay',
    name: 'InstaPay',
    description: 'Instant bank transfer from all Egyptian banks',
    icon: <Zap className="h-5 w-5" />,
    provider: 'paymob',
    category: 'bank',
    badge: 'Instant',
    badgeVariant: 'default',
    available: true,
    requiresPhone: true,
    processingFee: 0,
  },
  {
    id: 'paymob_valu',
    name: 'Valu BNPL',
    description: 'Buy Now, Pay Later - Split over 6-36 months',
    icon: <Clock className="h-5 w-5" />,
    provider: 'paymob',
    category: 'bnpl',
    badge: '0% Interest*',
    badgeVariant: 'default',
    available: true,
    requiresPhone: true,
    processingFee: 0,
    minAmountPiastres: 100000, // 1,000 EGP minimum
  },
  // Fawry Methods
  {
    id: 'fawry_card',
    name: 'Card Payment (Fawry)',
    description: 'Credit/Debit card with 3D Secure',
    icon: <CreditCard className="h-5 w-5" />,
    provider: 'fawry',
    category: 'card',
    available: true,
    processingFee: 0,
  },
  {
    id: 'fawry_cod',
    name: 'Cash on Delivery',
    description: 'Pay in cash when your order arrives',
    icon: <Truck className="h-5 w-5" />,
    provider: 'fawry',
    category: 'cod',
    badge: 'COD',
    badgeVariant: 'outline',
    available: true,
    processingFee: 5000, // 50 EGP COD fee
    maxAmountPiastres: 500000, // 5,000 EGP max for COD
  },
  {
    id: 'fawry_wallet',
    name: 'Mobile Wallet',
    description: 'Vodafone Cash, Orange Money, Etisalat Cash',
    icon: <Smartphone className="h-5 w-5" />,
    provider: 'fawry',
    category: 'wallet',
    badge: 'Wallet',
    badgeVariant: 'secondary',
    available: true,
    requiresPhone: true,
    processingFee: 0,
  },
  {
    id: 'fawry_ref_number',
    name: 'Fawry Kiosk / ATM',
    description: 'Pay with cash at any Fawry location',
    icon: <MapPin className="h-5 w-5" />,
    provider: 'fawry',
    category: 'kiosk',
    badge: 'Cash',
    badgeVariant: 'outline',
    available: true,
    processingFee: 1500, // 15 EGP service fee
  },
];

const VALU_TENORS = [6, 9, 12, 18, 24, 36] as const;

// ===========================================
// Helper Functions
// ===========================================

function piastresToEGP(piastres: number): number {
  return piastres / 100;
}

function formatEGP(piastres: number): string {
  const egp = piastresToEGP(piastres);
  return `${egp.toFixed(2)} EGP`;
}

function calculateValuInstallment(totalPiastres: number, tenor: number): number {
  return Math.ceil(totalPiastres / tenor);
}

function calculateTotalWithFee(amountPiastres: number, feePiastres?: number): number {
  return amountPiastres + (feePiastres || 0);
}

// ===========================================
// Component
// ===========================================

export function PaymentMethodSelector({
  amountPiastres,
  currency,
  customerPhone,
  customerEmail,
  onMethodSelect,
  selectedMethod,
  loading = false,
  error = null,
  availableMethods,
  disabledMethods = [],
  showFees = true,
  className,
}: PaymentMethodSelectorProps) {
  const [valuTenor, setValuTenor] = useState<number>(6);
  const [showValuDetails, setShowValuDetails] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  // Filter and validate payment methods
  const paymentMethods = useMemo(() => {
    let methods = ALL_PAYMENT_METHODS;
    
    // Filter by available methods if specified
    if (availableMethods) {
      methods = methods.filter(m => availableMethods.includes(m.id));
    }
    
    // Check amount constraints
    methods = methods.map(method => {
      const isDisabled = disabledMethods.includes(method.id);
      const belowMin = method.minAmountPiastres && amountPiastres < method.minAmountPiastres;
      const aboveMax = method.maxAmountPiastres && amountPiastres > method.maxAmountPiastres;
      const missingPhone = method.requiresPhone && !customerPhone;
      
      let unavailableReason: string | undefined;
      if (belowMin) unavailableReason = `Minimum ${formatEGP(method.minAmountPiastres!)} required`;
      if (aboveMax) unavailableReason = `Maximum ${formatEGP(method.maxAmountPiastres!)} allowed`;
      if (missingPhone) unavailableReason = 'Phone number required';
      
      return {
        ...method,
        available: method.available && !isDisabled && !belowMin && !aboveMax && !missingPhone,
        unavailableReason,
      };
    });
    
    return methods;
  }, [amountPiastres, availableMethods, disabledMethods, customerPhone]);

  // Group methods by category
  const groupedMethods = useMemo(() => {
    const groups: Record<string, (PaymentMethodOption & { unavailableReason?: string })[]> = {
      'Recommended': [],
      'Cards': [],
      'Buy Now, Pay Later': [],
      'Cash & Wallets': [],
    };

    const sorted = [...paymentMethods].sort((a, b) => {
      const priority: Record<PaymentCategory, number> = {
        'card': 1,
        'cod': 2,
        'bnpl': 3,
        'wallet': 4,
        'bank': 5,
        'kiosk': 6,
      };
      return (priority[a.category] || 99) - (priority[b.category] || 99);
    });

    sorted.forEach(method => {
      if (method.category === 'card') {
        groups['Cards'].push(method);
      } else if (method.category === 'bnpl') {
        groups['Buy Now, Pay Later'].push(method);
      } else if (method.category === 'cod' || method.category === 'wallet' || method.category === 'kiosk') {
        groups['Cash & Wallets'].push(method);
      } else {
        groups['Recommended'].push(method);
      }
    });

    // Remove empty groups
    Object.keys(groups).forEach(key => {
      if (groups[key].length === 0) {
        delete groups[key];
      }
    });

    return groups;
  }, [paymentMethods]);

  const handleMethodChange = useCallback((methodId: EgyptPaymentMethod) => {
    const method = paymentMethods.find(m => m.id === methodId);
    if (!method || !method.available) return;

    setLocalError(null);
    const metadata: Record<string, unknown> = {};

    if (methodId === 'paymob_valu') {
      metadata.tenor = valuTenor;
      metadata.monthlyInstallment = calculateValuInstallment(amountPiastres, valuTenor);
    }

    if (method.processingFee) {
      metadata.processingFee = method.processingFee;
      metadata.totalAmount = calculateTotalWithFee(amountPiastres, method.processingFee);
    }

    onMethodSelect(methodId, metadata);
  }, [paymentMethods, valuTenor, amountPiastres, onMethodSelect]);

  const selectedMethodData = paymentMethods.find(m => m.id === selectedMethod);
  const displayError = error || localError;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="text-lg">Payment Method</CardTitle>
        <CardDescription>
          Total: <span className="font-medium text-foreground">{formatEGP(amountPiastres)}</span>
          {currency !== 'EGP' && ` (${currency})`}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {displayError && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{displayError}</AlertDescription>
          </Alert>
        )}

        <RadioGroup
          value={selectedMethod}
          onValueChange={handleMethodChange}
          className="space-y-4"
          disabled={loading}
        >
          {Object.entries(groupedMethods).map(([groupName, methods]) => (
            <div key={groupName}>
              <h4 className="text-sm font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                {groupName}
              </h4>
              <div className="grid gap-3">
                {methods.map((method) => (
                  <div key={method.id}>
                    <Label
                      htmlFor={method.id}
                      className={cn(
                        "flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-all",
                        selectedMethod === method.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50 hover:bg-muted/50',
                        !method.available && 'opacity-60 cursor-not-allowed',
                        loading && 'pointer-events-none opacity-50'
                      )}
                    >
                      <RadioGroupItem
                        value={method.id}
                        id={method.id}
                        disabled={!method.available || loading}
                        className="shrink-0"
                      />
                      <div className="flex-1 flex items-center gap-3 min-w-0">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-muted shrink-0">
                          {method.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium">{method.name}</span>
                            {method.badge && method.available && (
                              <Badge 
                                variant={method.badgeVariant || 'secondary'} 
                                className="text-xs"
                              >
                                {method.badge}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground truncate">
                            {method.description}
                          </p>
                          {!method.available && method.unavailableReason && (
                            <p className="text-xs text-destructive mt-1">
                              {method.unavailableReason}
                            </p>
                          )}
                        </div>
                        <div className="text-right shrink-0">
                          {method.provider === 'paymob' && (
                            <Badge variant="outline" className="text-xs">Paymob</Badge>
                          )}
                          {method.provider === 'fawry' && (
                            <Badge variant="outline" className="text-xs">Fawry</Badge>
                          )}
                          {showFees && method.processingFee !== undefined && method.processingFee > 0 && (
                            <p className="text-xs text-muted-foreground mt-1">
                              +{formatEGP(method.processingFee)} fee
                            </p>
                          )}
                        </div>
                      </div>
                    </Label>

                    {/* Valu BNPL installment selector */}
                    {method.id === 'paymob_valu' && selectedMethod === 'paymob_valu' && method.available && (
                      <div className="mt-3 p-4 bg-muted/50 rounded-lg animate-in slide-in-from-top-2">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-sm font-medium">Select Installment Plan</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowValuDetails(!showValuDetails)}
                            type="button"
                          >
                            <Info className="h-4 w-4 mr-1" />
                            Details
                          </Button>
                        </div>
                        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                          {VALU_TENORS.map((tenor) => (
                            <Button
                              key={tenor}
                              variant={valuTenor === tenor ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => {
                                setValuTenor(tenor);
                                onMethodSelect('paymob_valu', {
                                  tenor,
                                  monthlyInstallment: calculateValuInstallment(amountPiastres, tenor),
                                });
                              }}
                              type="button"
                              className="flex flex-col h-auto py-2"
                            >
                              <span className="text-xs font-medium">{tenor}m</span>
                              <span className="text-[10px] text-muted-foreground">
                                {formatEGP(calculateValuInstallment(amountPiastres, tenor))}/mo
                              </span>
                            </Button>
                          ))}
                        </div>
                        {showValuDetails && (
                          <div className="mt-3 p-3 bg-background rounded border text-sm animate-in fade-in">
                            <p className="font-medium mb-2">Valu BNPL Terms:</p>
                            <ul className="text-muted-foreground space-y-1 text-xs">
                              <li>• Interest-free options available for select merchants</li>
                              <li>• Down payment may be required based on eligibility</li>
                              <li>• Valid Egyptian ID and mobile number required</li>
                              <li>• Instant approval decision</li>
                              <li>• Subject to Valu credit assessment</li>
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    {/* COD info */}
                    {method.id === 'fawry_cod' && selectedMethod === 'fawry_cod' && method.available && (
                      <div className="mt-3 p-4 bg-muted/50 rounded-lg animate-in slide-in-from-top-2">
                        <div className="flex items-start gap-3">
                          <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
                          <div className="text-sm">
                            <p className="font-medium">Cash on Delivery</p>
                            <p className="text-muted-foreground">
                              Pay {formatEGP(calculateTotalWithFee(amountPiastres, method.processingFee))} in cash when your order arrives.
                              {method.processingFee ? ` (Includes ${formatEGP(method.processingFee)} COD fee)` : ''}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Fawry Ref Number info */}
                    {method.id === 'fawry_ref_number' && selectedMethod === 'fawry_ref_number' && method.available && (
                      <div className="mt-3 p-4 bg-muted/50 rounded-lg animate-in slide-in-from-top-2">
                        <div className="flex items-start gap-3">
                          <Info className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
                          <div className="text-sm">
                            <p className="font-medium">How it works:</p>
                            <ol className="text-muted-foreground space-y-1 text-xs list-decimal list-inside">
                              <li>Complete order to receive your Fawry reference number</li>
                              <li>Visit any Fawry kiosk, ATM, or authorized retailer</li>
                              <li>Pay the exact amount within 24 hours</li>
                              <li>Order is confirmed automatically after payment</li>
                            </ol>
                            {method.processingFee ? (
                              <p className="text-xs text-muted-foreground mt-2">
                                Service fee: {formatEGP(method.processingFee)}
                              </p>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Mobile wallet info */}
                    {method.id === 'fawry_wallet' && selectedMethod === 'fawry_wallet' && method.available && (
                      <div className="mt-3 p-4 bg-muted/50 rounded-lg animate-in slide-in-from-top-2">
                        <p className="text-sm font-medium mb-2">Supported Wallets:</p>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline" className="text-xs">Vodafone Cash</Badge>
                          <Badge variant="outline" className="text-xs">Orange Money</Badge>
                          <Badge variant="outline" className="text-xs">Etisalat Cash</Badge>
                          <Badge variant="outline" className="text-xs">WE Pay</Badge>
                        </div>
                        {!customerPhone && (
                          <Alert variant="destructive" className="mt-2">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>Phone number required for mobile wallet payments</AlertDescription>
                          </Alert>
                        )}
                      </div>
                    )}

                    {/* InstaPay info */}
                    {method.id === 'paymob_instapay' && selectedMethod === 'paymob_instapay' && method.available && (
                      <div className="mt-3 p-4 bg-muted/50 rounded-lg animate-in slide-in-from-top-2">
                        <p className="text-sm font-medium mb-2">Supported Banks:</p>
                        <div className="grid grid-cols-2 gap-1 text-xs text-muted-foreground">
                          <span>• CIB</span>
                          <span>• QNB</span>
                          <span>• Banque Misr</span>
                          <span>• National Bank of Egypt</span>
                          <span>• AlexBank</span>
                          <span>• And more...</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </RadioGroup>

        {/* Selected method summary */}
        {selectedMethodData && (
          <div className="p-4 bg-primary/5 rounded-lg border border-primary/20 animate-in fade-in">
            <div className="flex items-center justify-between">
              <p className="text-sm">
                <span className="font-medium">Selected:</span>{' '}
                <span className="text-foreground">{selectedMethodData.name}</span>
              </p>
              {loading && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
            </div>
            
            {selectedMethod === 'paymob_valu' && (
              <p className="text-sm text-muted-foreground mt-1">
                {valuTenor} months • {formatEGP(calculateValuInstallment(amountPiastres, valuTenor))}/month
              </p>
            )}
            
            {selectedMethodData.processingFee !== undefined && selectedMethodData.processingFee > 0 && (
              <p className="text-sm text-muted-foreground mt-1">
                Including {formatEGP(selectedMethodData.processingFee)} processing fee
              </p>
            )}
            
            {selectedMethodData.processingFee !== undefined && (
              <p className="text-sm font-medium mt-2">
                Total to pay: {formatEGP(calculateTotalWithFee(amountPiastres, selectedMethodData.processingFee))}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default PaymentMethodSelector;
