/**
 * Valu BNPL Installment Calculator
 * Shows monthly amounts and tenor selection for Valu Buy Now Pay Later
 * 
 * @version 1.0.0 - Phase C Implementation
 */
import { useState, useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Calculator,
  Percent,
  Info,
  Calendar,
  TrendingUp,
  Shield,
  Wallet
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ===========================================
// Types
// ===========================================

export type ValuTenor = 6 | 9 | 12 | 18 | 24 | 36;

export interface ValuCalculation {
  tenor: ValuTenor;
  monthlyAmount: number; // in piastres
  totalAmount: number; // in piastres
  interestRate: number; // annual percentage
  downPayment: number; // in piastres
  processingFee: number; // in piastres
  apr: number; // annual percentage rate
}

export interface ValuCalculatorProps {
  amountPiastres: number;
  onTenorChange?: (tenor: ValuTenor, calculation: ValuCalculation) => void;
  onConfirm?: (calculation: ValuCalculation) => void;
  selectedTenor?: ValuTenor;
  minAmountPiastres?: number;
  maxAmountPiastres?: number;
  showEligibilityCheck?: boolean;
  className?: string;
  loading?: boolean;
}

export interface ValuEligibilityResult {
  eligible: boolean;
  maxAmountEGP: number;
  availableTenors: ValuTenor[];
  reason?: string;
  creditLimit: number;
  usedCredit: number;
  availableCredit: number;
}

// ===========================================
// Constants
// ===========================================

const VALU_TENORS: ValuTenor[] = [6, 9, 12, 18, 24, 36];

const DEFAULT_INTEREST_RATES: Record<ValuTenor, number> = {
  6: 0,    // 0% for 6 months
  9: 0,    // 0% for 9 months
  12: 0,   // 0% for 12 months
  18: 15,  // 15% for 18 months
  24: 15,  // 15% for 24 months
  36: 20,  // 20% for 36 months
};

const PROCESSING_FEE_RATES: Record<ValuTenor, number> = {
  6: 0.025,  // 2.5%
  9: 0.025,
  12: 0.03,  // 3%
  18: 0.035, // 3.5%
  24: 0.04,  // 4%
  36: 0.05,  // 5%
};

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

function formatCurrencyShort(piastres: number): string {
  const egp = piastresToEGP(piastres);
  if (egp >= 1000) {
    return `${(egp / 1000).toFixed(1)}k EGP`;
  }
  return `${egp.toFixed(0)} EGP`;
}

function calculateInstallment(
  amountPiastres: number,
  tenor: ValuTenor,
  interestRate: number = DEFAULT_INTEREST_RATES[tenor],
  processingFeeRate: number = PROCESSING_FEE_RATES[tenor]
): ValuCalculation {
  const processingFee = Math.round(amountPiastres * processingFeeRate);
  const totalWithFee = amountPiastres + processingFee;
  
  // Simple interest calculation
  const annualInterest = totalWithFee * (interestRate / 100);
  const totalInterest = (annualInterest * tenor) / 12;
  const totalAmount = totalWithFee + totalInterest;
  
  // Monthly amount
  const monthlyAmount = Math.ceil(totalAmount / tenor);
  
  // Down payment (usually 0 for Valu, but can be configured)
  const downPayment = 0;
  
  // Calculate APR
  const apr = interestRate > 0 ? interestRate + (processingFeeRate * 100 * 12) : processingFeeRate * 100 * 12;
  
  return {
    tenor,
    monthlyAmount,
    totalAmount,
    interestRate,
    downPayment,
    processingFee,
    apr: Math.round(apr * 100) / 100,
  };
}

// ===========================================
// Component
// ===========================================

export function ValuCalculator({
  amountPiastres,
  onTenorChange,
  onConfirm,
  selectedTenor: initialTenor = 6,
  minAmountPiastres = 100000, // 1,000 EGP
  maxAmountPiastres = 10000000, // 100,000 EGP
  showEligibilityCheck = true,
  className,
  loading = false,
}: ValuCalculatorProps) {
  const [selectedTenor, setSelectedTenor] = useState<ValuTenor>(initialTenor);
  const [showDetails, setShowDetails] = useState(false);
  const [eligibility, setEligibility] = useState<ValuEligibilityResult | null>(null);
  const [checkingEligibility, setCheckingEligibility] = useState(false);

  // Validate amount constraints
  const amountValid = useMemo(() => {
    return amountPiastres >= minAmountPiastres && amountPiastres <= maxAmountPiastres;
  }, [amountPiastres, minAmountPiastres, maxAmountPiastres]);

  // Calculate current installment
  const calculation = useMemo(() => {
    return calculateInstallment(amountPiastres, selectedTenor);
  }, [amountPiastres, selectedTenor]);

  // Calculate all tenors for comparison
  const allCalculations = useMemo(() => {
    return VALU_TENORS.map(tenor => ({
      tenor,
      calc: calculateInstallment(amountPiastres, tenor),
    }));
  }, [amountPiastres]);

  const handleTenorChange = useCallback((tenor: ValuTenor) => {
    setSelectedTenor(tenor);
    const calc = calculateInstallment(amountPiastres, tenor);
    onTenorChange?.(tenor, calc);
  }, [amountPiastres, onTenorChange]);

  const handleSliderChange = useCallback((value: number[]) => {
    const tenor = VALU_TENORS[value[0]];
    if (tenor) {
      handleTenorChange(tenor);
    }
  }, [handleTenorChange]);

  const checkEligibility = useCallback(async () => {
    setCheckingEligibility(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Mock eligibility result
    const mockResult: ValuEligibilityResult = {
      eligible: amountPiastres <= 500000, // Mock: eligible up to 5,000 EGP
      maxAmountEGP: 5000,
      availableTenors: [6, 9, 12, 18, 24, 36],
      creditLimit: 10000,
      usedCredit: 0,
      availableCredit: 10000,
    };
    
    setEligibility(mockResult);
    setCheckingEligibility(false);
  }, [amountPiastres]);

  if (!amountValid) {
    return (
      <Card className={cn("w-full", className)}>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Wallet className="h-5 w-5 text-purple-600" />
            Valu BNPL
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {amountPiastres < minAmountPiastres 
                ? `Minimum amount for Valu is ${formatEGP(minAmountPiastres)}`
                : `Maximum amount for Valu is ${formatEGP(maxAmountPiastres)}`}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Calculator className="h-5 w-5 text-purple-600" />
              Valu Installment Calculator
            </CardTitle>
            <CardDescription>
              Split your payment over {selectedTenor} months
            </CardDescription>
          </div>
          {calculation.interestRate === 0 ? (
            <Badge variant="default" className="bg-green-600">
              <Percent className="h-3 w-3 mr-1" />
              0% Interest
            </Badge>
          ) : (
            <Badge variant="secondary">
              <Percent className="h-3 w-3 mr-1" />
              {calculation.interestRate}% p.a.
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Amount display */}
        <div className="text-center p-4 bg-muted rounded-lg">
          <p className="text-sm text-muted-foreground">Order Amount</p>
          <p className="text-3xl font-bold">{formatEGP(amountPiastres)}</p>
        </div>

        {/* Tenor slider */}
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Select Duration</span>
            <span className="font-medium">{selectedTenor} months</span>
          </div>
          <Slider
            value={[VALU_TENORS.indexOf(selectedTenor)]}
            onValueChange={handleSliderChange}
            max={VALU_TENORS.length - 1}
            step={1}
            disabled={loading}
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            {VALU_TENORS.map(t => (
              <button
                key={t}
                onClick={() => handleTenorChange(t)}
                className={cn(
                  "px-2 py-1 rounded transition-colors",
                  selectedTenor === t 
                    ? "bg-primary text-primary-foreground font-medium" 
                    : "hover:bg-muted"
                )}
                disabled={loading}
              >
                {t}m
              </button>
            ))}
          </div>
        </div>

        {/* Installment summary */}
        <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-purple-600 uppercase tracking-wide">Monthly Payment</p>
              <p className="text-2xl font-bold text-purple-900">
                {formatEGP(calculation.monthlyAmount)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-purple-600 uppercase tracking-wide">Duration</p>
              <p className="text-2xl font-bold text-purple-900">
                {selectedTenor} <span className="text-base font-normal">months</span>
              </p>
            </div>
          </div>
          
          <Separator className="my-3 bg-purple-200" />
          
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-purple-700">Principal:</span>
              <span className="font-medium">{formatEGP(amountPiastres)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-purple-700">Processing Fee:</span>
              <span className="font-medium">{formatEGP(calculation.processingFee)}</span>
            </div>
            {calculation.interestRate > 0 && (
              <div className="flex justify-between">
                <span className="text-purple-700">Interest ({calculation.interestRate}%):</span>
                <span className="font-medium">
                  {formatEGP(calculation.totalAmount - amountPiastres - calculation.processingFee)}
                </span>
              </div>
            )}
            <div className="flex justify-between pt-2 border-t border-purple-200 mt-1">
              <span className="font-medium text-purple-900">Total:</span>
              <span className="font-bold text-purple-900">{formatEGP(calculation.totalAmount)}</span>
            </div>
          </div>
        </div>

        {/* Tenor comparison table */}
        {showDetails && (
          <div className="rounded-lg border overflow-hidden animate-in slide-in-from-top-2">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="p-2 text-left">Months</th>
                  <th className="p-2 text-right">Monthly</th>
                  <th className="p-2 text-right">Total</th>
                  <th className="p-2 text-center">Rate</th>
                </tr>
              </thead>
              <tbody>
                {allCalculations.map(({ tenor, calc }) => (
                  <tr 
                    key={tenor} 
                    className={cn(
                      "border-t",
                      tenor === selectedTenor && "bg-purple-50"
                    )}
                  >
                    <td className="p-2">
                      {tenor === selectedTenor && (
                        <CheckCircle2 className="h-4 w-4 text-purple-600 inline mr-1" />
                      )}
                      {tenor} months
                    </td>
                    <td className="p-2 text-right font-medium">
                      {formatEGP(calc.monthlyAmount)}
                    </td>
                    <td className="p-2 text-right text-muted-foreground">
                      {formatEGP(calc.totalAmount)}
                    </td>
                    <td className="p-2 text-center">
                      {calc.interestRate === 0 ? (
                        <Badge variant="default" className="text-xs bg-green-600">0%</Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">{calc.interestRate}%</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Info section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Shield className="h-4 w-4 text-green-600" />
            <span>Instant approval with valid Egyptian ID</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4 text-blue-600" />
            <span>First installment due next month</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <TrendingUp className="h-4 w-4 text-purple-600" />
            <span>Build your credit history with Valu</span>
          </div>
        </div>

        {/* Eligibility check */}
        {showEligibilityCheck && eligibility && (
          <Alert className={cn(
            eligibility.eligible ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"
          )}>
            <AlertCircle className={cn(
              "h-4 w-4",
              eligibility.eligible ? "text-green-600" : "text-amber-600"
            )} />
            <AlertDescription className={eligibility.eligible ? "text-green-800" : "text-amber-800"}>
              {eligibility.eligible 
                ? `You're eligible! Credit limit: ${formatEGP(eligibility.creditLimit * 100)}`
                : eligibility.reason || 'Not eligible for this amount'}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>

      <CardFooter className="flex gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                onClick={() => setShowDetails(!showDetails)}
                className="flex-1"
                disabled={loading}
              >
                <Info className="h-4 w-4 mr-2" />
                {showDetails ? 'Hide Details' : 'View All Plans'}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Compare all installment options</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {showEligibilityCheck && !eligibility && (
          <Button
            variant="outline"
            onClick={checkEligibility}
            disabled={checkingEligibility || loading}
          >
            {checkingEligibility ? (
              <Clock className="h-4 w-4 animate-spin" />
            ) : (
              <Shield className="h-4 w-4 mr-2" />
            )}
            Check Eligibility
          </Button>
        )}

        <Button
          onClick={() => onConfirm?.(calculation)}
          disabled={loading || Boolean(showEligibilityCheck && eligibility && !eligibility.eligible)}
          className="flex-1"
        >
          {loading ? (
            <Clock className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <CheckCircle2 className="h-4 w-4 mr-2" />
          )}
          Proceed with {selectedTenor} Months
        </Button>
      </CardFooter>
    </Card>
  );
}

// Hook for Valu calculations
export function useValuCalculator(amountPiastres: number) {
  const [selectedTenor, setSelectedTenor] = useState<ValuTenor>(6);

  const calculation = useMemo(() => {
    return calculateInstallment(amountPiastres, selectedTenor);
  }, [amountPiastres, selectedTenor]);

  const allCalculations = useMemo(() => {
    return VALU_TENORS.map(tenor => ({
      tenor,
      calculation: calculateInstallment(amountPiastres, tenor),
    }));
  }, [amountPiastres]);

  return {
    selectedTenor,
    setSelectedTenor,
    calculation,
    allCalculations,
    VALU_TENORS,
  };
}

export default ValuCalculator;
