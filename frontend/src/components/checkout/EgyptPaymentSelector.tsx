/**
 * Egypt Payment Method Selector
 * Supports: Paymob (cards, Meeza, Instapay), Fawry (COD, cards, wallets), Valu BNPL
 */
import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { 
  CreditCard, 
  Truck, 
  Wallet, 
  Building2, 
  Smartphone,
  Clock,
  CheckCircle2,
  Info
} from 'lucide-react';

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

export interface PaymentMethodOption {
  id: EgyptPaymentMethod;
  name: string;
  description: string;
  icon: React.ReactNode;
  provider: 'paymob' | 'fawry';
  category: 'card' | 'bnpl' | 'cod' | 'wallet' | 'bank' | 'kiosk';
  badge?: string;
  available: boolean;
  tenor?: number; // For Valu BNPL
  fee?: number;
}

export interface EgyptPaymentSelectorProps {
  amountPiastres: number;
  currency: string;
  customerPhone?: string;
  onMethodSelect: (method: EgyptPaymentMethod, metadata?: Record<string, unknown>) => void;
  selectedMethod?: EgyptPaymentMethod;
  loading?: boolean;
}

// ===========================================
// Payment Methods Configuration
// ===========================================

const PAYMENT_METHODS: PaymentMethodOption[] = [
  // Paymob Methods
  {
    id: 'paymob_card',
    name: 'Credit / Debit Card',
    description: 'Visa, Mastercard, or Meeza cards',
    icon: <CreditCard className="h-5 w-5" />,
    provider: 'paymob',
    category: 'card',
    available: true,
  },
  {
    id: 'paymob_meeza',
    name: 'Meeza Card',
    description: 'Egypt local card scheme',
    icon: <CreditCard className="h-5 w-5" />,
    provider: 'paymob',
    category: 'card',
    badge: 'Egypt',
    available: true,
  },
  {
    id: 'paymob_instapay',
    name: 'InstaPay',
    description: 'Instant bank transfer',
    icon: <Building2 className="h-5 w-5" />,
    provider: 'paymob',
    category: 'bank',
    badge: 'Instant',
    available: true,
  },
  {
    id: 'paymob_valu',
    name: 'Valu BNPL',
    description: 'Buy Now, Pay Later - up to 24 months',
    icon: <Clock className="h-5 w-5" />,
    provider: 'paymob',
    category: 'bnpl',
    badge: 'BNPL',
    available: true,
  },
  // Fawry Methods
  {
    id: 'fawry_card',
    name: 'Card (Fawry)',
    description: 'Credit/Debit card with 3DS',
    icon: <CreditCard className="h-5 w-5" />,
    provider: 'fawry',
    category: 'card',
    available: true,
  },
  {
    id: 'fawry_cod',
    name: 'Cash on Delivery',
    description: 'Pay when you receive your order',
    icon: <Truck className="h-5 w-5" />,
    provider: 'fawry',
    category: 'cod',
    badge: 'COD',
    available: true,
  },
  {
    id: 'fawry_wallet',
    name: 'Mobile Wallet',
    description: 'Vodafone Cash, Orange Money, Etisalat Cash',
    icon: <Smartphone className="h-5 w-5" />,
    provider: 'fawry',
    category: 'wallet',
    badge: 'Wallet',
    available: true,
  },
  {
    id: 'fawry_ref_number',
    name: 'Fawry Kiosk / ATM',
    description: 'Pay at any Fawry location',
    icon: <Wallet className="h-5 w-5" />,
    provider: 'fawry',
    category: 'kiosk',
    available: true,
  },
];

const VALU_TENORS = [6, 9, 12, 18, 24] as const;

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

// ===========================================
// Component
// ===========================================

export function EgyptPaymentSelector({
  amountPiastres,
  currency,
  customerPhone,
  onMethodSelect,
  selectedMethod,
  loading = false,
}: EgyptPaymentSelectorProps) {
  const [valuTenor, setValuTenor] = useState<number>(6);
  const [showValuDetails, setShowValuDetails] = useState(false);

  const groupedMethods = useMemo(() => {
    const groups: Record<string, PaymentMethodOption[]> = {
      'Recommended': [],
      'Cards': [],
      'Buy Now, Pay Later': [],
      'Cash & Wallets': [],
    };

    // Sort and group methods
    const sorted = [...PAYMENT_METHODS].sort((a, b) => {
      // Prioritize COD and cards for Egypt
      const priority: Record<string, number> = {
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
  }, []);

  const handleMethodChange = (methodId: EgyptPaymentMethod) => {
    const method = PAYMENT_METHODS.find(m => m.id === methodId);
    if (!method) return;

    const metadata: Record<string, unknown> = {};

    if (methodId === 'paymob_valu') {
      metadata.tenor = valuTenor;
      metadata.monthlyInstallment = calculateValuInstallment(amountPiastres, valuTenor);
    }

    onMethodSelect(methodId, metadata);
  };

  const selectedMethodData = PAYMENT_METHODS.find(m => m.id === selectedMethod);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Payment Method</h3>
        <p className="text-sm text-muted-foreground">
          Total: <span className="font-medium text-foreground">{formatEGP(amountPiastres)}</span>
        </p>
      </div>

      <RadioGroup
        value={selectedMethod}
        onValueChange={handleMethodChange}
        className="space-y-4"
      >
        {Object.entries(groupedMethods).map(([groupName, methods]) => (
          <div key={groupName}>
            <h4 className="text-sm font-medium text-muted-foreground mb-2">{groupName}</h4>
            <div className="grid gap-3">
              {methods.map((method) => (
                <div key={method.id}>
                  <Label
                    htmlFor={method.id}
                    className={`flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-colors ${
                      selectedMethod === method.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    } ${!method.available ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <RadioGroupItem
                      value={method.id}
                      id={method.id}
                      disabled={!method.available || loading}
                    />
                    <div className="flex-1 flex items-center gap-3">
                      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-muted">
                        {method.icon}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{method.name}</span>
                          {method.badge && (
                            <Badge variant="secondary" className="text-xs">
                              {method.badge}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{method.description}</p>
                      </div>
                      {method.provider === 'paymob' && (
                        <Badge variant="outline" className="text-xs">Paymob</Badge>
                      )}
                      {method.provider === 'fawry' && (
                        <Badge variant="outline" className="text-xs">Fawry</Badge>
                      )}
                    </div>
                  </Label>

                  {/* Valu BNPL installment selector */}
                  {method.id === 'paymob_valu' && selectedMethod === 'paymob_valu' && (
                    <div className="mt-3 p-4 bg-muted/50 rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium">Select Installment Plan</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowValuDetails(!showValuDetails)}
                        >
                          <Info className="h-4 w-4 mr-1" />
                          Details
                        </Button>
                      </div>
                      <div className="grid grid-cols-5 gap-2">
                        {VALU_TENORS.map((tenor) => (
                          <Button
                            key={tenor}
                            variant={valuTenor === tenor ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setValuTenor(tenor)}
                            className="flex flex-col"
                          >
                            <span className="text-xs">{tenor} months</span>
                            <span className="text-[10px] text-muted-foreground">
                              {formatEGP(calculateValuInstallment(amountPiastres, tenor))}/mo
                            </span>
                          </Button>
                        ))}
                      </div>
                      {showValuDetails && (
                        <div className="mt-3 p-3 bg-background rounded border text-sm">
                          <p className="font-medium mb-2">Valu BNPL Terms:</p>
                          <ul className="text-muted-foreground space-y-1 text-xs">
                            <li>· Interest-free options available for select merchants</li>
                            <li>· Down payment may be required based on eligibility</li>
                            <li>· Valid Egyptian ID and mobile number required</li>
                            <li>· Instant approval decision</li>
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* COD info */}
                  {method.id === 'fawry_cod' && selectedMethod === 'fawry_cod' && (
                    <div className="mt-3 p-4 bg-muted/50 rounded-lg">
                      <div className="flex items-start gap-3">
                        <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                        <div className="text-sm">
                          <p className="font-medium">Cash on Delivery</p>
                          <p className="text-muted-foreground">
                            Pay {formatEGP(amountPiastres)} in cash when your order arrives.
                            Our courier will collect payment at your doorstep.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Fawry Ref Number info */}
                  {method.id === 'fawry_ref_number' && selectedMethod === 'fawry_ref_number' && (
                    <div className="mt-3 p-4 bg-muted/50 rounded-lg">
                      <div className="flex items-start gap-3">
                        <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                        <div className="text-sm">
                          <p className="font-medium">How it works:</p>
                          <ol className="text-muted-foreground space-y-1 text-xs list-decimal list-inside">
                            <li>Complete order to receive your Fawry reference number</li>
                            <li>Visit any Fawry kiosk, ATM, or authorized retailer</li>
                            <li>Pay the exact amount within 24 hours</li>
                            <li>Order is confirmed automatically after payment</li>
                          </ol>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </RadioGroup>

      {selectedMethodData && (
        <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
          <p className="text-sm">
            <span className="font-medium">Selected:</span> {selectedMethodData.name}
            {selectedMethod === 'paymob_valu' && (
              <span className="text-muted-foreground">
                {' '}· {valuTenor} months · {formatEGP(calculateValuInstallment(amountPiastres, valuTenor))}/month
              </span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}

export default EgyptPaymentSelector;
