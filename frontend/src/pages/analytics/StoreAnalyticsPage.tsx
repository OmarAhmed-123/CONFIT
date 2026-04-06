/**
 * CONFIT Store Analytics Dashboard Page
 * =====================================
 * Analytics dashboard for store managers with KPIs, heatmap, and top products.
 * Access: Store managers and admins only.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Users, ShoppingBag, DollarSign, Eye, RefreshCw,
  MapPin, Clock, Package, AlertTriangle, ShieldAlert,
  Loader2, Store, TrendingUp, ArrowLeft
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { analyticsService } from '@/services/analytics.service';
import type { StoreDashboardData, HeatmapCell } from '@/services/analytics.service';
import {
  KPICard, KPIGrid, ChartWrapper, VisitorHeatmap,
  TopProductsTable, EmptyState, LoadingSpinner
} from '@/components/analytics/AnalyticsSharedComponents';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EASE_LUXURY } from '@/motion';
import { isStoreOwner, isAdmin } from '@/lib/auth/roles';
import { cn } from '@/lib/utils';

// ===========================================
// Store Analytics Page Component
// ===========================================

interface StoreAnalyticsPageProps {
  storeId?: string;
}

export default function StoreAnalyticsPage({ storeId }: StoreAnalyticsPageProps) {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // State
  const [dashboardData, setDashboardData] = useState<StoreDashboardData | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapCell[]>([]);
  const [topViewed, setTopViewed] = useState<Array<{ sku: string; view_count: number }>>([]);
  const [topPurchased, setTopPurchased] = useState<Array<{ sku: string; purchase_count: number; revenue_egp?: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [heatmapDays, setHeatmapDays] = useState(7);
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  // Default store ID (in production, would come from user's assigned store)
  const activeStoreId = storeId || 'store-default';

  // Fetch data
  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, heatmap, topProducts] = await Promise.all([
        analyticsService.getStoreDashboard(activeStoreId),
        analyticsService.getStoreHeatmap(activeStoreId, heatmapDays),
        analyticsService.getStoreTopProducts(activeStoreId, 30, 10),
      ]);

      setDashboardData(dashboard);
      setHeatmapData(heatmap.data);
      setTopViewed(topProducts.top_viewed);
      setTopPurchased(topProducts.top_purchased);
    } catch (err) {
      console.error('Failed to fetch store analytics:', err);
      setError('Failed to load analytics data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [activeStoreId, heatmapDays]);

  // Auth guard
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    const authorized = isStoreOwner(user) || isAdmin(user);
    setIsAuthorized(authorized);
    if (authorized) {
      fetchDashboardData();
    }
  }, [authLoading, isAuthenticated, router, user, fetchDashboardData]);

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
          <span className="text-sm text-muted-foreground">Loading dashboard...</span>
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
            Access Restricted
          </h2>
          <p className="text-muted-foreground mb-6">
            This dashboard is exclusively for store managers and administrators.
          </p>
          <Button onClick={() => router.push('/')} className="bg-accent text-accent-foreground">
            Return to Home
          </Button>
        </motion.div>
      </div>
    );
  }

  // Error state
  if (error && !dashboardData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <EmptyState
          icon={<AlertTriangle className="h-8 w-8 text-red-400" />}
          title="Failed to Load Analytics"
          description={error}
          action={
            <Button onClick={fetchDashboardData} variant="outline">
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
                <Store className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-foreground font-sans tracking-tight">
                  Store Analytics
                </h1>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{dashboardData?.store_name || 'Loading...'}</span>
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
              onClick={fetchDashboardData}
              disabled={loading}
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </motion.div>

        {/* KPI Grid */}
        <div className="mb-8">
          <KPIGrid columns={4}>
            <KPICard
              title="Visitors Today"
              value={dashboardData?.visitors_today || 0}
              icon={<Users className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Conversion Rate"
              value={dashboardData?.conversion_rate || 0}
              format="percent"
              icon={<TrendingUp className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Revenue Today"
              value={dashboardData?.revenue_today_egp || 0}
              format="currency"
              icon={<DollarSign className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Orders Today"
              value={dashboardData?.orders_today || 0}
              icon={<ShoppingBag className="h-5 w-5" />}
              loading={loading}
            />
          </KPIGrid>
        </div>

        {/* Secondary KPIs */}
        <div className="mb-8">
          <KPIGrid columns={4}>
            <KPICard
              title="Visitors (7 Days)"
              value={dashboardData?.visitors_7d || 0}
              icon={<Eye className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Try-On to Purchase"
              value={dashboardData?.try_on_to_purchase_rate || 0}
              format="percent"
              icon={<Package className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Revenue (7 Days)"
              value={dashboardData?.revenue_7d_egp || 0}
              format="currency"
              icon={<DollarSign className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Coupon Redemption"
              value={dashboardData?.coupon_redemption_rate || 0}
              format="percent"
              icon={<Badge className="h-5 w-5" />}
              loading={loading}
            />
          </KPIGrid>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Visitor Heatmap */}
          <ChartWrapper
            title="Visitor Heatmap"
            subtitle="Peak hours by day of week"
            loading={loading}
            action={
              <Select value={String(heatmapDays)} onValueChange={(v) => setHeatmapDays(Number(v))}>
                <SelectTrigger className="w-[120px] h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">Last 7 days</SelectItem>
                  <SelectItem value="14">Last 14 days</SelectItem>
                  <SelectItem value="30">Last 30 days</SelectItem>
                </SelectContent>
              </Select>
            }
          >
            <VisitorHeatmap data={heatmapData} />
          </ChartWrapper>

          {/* Return Reasons */}
          <ChartWrapper
            title="Return Reason Breakdown"
            subtitle="Why customers return items"
            loading={loading}
          >
            <div className="space-y-4">
              {dashboardData?.return_reason_breakdown && (
                <>
                  {Object.entries(dashboardData.return_reason_breakdown).map(([reason, count]) => {
                    const total = Object.values(dashboardData.return_reason_breakdown).reduce((a, b) => a + b, 0);
                    const percentage = total > 0 ? (count / total) * 100 : 0;
                    return (
                      <div key={reason} className="flex items-center gap-4">
                        <div className="w-24 text-sm capitalize text-muted-foreground">
                          {reason.replace('_', ' ')}
                        </div>
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${percentage}%` }}
                            transition={{ duration: 0.5, ease: EASE_LUXURY }}
                            className="h-full bg-accent rounded-full"
                          />
                        </div>
                        <div className="w-16 text-sm text-right text-muted-foreground">
                          {percentage.toFixed(0)}%
                        </div>
                      </div>
                    );
                  })}
                </>
              )}
            </div>
          </ChartWrapper>
        </div>

        {/* Top Products Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="text-lg font-semibold">Top Products</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="viewed" className="w-full">
                <TabsList className="mb-4">
                  <TabsTrigger value="viewed">Most Viewed</TabsTrigger>
                  <TabsTrigger value="purchased">Most Purchased</TabsTrigger>
                </TabsList>
                <TabsContent value="viewed">
                  <TopProductsTable
                    products={topViewed}
                    type="viewed"
                    loading={loading}
                  />
                </TabsContent>
                <TabsContent value="purchased">
                  <TopProductsTable
                    products={topPurchased}
                    type="purchased"
                    loading={loading}
                  />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>

        {/* Additional Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <Clock className="h-5 w-5 text-accent" />
                <span className="text-sm text-muted-foreground">Avg BOPIS Pickup Time</span>
              </div>
              <p className="text-2xl font-bold">
                {dashboardData?.bopis_avg_pickup_time_minutes
                  ? `${dashboardData.bopis_avg_pickup_time_minutes} min`
                  : 'N/A'}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <DollarSign className="h-5 w-5 text-accent" />
                <span className="text-sm text-muted-foreground">Donor Coupon Attribution</span>
              </div>
              <p className="text-2xl font-bold">
                {dashboardData?.donor_coupon_attribution_egp?.toLocaleString() || 0} EGP
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <ShoppingBag className="h-5 w-5 text-accent" />
                <span className="text-sm text-muted-foreground">Orders (30 Days)</span>
              </div>
              <p className="text-2xl font-bold">
                {dashboardData?.orders_30d?.toLocaleString() || 0}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
