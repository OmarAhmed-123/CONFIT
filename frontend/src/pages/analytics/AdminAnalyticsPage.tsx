/**
 * CONFIT Admin Platform Analytics Page
 * =====================================
 * Platform-wide analytics dashboard for administrators.
 * Access: Admin only.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Users, DollarSign, ShoppingBag, Store, Building2,
  TrendingUp, AlertTriangle, Gift, ArrowLeft,
  RefreshCw, Loader2, ShieldAlert, BarChart3,
  Activity, Globe, Target
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { analyticsService } from '@/services/analytics.service';
import type { AdminOverviewData, FunnelStage } from '@/services/analytics.service';
import {
  KPICard, KPIGrid, ChartWrapper, DonutChart,
  LineChartComponent, RegionalSalesChart, EmptyState
} from '@/components/analytics/AnalyticsSharedComponents';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { EASE_LUXURY } from '@/motion';
import { isAdmin } from '@/lib/auth/roles';
import { cn } from '@/lib/utils';

// ===========================================
// Admin Analytics Page Component
// ===========================================

export default function AdminAnalyticsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // State
  const [overviewData, setOverviewData] = useState<AdminOverviewData | null>(null);
  const [funnelData, setFunnelData] = useState<FunnelStage[]>([]);
  const [geographicData, setGeographicData] = useState<{ users_by_country: Record<string, number>; orders_by_city_egypt: Record<string, number> } | null>(null);
  const [revenueData, setRevenueData] = useState<Array<{ period?: string; orders: number; revenue_egp: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [revenueGroupBy, setRevenueGroupBy] = useState<'day' | 'week' | 'month'>('day');

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overview, funnel, geographic, revenue] = await Promise.all([
        analyticsService.getAdminOverview(),
        analyticsService.getConversionFunnel(30),
        analyticsService.getGeographicDistribution(30),
        analyticsService.getRevenueAnalytics(30, revenueGroupBy),
      ]);

      setOverviewData(overview);
      setFunnelData(funnel.funnel);
      setGeographicData(geographic);
      setRevenueData(revenue.data);
    } catch (err) {
      console.error('Failed to fetch admin analytics:', err);
      setError('Failed to load platform analytics. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [revenueGroupBy]);

  // Auth guard
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    const authorized = isAdmin(user);
    setIsAuthorized(authorized);
    if (authorized) {
      fetchData();
    }
  }, [authLoading, isAuthenticated, router, user, fetchData]);

  // Loading state
  if (authLoading || isAuthorized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="text-sm text-muted-foreground">Loading admin dashboard...</span>
        </motion.div>
      </div>
    );
  }

  // Unauthorized state
  if (!isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
          className="text-center max-w-md"
        >
          <div className="h-16 w-16 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-6">
            <ShieldAlert className="h-8 w-8 text-red-400" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-3 font-sans">
            Admin Access Required
          </h2>
          <p className="text-muted-foreground mb-6">
            This dashboard is exclusively for administrators.
          </p>
          <Button onClick={() => router.push('/')} className="bg-accent text-accent-foreground">
            Return to Home
          </Button>
        </motion.div>
      </div>
    );
  }

  // Error state
  if (error && !overviewData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <EmptyState
          icon={<AlertTriangle className="h-8 w-8 text-red-400" />}
          title="Failed to Load Analytics"
          description={error}
          action={
            <Button onClick={fetchData} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  // Prepare chart data
  const revenueChartData = revenueData.map(item => ({
    date: item.period || '',
    value: item.revenue_egp,
  }));

  const geographicChartData = geographicData?.orders_by_city_egypt
    ? Object.entries(geographicData.orders_by_city_egypt).map(([city, count]) => ({
        city,
        sales_count: count,
        revenue_egp: count * 500, // Estimate
      }))
    : [];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
        >
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.back()}
              className="mr-2"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center">
                <BarChart3 className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-foreground font-sans tracking-tight">
                  Platform Analytics
                </h1>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Admin Dashboard</span>
                  <span className="text-muted-foreground/40">|</span>
                  <span>{today}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchData}
              disabled={loading}
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </motion.div>

        {/* North Star Metric */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-8"
        >
          <Card className="bg-gradient-to-br from-accent/10 to-accent/5 border-accent/20">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <Target className="h-5 w-5 text-accent" />
                <span className="text-sm text-muted-foreground">North Star Metric</span>
              </div>
              <div className="flex items-baseline gap-2">
                <p className="text-4xl font-bold text-foreground">
                  {overviewData?.confident_purchases_per_month?.toLocaleString() || 0}
                </p>
                <p className="text-muted-foreground">confident purchases this month</p>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Orders not returned within 30 days (high confidence in fit/quality)
              </p>
            </CardContent>
          </Card>
        </motion.div>

        {/* Primary KPI Grid */}
        <div className="mb-8">
          <KPIGrid columns={4}>
            <KPICard
              title="Daily Active Users"
              value={overviewData?.dau || 0}
              icon={<Users className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Monthly Active Users"
              value={overviewData?.mau || 0}
              icon={<Activity className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Total Revenue (Month)"
              value={overviewData?.total_revenue_egp || 0}
              format="currency"
              icon={<DollarSign className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Total Orders (Month)"
              value={overviewData?.total_orders || 0}
              icon={<ShoppingBag className="h-5 w-5" />}
              loading={loading}
            />
          </KPIGrid>
        </div>

        {/* Secondary KPIs */}
        <div className="mb-8">
          <KPIGrid columns={4}>
            <KPICard
              title="Total Users"
              value={overviewData?.total_users || 0}
              icon={<Users className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Active Stores"
              value={overviewData?.active_stores || 0}
              icon={<Store className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Active Brands"
              value={overviewData?.active_brands || 0}
              icon={<Building2 className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Fraud Flags"
              value={overviewData?.fraud_flags_count || 0}
              icon={<AlertTriangle className="h-5 w-5" />}
              loading={loading}
            />
          </KPIGrid>
        </div>

        {/* Tabs Section */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="retention">Retention</TabsTrigger>
            <TabsTrigger value="funnel">Funnel</TabsTrigger>
            <TabsTrigger value="revenue">Revenue</TabsTrigger>
            <TabsTrigger value="geographic">Geographic</TabsTrigger>
            <TabsTrigger value="coupons">Coupons</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* NPS & CSAT */}
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Customer Satisfaction</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-muted-foreground">NPS Score</span>
                      <span className="font-semibold">
                        {overviewData?.nps_score !== null
                          ? `${overviewData?.nps_score?.toFixed(1)}`
                          : 'N/A'}
                      </span>
                    </div>
                    {overviewData?.nps_score !== null && (
                      <Progress
                        value={((overviewData?.nps_score || 0) + 100) / 2}
                        className="h-2"
                      />
                    )}
                  </div>
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-muted-foreground">CSAT Score</span>
                      <span className="font-semibold">
                        {overviewData?.csat_score !== null
                          ? `${overviewData?.csat_score?.toFixed(1)}/5`
                          : 'N/A'}
                      </span>
                    </div>
                    {overviewData?.csat_score !== null && (
                      <Progress
                        value={((overviewData?.csat_score || 0) / 5) * 100}
                        className="h-2"
                      />
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Weekly Active Users */}
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">User Engagement</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">{overviewData?.dau || 0}</p>
                      <p className="text-xs text-muted-foreground">DAU</p>
                    </div>
                    <div className="p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">{overviewData?.wau || 0}</p>
                      <p className="text-xs text-muted-foreground">WAU</p>
                    </div>
                    <div className="p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">{overviewData?.mau || 0}</p>
                      <p className="text-xs text-muted-foreground">MAU</p>
                    </div>
                  </div>
                  <div className="mt-4 p-3 bg-accent/10 rounded-lg">
                    <p className="text-sm text-muted-foreground">
                      DAU/MAU Ratio: {overviewData?.mau ? ((overviewData?.dau || 0) / overviewData.mau * 100).toFixed(1) : 0}%
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Higher ratio indicates better daily engagement
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Retention Tab */}
          <TabsContent value="retention">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="text-lg font-semibold">Retention Cohorts</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cohort Date</TableHead>
                      <TableHead className="text-right">Users</TableHead>
                      <TableHead className="text-right">D1 Retention</TableHead>
                      <TableHead className="text-right">D7 Retention</TableHead>
                      <TableHead className="text-right">D30 Retention</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overviewData?.retention_cohorts?.map((cohort) => (
                      <TableRow key={cohort.cohort_date}>
                        <TableCell className="font-medium">{cohort.cohort_date}</TableCell>
                        <TableCell className="text-right">{cohort.users_count}</TableCell>
                        <TableCell className="text-right">
                          <Badge variant={cohort.d1_retention > 30 ? 'default' : 'secondary'}>
                            {cohort.d1_retention.toFixed(1)}%
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge variant={cohort.d7_retention > 15 ? 'default' : 'secondary'}>
                            {cohort.d7_retention.toFixed(1)}%
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge variant={cohort.d30_retention > 5 ? 'default' : 'secondary'}>
                            {cohort.d30_retention.toFixed(1)}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Funnel Tab */}
          <TabsContent value="funnel">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="text-lg font-semibold">Conversion Funnel (30 Days)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {funnelData.map((stage, index) => {
                    const maxUsers = funnelData[0]?.unique_users || 1;
                    const width = (stage.unique_users / maxUsers) * 100;
                    
                    return (
                      <div key={stage.stage} className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{stage.stage}</span>
                          <div className="text-right">
                            <span className="font-semibold">{stage.unique_users.toLocaleString()}</span>
                            {stage.conversion_from_previous !== null && (
                              <span className="text-sm text-muted-foreground ml-2">
                                ({stage.conversion_from_previous.toFixed(1)}% from previous)
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="h-8 bg-muted rounded-lg overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${width}%` }}
                            transition={{ duration: 0.5, delay: index * 0.1 }}
                            className="h-full bg-accent rounded-lg flex items-center justify-end pr-2"
                          >
                            {width > 10 && (
                              <span className="text-xs text-accent-foreground font-medium">
                                {width.toFixed(0)}%
                              </span>
                            )}
                          </motion.div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Revenue Tab */}
          <TabsContent value="revenue">
            <ChartWrapper
              title="Revenue Trend"
              subtitle="Daily revenue over time"
              loading={loading}
              action={
                <Select value={revenueGroupBy} onValueChange={(v) => setRevenueGroupBy(v as 'day' | 'week' | 'month')}>
                  <SelectTrigger className="w-[120px] h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="day">Daily</SelectItem>
                    <SelectItem value="week">Weekly</SelectItem>
                    <SelectItem value="month">Monthly</SelectItem>
                  </SelectContent>
                </Select>
              }
            >
              <LineChartComponent
                data={revenueChartData}
                lines={[{ key: 'value', color: 'hsl(var(--accent))', name: 'Revenue (EGP)' }]}
              />
            </ChartWrapper>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <p className="text-sm text-muted-foreground mb-1">Total Revenue</p>
                  <p className="text-2xl font-bold">
                    {revenueData.reduce((sum, d) => sum + d.revenue_egp, 0).toLocaleString()} EGP
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <p className="text-sm text-muted-foreground mb-1">Total Orders</p>
                  <p className="text-2xl font-bold">
                    {revenueData.reduce((sum, d) => sum + d.orders, 0).toLocaleString()}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <p className="text-sm text-muted-foreground mb-1">Avg Order Value</p>
                  <p className="text-2xl font-bold">
                    {revenueData.reduce((sum, d) => sum + d.revenue_egp, 0) / 
                      (revenueData.reduce((sum, d) => sum + d.orders, 0) || 1)
                    ).toFixed(0)} EGP
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Geographic Tab */}
          <TabsContent value="geographic">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartWrapper
                title="Orders by City (Egypt)"
                subtitle="Regional distribution"
                loading={loading}
              >
                <RegionalSalesChart data={geographicChartData} loading={loading} />
              </ChartWrapper>

              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Users by Country</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {geographicData?.users_by_country &&
                      Object.entries(geographicData.users_by_country).map(([country, count]) => (
                        <div key={country} className="flex justify-between items-center p-3 bg-muted/30 rounded-lg">
                          <div className="flex items-center gap-2">
                            <Globe className="h-4 w-4 text-muted-foreground" />
                            <span>{country}</span>
                          </div>
                          <span className="font-semibold">{count.toLocaleString()}</span>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Coupons Tab */}
          <TabsContent value="coupons">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Gift className="h-4 w-4 text-green-500" />
                    <span className="text-sm text-muted-foreground">Active Coupons</span>
                  </div>
                  <p className="text-2xl font-bold">
                    {overviewData?.coupon_ecosystem_health?.active_coupons || 0}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Gift className="h-4 w-4 text-blue-500" />
                    <span className="text-sm text-muted-foreground">Redeemed</span>
                  </div>
                  <p className="text-2xl font-bold">
                    {overviewData?.coupon_ecosystem_health?.redeemed_coupons || 0}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Gift className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Expired</span>
                  </div>
                  <p className="text-2xl font-bold">
                    {overviewData?.coupon_ecosystem_health?.expired_coupons || 0}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign className="h-4 w-4 text-accent" />
                    <span className="text-sm text-muted-foreground">Total Discount</span>
                  </div>
                  <p className="text-2xl font-bold">
                    {overviewData?.coupon_ecosystem_health?.total_discount_egp?.toLocaleString() || 0} EGP
                  </p>
                </CardContent>
              </Card>
            </div>

            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="text-lg font-semibold">Coupon Ecosystem Health</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-6">
                  <p className="text-sm text-muted-foreground mb-4">
                    The coupon ecosystem enables donors to support beneficiaries with discount vouchers
                  </p>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-green-500/10 rounded-lg">
                      <p className="text-2xl font-bold text-green-500">
                        {overviewData?.coupon_ecosystem_health?.active_coupons || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">Active</p>
                    </div>
                    <div className="p-4 bg-blue-500/10 rounded-lg">
                      <p className="text-2xl font-bold text-blue-500">
                        {overviewData?.coupon_ecosystem_health?.redeemed_coupons || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">Redeemed</p>
                    </div>
                    <div className="p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">
                        {overviewData?.coupon_ecosystem_health?.expired_coupons || 0}
                      </p>
                      <p className="text-xs text-muted-foreground">Expired</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
