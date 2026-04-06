/**
 * CONFIT Donor Dashboard
 * User profile section for viewing donations, credits, and redemption history
 */

'use client';

import React, { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Heart,
  Gift,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
  Copy,
  Calendar,
  DollarSign,
  TrendingUp,
  ShoppingBag,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { getAuthToken } from '@/lib/auth';
import { getPublicApiBaseUrl } from '@/lib/env';

const API_BASE_URL = getPublicApiBaseUrl();

// ============================================
// TYPES
// ============================================

interface DonationStats {
  total_donations: number;
  total_donated: number;
  total_credit_earned: number;
  total_credit_used: number;
  total_credit_remaining: number;
  active_credits: number;
  total_redemptions: number;
}

interface Credit {
  id: string;
  coupon_code: string;
  total_credit: number;
  remaining_credit: number;
  used_credit: number;
  status: string;
  expires_at: string | null;
  created_at: string;
  is_active: boolean;
}

interface Donation {
  id: string;
  amount: number;
  status: string;
  payment_method: string;
  created_at: string;
  completed_at: string | null;
  credit: {
    coupon_code: string;
    total_credit: number;
    remaining_credit: number;
    status: string;
    expires_at: string | null;
  } | null;
}

interface Redemption {
  id: string;
  amount_used: number;
  order_id: string | null;
  product_name: string | null;
  created_at: string;
}

// ============================================
// DONOR DASHBOARD COMPONENT
// ============================================

export default function DonorDashboardPage() {
  const [stats, setStats] = useState<DonationStats | null>(null);
  const [credits, setCredits] = useState<Credit[]>([]);
  const [donations, setDonations] = useState<Donation[]>([]);
  const [redemptions, setRedemptions] = useState<Redemption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const token = getAuthToken();
      if (!token) {
        window.location.href = '/login?redirect=/profile/donations';
        return;
      }

      const headers: Record<string, string> = {
        'Authorization': `Bearer ${token}`,
      };

      // Fetch all data in parallel
      const [statsRes, creditsRes, donationsRes, redemptionsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/donations/stats`, { headers }),
        fetch(`${API_BASE_URL}/api/donations/credits?active_only=false`, { headers }),
        fetch(`${API_BASE_URL}/api/donations/history?limit=20`, { headers }),
        fetch(`${API_BASE_URL}/api/donations/redemptions?limit=20`, { headers }),
      ]);

      if (!statsRes.ok) throw new Error('Failed to load stats');

      const [statsData, creditsData, donationsData, redemptionsData] = await Promise.all([
        statsRes.json(),
        creditsRes.ok ? creditsRes.json() : [],
        donationsRes.ok ? donationsRes.json() : [],
        redemptionsRes.ok ? redemptionsRes.json() : [],
      ]);

      setStats(statsData);
      setCredits(creditsData);
      setDonations(donationsData);
      setRedemptions(redemptionsData);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const copyCouponCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const getDaysUntilExpiry = (expiresAt: string | null) => {
    if (!expiresAt) return null;
    const expiry = new Date(expiresAt);
    const now = new Date();
    const days = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
      active: { variant: 'default', label: 'Active' },
      depleted: { variant: 'secondary', label: 'Depleted' },
      expired: { variant: 'destructive', label: 'Expired' },
      cancelled: { variant: 'outline', label: 'Cancelled' },
      completed: { variant: 'default', label: 'Completed' },
      pending: { variant: 'outline', label: 'Pending' },
      failed: { variant: 'destructive', label: 'Failed' },
    };

    const config = statusConfig[status] || { variant: 'outline', label: status };
    return <Badge variant={config.variant}>{config.label}</Badge>;
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
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 py-8">
        <div className="container mx-auto px-4 max-w-6xl">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-serif font-bold text-foreground mb-2">
              Donor Dashboard
            </h1>
            <p className="text-muted-foreground">
              Track your donations, credits, and redemption history
            </p>
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Stats Overview */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <Card className="border border-border/30">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                      <Heart className="w-5 h-5 text-accent" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">
                        {stats.total_donations}
                      </p>
                      <p className="text-xs text-muted-foreground">Donations</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border border-border/30">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                      <DollarSign className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">
                        {formatCurrency(stats.total_donated)}
                      </p>
                      <p className="text-xs text-muted-foreground">Total Donated</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border border-border/30">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <Gift className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">
                        {formatCurrency(stats.total_credit_remaining)}
                      </p>
                      <p className="text-xs text-muted-foreground">Available Credit</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border border-border/30">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                      <ShoppingBag className="w-5 h-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-foreground">
                        {formatCurrency(stats.total_credit_used)}
                      </p>
                      <p className="text-xs text-muted-foreground">Credit Used</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Main Content Tabs */}
          <Tabs defaultValue="credits" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 max-w-md">
              <TabsTrigger value="credits">Credits</TabsTrigger>
              <TabsTrigger value="donations">Donations</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            {/* Credits Tab */}
            <TabsContent value="credits" className="space-y-4">
              {credits.length === 0 ? (
                <Card className="border border-border/30">
                  <CardContent className="py-12 text-center">
                    <Gift className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-foreground mb-2">
                      No Credits Yet
                    </h3>
                    <p className="text-muted-foreground mb-6">
                      Make a donation to receive shopping credit
                    </p>
                    <Button variant="hero" asChild>
                      <a href="/donate">
                        Make a Donation
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </a>
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {credits.map((credit) => (
                    <Card
                      key={credit.id}
                      className={`border ${
                        credit.is_active
                          ? 'border-accent/30 bg-accent/5'
                          : 'border-border/30'
                      }`}
                    >
                      <CardContent className="pt-6">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-3">
                              <code className="text-lg font-mono font-bold text-accent tracking-wider">
                                {credit.coupon_code}
                              </code>
                              {getStatusBadge(credit.status)}
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => copyCouponCode(credit.coupon_code)}
                                className="h-8 w-8"
                              >
                                <Copy className="w-4 h-4" />
                              </Button>
                              {copiedCode === credit.coupon_code && (
                                <span className="text-xs text-green-600">Copied!</span>
                              )}
                            </div>

                            <div className="flex items-center gap-6 text-sm">
                              <div>
                                <span className="text-muted-foreground">Total: </span>
                                <span className="font-semibold">{formatCurrency(credit.total_credit)}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Remaining: </span>
                                <span className="font-semibold text-accent">
                                  {formatCurrency(credit.remaining_credit)}
                                </span>
                              </div>
                              {credit.expires_at && (
                                <div className="flex items-center gap-1.5 text-muted-foreground">
                                  <Clock className="w-4 h-4" />
                                  <span>
                                    {getDaysUntilExpiry(credit.expires_at)} days left
                                  </span>
                                </div>
                              )}
                            </div>

                            {/* Progress Bar */}
                            {credit.status === 'active' && (
                              <div className="mt-3">
                                <Progress
                                  value={(credit.remaining_credit / credit.total_credit) * 100}
                                  className="h-2"
                                />
                                <p className="text-xs text-muted-foreground mt-1">
                                  {formatCurrency(credit.used_credit)} used ·{' '}
                                  {formatCurrency(credit.remaining_credit)} remaining
                                </p>
                              </div>
                            )}
                          </div>

                          {credit.is_active && (
                            <Button variant="hero" asChild>
                              <a href="/products">
                                Shop Now
                                <ArrowRight className="w-4 h-4 ml-2" />
                              </a>
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Donations Tab */}
            <TabsContent value="donations" className="space-y-4">
              {donations.length === 0 ? (
                <Card className="border border-border/30">
                  <CardContent className="py-12 text-center">
                    <Heart className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-foreground mb-2">
                      No Donations Yet
                    </h3>
                    <p className="text-muted-foreground mb-6">
                      Your donation history will appear here
                    </p>
                    <Button variant="hero" asChild>
                      <a href="/donate">
                        Make a Donation
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </a>
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <Card className="border border-border/30">
                  <CardContent className="p-0">
                    <div className="divide-y divide-border/50">
                      {donations.map((donation) => (
                        <div
                          key={donation.id}
                          className="p-4 hover:bg-muted/30 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                                <Heart className="w-5 h-5 text-accent" />
                              </div>
                              <div>
                                <p className="font-semibold text-foreground">
                                  {formatCurrency(donation.amount)} Donation
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  {formatDate(donation.created_at)}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              {getStatusBadge(donation.status)}
                              <ChevronRight className="w-5 h-5 text-muted-foreground" />
                            </div>
                          </div>

                          {donation.credit && donation.status === 'completed' && (
                            <div className="mt-3 ml-14 text-sm text-muted-foreground">
                              Credit: <code className="text-accent">{donation.credit.coupon_code}</code>
                              {' · '}
                              {formatCurrency(donation.credit.remaining_credit)} remaining
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Redemption History Tab */}
            <TabsContent value="history" className="space-y-4">
              {redemptions.length === 0 ? (
                <Card className="border border-border/30">
                  <CardContent className="py-12 text-center">
                    <ShoppingBag className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-foreground mb-2">
                      No Redemptions Yet
                    </h3>
                    <p className="text-muted-foreground">
                      Your credit redemption history will appear here
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <Card className="border border-border/30">
                  <CardContent className="p-0">
                    <div className="divide-y divide-border/50">
                      {redemptions.map((redemption) => (
                        <div
                          key={redemption.id}
                          className="p-4 hover:bg-muted/30 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                                <TrendingUp className="w-5 h-5 text-green-600" />
                              </div>
                              <div>
                                <p className="font-semibold text-foreground">
                                  {formatCurrency(redemption.amount_used)} Redeemed
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  {redemption.product_name || 'Purchase'}
                                  {redemption.order_id && (
                                    <span className="ml-2">
                                      · Order #{redemption.order_id.slice(-8)}
                                    </span>
                                  )}
                                </p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className="text-sm text-muted-foreground">
                                {formatDate(redemption.created_at)}
                              </p>
                              {redemption.order_id && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-xs text-accent"
                                  asChild
                                >
                                  <a href={`/orders/${redemption.order_id}`}>
                                    View Order
                                    <ExternalLink className="w-3 h-3 ml-1" />
                                  </a>
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>

          {/* Quick Actions */}
          <div className="mt-8 flex flex-wrap gap-4">
            <Button variant="hero" asChild>
              <a href="/donate">
                <Heart className="w-4 h-4 mr-2" />
                Make Another Donation
              </a>
            </Button>
            <Button variant="outline" asChild>
              <a href="/products">
                <ShoppingBag className="w-4 h-4 mr-2" />
                Browse Products
              </a>
            </Button>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
