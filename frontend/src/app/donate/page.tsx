/**
 * CONFIT Donation Page
 * Premium, trust-focused donation experience
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Heart,
  Shield,
  Clock,
  Gift,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  Star,
  Users,
  Leaf,
} from 'lucide-react';
import { getAuthToken } from '@/lib/auth';
import { getPublicApiBaseUrl } from '@/lib/env';

const API_BASE_URL = getPublicApiBaseUrl();

// ============================================
// TYPES
// ============================================

interface DonationConfig {
  min_amount: number;
  max_amount: number;
  preset_amounts: number[];
  enable_custom_amounts: boolean;
  hero_title: string;
  hero_subtitle: string;
  benefits: Array<{
    title: string;
    description: string;
  }>;
  default_expiry_days: number | null;
}

interface DonationState {
  id: string;
  amount: number;
  status: string;
  client_secret: string | null;
  payment_intent_id: string | null;
  coupon_code?: string;
  credit?: {
    total_credit?: number;
    expires_at?: string;
  };
}

// ============================================
// DONATION PAGE COMPONENT
// ============================================

export default function DonatePage() {
  const [config, setConfig] = useState<DonationConfig | null>(null);
  const [selectedAmount, setSelectedAmount] = useState<number | null>(null);
  const [customAmount, setCustomAmount] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [donation, setDonation] = useState<DonationState | null>(null);
  const [step, setStep] = useState<'amount' | 'confirm' | 'payment' | 'success'>('amount');

  // Fetch config
  useEffect(() => {
    fetchDonationConfig();
  }, []);

  const fetchDonationConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/donations/config`);
      if (!response.ok) throw new Error('Failed to load config');
      const data = await response.json();
      setConfig(data);
      // Set default selection
      if (data.preset_amounts?.length > 0) {
        setSelectedAmount(data.preset_amounts[2] || data.preset_amounts[0]);
      }
    } catch (err) {
      console.error('Failed to load donation config:', err);
      // Set defaults
      setConfig({
        min_amount: 1,
        max_amount: 10000,
        preset_amounts: [10, 25, 50, 100],
        enable_custom_amounts: true,
        hero_title: 'Support the Future of Fashion',
        hero_subtitle: 'Your donation helps us build sustainable, inclusive fashion technology.',
        benefits: [
          { title: '100% Shopping Credit', description: 'Every dollar donated becomes store credit' },
          { title: 'Exclusive Access', description: 'Early access to new collections' },
          { title: 'Support Sustainability', description: 'Help reduce fashion waste' },
        ],
        default_expiry_days: 365,
      });
      setSelectedAmount(50);
    } finally {
      setIsLoading(false);
    }
  };

  const getDonationAmount = useCallback(() => {
    if (selectedAmount !== null) return selectedAmount;
    if (customAmount) {
      const parsed = parseFloat(customAmount);
      return isNaN(parsed) ? 0 : parsed;
    }
    return 0;
  }, [selectedAmount, customAmount]);

  const handleAmountSelect = (amount: number) => {
    setSelectedAmount(amount);
    setCustomAmount('');
    setError(null);
  };

  const handleCustomAmountChange = (value: string) => {
    setCustomAmount(value);
    setSelectedAmount(null);
    setError(null);
  };

  const validateAmount = (): boolean => {
    const amount = getDonationAmount();
    if (!config) return false;

    if (amount < config.min_amount) {
      setError(`Minimum donation is $${config.min_amount}`);
      return false;
    }
    if (amount > config.max_amount) {
      setError(`Maximum donation is $${config.max_amount}`);
      return false;
    }
    return true;
  };

  const handleContinue = () => {
    if (!validateAmount()) return;
    setStep('confirm');
  };

  const handleConfirmAndPay = async () => {
    if (!validateAmount()) return;

    setIsProcessing(true);
    setError(null);

    try {
      const token = getAuthToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/api/donations`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          amount: getDonationAmount(),
          payment_method: 'card',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create donation');
      }

      const data = await response.json();
      setDonation(data);

      // If we have a Stripe client secret, redirect to payment
      if (data.client_secret) {
        setStep('payment');
        // TODO: Integrate Stripe Payment Element
        // For now, simulate payment success in dev mode
        if (data.payment_intent_id?.startsWith('pi_mock_')) {
          await handleMockPaymentConfirm(data);
        } else {
          // Real Stripe - would integrate Stripe.js here
          await handleStripePayment(data);
        }
      }
    } catch (err) {
      console.error('Donation error:', err);
      setError(err instanceof Error ? err.message : 'Failed to process donation');
      setStep('amount');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleStripePayment = async (donationData: DonationState) => {
    // In production, this would use Stripe.js Payment Element
    // For now, show payment processing UI
    setError('Stripe integration requires Stripe.js. Payment intent created: ' + donationData.payment_intent_id);
    setStep('payment');
  };

  const handleMockPaymentConfirm = async (donationData: DonationState) => {
    try {
      const token = getAuthToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(
        `${API_BASE_URL}/api/donations/${donationData.id}/confirm`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({
            payment_intent_id: donationData.payment_intent_id,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to confirm payment');
      }

      const result = await response.json();
      setDonation({
        ...donationData,
        status: 'completed',
        ...result.donation,
      });
      setStep('success');
    } catch (err) {
      console.error('Payment confirmation error:', err);
      setError(err instanceof Error ? err.message : 'Payment confirmation failed');
      setStep('amount');
    }
  };

  const handleBack = () => {
    setStep(step === 'confirm' ? 'amount' : step === 'payment' ? 'confirm' : step);
    setError(null);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // ============================================
  // RENDER
  // ============================================

  if (isLoading) {
    return (
      <MainLayout>
        <div className="min-h-[80vh] flex items-center justify-center">
          <div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
        {/* Hero Section */}
        <section className="relative py-16 md:py-24 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-accent/5 via-transparent to-primary/5" />
          <div className="container mx-auto px-4 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <Badge variant="outline" className="mb-6 px-4 py-1.5 text-sm border-accent/30 text-accent">
                <Heart className="w-4 h-4 mr-2" />
                Support Our Mission
              </Badge>
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-serif font-bold text-foreground mb-6">
                {config?.hero_title || 'Support the Future of Fashion'}
              </h1>
              <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
                {config?.hero_subtitle || 'Your donation helps us build sustainable, inclusive fashion technology.'}
              </p>
            </div>
          </div>
        </section>

        {/* Main Content */}
        <section className="py-12 md:py-16">
          <div className="container mx-auto px-4">
            <div className="grid lg:grid-cols-2 gap-8 lg:gap-12 max-w-6xl mx-auto">
              {/* Left: Donation Form */}
              <div className="order-2 lg:order-1">
                <Card className="border-2 border-border/50 shadow-xl bg-card/80 backdrop-blur-sm">
                  <CardHeader className="border-b border-border/50">
                    <CardTitle className="text-2xl font-serif">
                      {step === 'success' ? 'Thank You!' : 'Make a Donation'}
                    </CardTitle>
                    <CardDescription>
                      {step === 'success'
                        ? 'Your support means everything to us'
                        : 'Choose an amount and complete your secure donation'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-6">
                    {/* Error Alert */}
                    {error && (
                      <Alert variant="destructive" className="mb-6">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    )}

                    {/* Success State */}
                    {step === 'success' && donation ? (
                      <DonationSuccess
                        amount={donation.amount}
                        couponCode={donation.coupon_code}
                        creditAmount={donation.credit?.total_credit || donation.amount}
                        expiresAt={donation.credit?.expires_at}
                      />
                    ) : (
                      <>
                        {/* Amount Selection */}
                        {(step === 'amount' || step === 'confirm') && (
                          <>
                            <div className="mb-6">
                              <label className="text-sm font-medium text-foreground mb-3 block">
                                Select Amount
                              </label>
                              <div className="grid grid-cols-3 gap-3">
                                {config?.preset_amounts.map((amount) => (
                                  <button
                                    key={amount}
                                    onClick={() => handleAmountSelect(amount)}
                                    className={`relative py-4 px-4 rounded-lg border-2 transition-all duration-200 font-semibold text-lg
                                      ${selectedAmount === amount
                                        ? 'border-accent bg-accent/10 text-accent shadow-md'
                                        : 'border-border hover:border-accent/50 hover:bg-accent/5'
                                      }`}
                                  >
                                    {formatCurrency(amount)}
                                    {selectedAmount === amount && (
                                      <CheckCircle2 className="absolute -top-1 -right-1 w-5 h-5 text-accent bg-background rounded-full" />
                                    )}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Custom Amount */}
                            {config?.enable_custom_amounts && (
                              <div className="mb-6">
                                <label className="text-sm font-medium text-foreground mb-2 block">
                                  Or enter custom amount
                                </label>
                                <div className="relative">
                                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground font-medium">
                                    $
                                  </span>
                                  <Input
                                    type="number"
                                    placeholder="Enter amount"
                                    value={customAmount}
                                    onChange={(e) => handleCustomAmountChange(e.target.value)}
                                    className="pl-8 h-12 text-lg"
                                    min={config?.min_amount}
                                    max={config?.max_amount}
                                    step="0.01"
                                  />
                                </div>
                                <p className="text-xs text-muted-foreground mt-2">
                                  Min: ${config?.min_amount} · Max: ${config?.max_amount?.toLocaleString()}
                                </p>
                              </div>
                            )}

                            {/* Summary */}
                            <div className="bg-muted/30 rounded-lg p-4 mb-6">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-muted-foreground">Donation Amount</span>
                                <span className="text-xl font-bold text-foreground">
                                  {formatCurrency(getDonationAmount())}
                                </span>
                              </div>
                              <div className="flex justify-between items-center text-sm">
                                <span className="text-muted-foreground">You'll receive</span>
                                <span className="font-semibold text-accent">
                                  {formatCurrency(getDonationAmount())} shopping credit
                                </span>
                              </div>
                            </div>
                          </>
                        )}

                        {/* Confirmation Step */}
                        {step === 'confirm' && (
                          <div className="mb-6 p-4 bg-accent/5 border border-accent/20 rounded-lg">
                            <h4 className="font-semibold text-foreground mb-2">Confirm Your Donation</h4>
                            <ul className="space-y-2 text-sm text-muted-foreground">
                              <li className="flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-accent" />
                                Donation amount: {formatCurrency(getDonationAmount())}
                              </li>
                              <li className="flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-accent" />
                                100% returned as shopping credit
                              </li>
                              <li className="flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-accent" />
                                Credit valid for {config?.default_expiry_days || 365} days
                              </li>
                            </ul>
                          </div>
                        )}

                        {/* Payment Processing */}
                        {step === 'payment' && (
                          <div className="text-center py-8">
                            <Loader2 className="w-12 h-12 animate-spin text-accent mx-auto mb-4" />
                            <p className="text-muted-foreground">Processing your payment...</p>
                          </div>
                        )}

                        {/* Action Buttons */}
                        {step !== 'payment' && step !== 'success' && (
                          <div className="flex gap-3">
                            {step === 'confirm' && (
                              <Button
                                variant="outline"
                                onClick={handleBack}
                                disabled={isProcessing}
                                className="flex-1"
                              >
                                Back
                              </Button>
                            )}
                            <Button
                              variant="hero"
                              onClick={step === 'amount' ? handleContinue : handleConfirmAndPay}
                              disabled={isProcessing || getDonationAmount() <= 0}
                              className="flex-1 h-12 text-lg"
                            >
                              {isProcessing ? (
                                <>
                                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                                  Processing...
                                </>
                              ) : step === 'amount' ? (
                                <>
                                  Continue
                                  <ArrowRight className="w-5 h-5 ml-2" />
                                </>
                              ) : (
                                <>
                                  <Shield className="w-5 h-5 mr-2" />
                                  Donate {formatCurrency(getDonationAmount())}
                                </>
                              )}
                            </Button>
                          </div>
                        )}

                        {/* Trust Indicators */}
                        <div className="mt-6 pt-6 border-t border-border/50">
                          <div className="flex items-center justify-center gap-6 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1.5">
                              <Shield className="w-4 h-4 text-accent" />
                              Secure Payment
                            </span>
                            <span className="flex items-center gap-1.5">
                              <Lock className="w-4 h-4 text-accent" />
                              256-bit SSL
                            </span>
                            <span className="flex items-center gap-1.5">
                              <CheckCircle2 className="w-4 h-4 text-accent" />
                              Instant Credit
                            </span>
                          </div>
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Right: Benefits */}
              <div className="order-1 lg:order-2 space-y-6">
                {/* Benefits Cards */}
                <div className="space-y-4">
                  {config?.benefits?.map((benefit, index) => (
                    <Card key={index} className="border border-border/30 bg-card/50 hover:border-accent/30 transition-colors">
                      <CardContent className="p-5 flex gap-4">
                        <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
                          {index === 0 ? (
                            <Gift className="w-5 h-5 text-accent" />
                          ) : index === 1 ? (
                            <Sparkles className="w-5 h-5 text-accent" />
                          ) : (
                            <Leaf className="w-5 h-5 text-accent" />
                          )}
                        </div>
                        <div>
                          <h4 className="font-semibold text-foreground mb-1">{benefit.title}</h4>
                          <p className="text-sm text-muted-foreground">{benefit.description}</p>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* How It Works */}
                <Card className="border border-border/30 bg-card/50">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">How It Works</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0 text-sm font-bold text-accent">
                        1
                      </div>
                      <div>
                        <p className="font-medium text-foreground">Donate</p>
                        <p className="text-sm text-muted-foreground">Choose any amount you'd like to contribute</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0 text-sm font-bold text-accent">
                        2
                      </div>
                      <div>
                        <p className="font-medium text-foreground">Get Credit</p>
                        <p className="text-sm text-muted-foreground">Receive 100% back as shopping credit instantly</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0 text-sm font-bold text-accent">
                        3
                      </div>
                      <div>
                        <p className="font-medium text-foreground">Shop</p>
                        <p className="text-sm text-muted-foreground">Use your credit on any eligible products</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-4 rounded-lg bg-card/50 border border-border/30">
                    <div className="text-2xl font-bold text-accent">100%</div>
                    <div className="text-xs text-muted-foreground">Credit Back</div>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-card/50 border border-border/30">
                    <div className="text-2xl font-bold text-accent">365</div>
                    <div className="text-xs text-muted-foreground">Days Valid</div>
                  </div>
                  <div className="text-center p-4 rounded-lg bg-card/50 border border-border/30">
                    <div className="text-2xl font-bold text-accent">Instant</div>
                    <div className="text-xs text-muted-foreground">Activation</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </MainLayout>
  );
}

// ============================================
// SUCCESS COMPONENT
// ============================================

function DonationSuccess({
  amount,
  couponCode,
  creditAmount,
  expiresAt,
}: {
  amount: number;
  couponCode?: string;
  creditAmount: number;
  expiresAt?: string;
}) {
  return (
    <div className="text-center py-6">
      <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
        <CheckCircle2 className="w-8 h-8 text-green-600" />
      </div>
      <h3 className="text-2xl font-bold text-foreground mb-2">Thank You!</h3>
      <p className="text-muted-foreground mb-6">
        Your donation of ${amount} has been processed successfully.
      </p>

      <div className="bg-accent/10 border border-accent/20 rounded-lg p-6 mb-6">
        <p className="text-sm text-muted-foreground mb-2">Your Credit Code</p>
        <p className="text-2xl font-mono font-bold text-accent tracking-wider">
          {couponCode || 'DONOR-XXXXXX-XXXX'}
        </p>
        <p className="text-sm text-muted-foreground mt-3">
          ${creditAmount} shopping credit activated
        </p>
        {expiresAt && (
          <p className="text-xs text-muted-foreground mt-1">
            Valid until {new Date(expiresAt).toLocaleDateString()}
          </p>
        )}
      </div>

      <div className="space-y-3">
        <Button variant="hero" className="w-full" asChild>
          <a href="/products">
            Start Shopping
            <ArrowRight className="w-5 h-5 ml-2" />
          </a>
        </Button>
        <Button variant="outline" className="w-full" asChild>
          <a href="/profile/donations">View My Donations</a>
        </Button>
      </div>
    </div>
  );
}

// Lock icon component
function Lock({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}
