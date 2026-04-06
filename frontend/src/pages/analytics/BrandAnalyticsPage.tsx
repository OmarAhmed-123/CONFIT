/**
 * CONFIT Brand/Factory Analytics Dashboard Page
 * ==============================================
 * Analytics dashboard for brand owners with sales, rejections, and forecasts.
 * Access: Brand managers and admins only.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Package, DollarSign, AlertTriangle, TrendingUp,
  MapPin, BarChart3, ShieldAlert, Loader2,
  Building2, ArrowLeft, RefreshCw, Eye
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { analyticsService } from '@/services/analytics.service';
import type { BrandDashboardData, RegionalSales } from '@/services/analytics.service';
import {
  KPICard, KPIGrid, ChartWrapper, RegionalSalesChart,
  DonutChart, LineChartComponent, EmptyState
} from '@/components/analytics/AnalyticsSharedComponents';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EASE_LUXURY } from '@/motion';
import { isBrandManager, isAdmin } from '@/lib/auth/roles';
import { cn } from '@/lib/utils';

// ===========================================
// Brand Analytics Page Component
// ===========================================

interface BrandAnalyticsPageProps {
  brandId?: string;
}

export default function BrandAnalyticsPage({ brandId }: BrandAnalyticsPageProps) {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // State
  const [dashboardData, setDashboardData] = useState<BrandDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Default brand ID (in production, would come from user's assigned brand)
  const activeBrandId = brandId || 'brand-default';

  // Fetch data
  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const dashboard = await analyticsService.getBrandDashboard(activeBrandId);
      setDashboardData(dashboard);
    } catch (err) {
      console.error('Failed to fetch brand analytics:', err);
      setError('Failed to load analytics data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [activeBrandId]);

  // Auth guard
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    const authorized = isBrandManager(user) || isAdmin(user);
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
            This dashboard is exclusively for brand managers and administrators.
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

  // Prepare chart data
  const rejectionData = dashboardData?.midway_rejections_by_reason
    ? Object.entries(dashboardData.midway_rejections_by_reason).map(([name, value]) => ({
        name: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value,
      }))
    : [];

  const forecastChartData = dashboardData?.forecast_next_30d?.map(item => ({
    date: item.date,
    predicted: item.predicted_sales,
    lower: item.confidence_lower,
    upper: item.confidence_upper,
  })) || [];

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
                <Building2 className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-foreground font-sans tracking-tight">
                  Brand Analytics
                </h1>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{dashboardData?.brand_name || 'Loading...'}</span>
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
              title="Products Sold (30 Days)"
              value={dashboardData?.products_sold_30d || 0}
              icon={<Package className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Outfit-to-Purchase Ratio"
              value={dashboardData?.outfit_to_purchase_ratio || 0}
              format="percent"
              icon={<TrendingUp className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Midway Rejections"
              value={dashboardData?.midway_rejections_count || 0}
              icon={<AlertTriangle className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Total Products Sold"
              value={dashboardData?.products_sold_total || 0}
              icon={<BarChart3 className="h-5 w-5" />}
              loading={loading}
            />
          </KPIGrid>
        </div>

        {/* Tabs Section */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="rejections">Quality Control</TabsTrigger>
            <TabsTrigger value="regional">Regional Sales</TabsTrigger>
            <TabsTrigger value="forecast">Forecast</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* SKU Breakdown */}
              <ChartWrapper
                title="Top Selling SKUs"
                subtitle="By quantity sold"
                loading={loading}
              >
                <div className="space-y-3">
                  {dashboardData?.sku_breakdown?.slice(0, 5).map((item, index) => (
                    <motion.div
                      key={item.sku}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center justify-between p-3 bg-muted/30 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-sm">{item.sku}</p>
                        {item.product_name && (
                          <p className="text-xs text-muted-foreground">{item.product_name}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="font-semibold">{item.quantity_sold}</p>
                        <p className="text-xs text-muted-foreground">{item.revenue_egp.toLocaleString()} EGP</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </ChartWrapper>

              {/* Most Styled With */}
              <ChartWrapper
                title="Most Styled With"
                subtitle="Products frequently styled together"
                loading={loading}
              >
                <div className="space-y-3">
                  {dashboardData?.most_styled_with?.slice(0, 5).map((item, index) => (
                    <motion.div
                      key={item.product_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center justify-between p-3 bg-muted/30 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-sm">{item.product_name || item.product_id}</p>
                        <p className="text-xs text-muted-foreground">{item.brand_name}</p>
                      </div>
                      <Badge variant="secondary">
                        {item.styled_together_count} times
                      </Badge>
                    </motion.div>
                  ))}
                </div>
              </ChartWrapper>
            </div>
          </TabsContent>

          {/* Rejections Tab */}
          <TabsContent value="rejections">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartWrapper
                title="Rejection Breakdown by Stage"
                subtitle="Quality control issues"
                loading={loading}
              >
                <DonutChart data={rejectionData} />
              </ChartWrapper>

              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Return Reduction</CardTitle>
                </CardHeader>
                <CardContent>
                  {dashboardData?.return_reduction_delta !== null ? (
                    <div className="text-center py-6">
                      <div className={cn(
                        "text-4xl font-bold mb-2",
                        dashboardData.return_reduction_delta >= 0 ? "text-green-500" : "text-red-500"
                      )}>
                        {dashboardData.return_reduction_delta >= 0 ? '+' : ''}
                        {dashboardData.return_reduction_delta}%
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Change in return rate vs. previous period
                      </p>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-muted-foreground">
                      No data available
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Regional Tab */}
          <TabsContent value="regional">
            <ChartWrapper
              title="Regional Sales Distribution"
              subtitle="Sales by city in Egypt"
              loading={loading}
            >
              <RegionalSalesChart
                data={dashboardData?.regional_heatmap_egypt || []}
                loading={loading}
              />
            </ChartWrapper>

            <div className="mt-6">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">City Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>City</TableHead>
                        <TableHead className="text-right">Sales Count</TableHead>
                        <TableHead className="text-right">Revenue (EGP)</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dashboardData?.regional_heatmap_egypt?.map((city) => (
                        <TableRow key={city.city}>
                          <TableCell className="font-medium">{city.city}</TableCell>
                          <TableCell className="text-right">{city.sales_count}</TableCell>
                          <TableCell className="text-right">{city.revenue_egp.toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Forecast Tab */}
          <TabsContent value="forecast">
            <ChartWrapper
              title="30-Day Sales Forecast"
              subtitle="Predicted sales with confidence interval"
              loading={loading}
            >
              <LineChartComponent
                data={forecastChartData}
                lines={[
                  { key: 'predicted', color: 'hsl(var(--accent))', name: 'Predicted Sales' },
                  { key: 'upper', color: '#82ca9d', name: 'Upper Bound' },
                  { key: 'lower', color: '#8884d8', name: 'Lower Bound' },
                ]}
              />
            </ChartWrapper>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <p className="text-sm text-muted-foreground mb-1">Total Predicted Sales</p>
                  <p className="text-2xl font-bold">
                    {dashboardData?.forecast_next_30d?.reduce((sum, d) => sum + d.predicted_sales, 0).toLocaleString() || 0}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <p className="text-sm text-muted-foreground mb-1">Avg Daily Sales</p>
                  <p className="text-2xl font-bold">
                    {dashboardData?.forecast_next_30d
                      ? Math.round(dashboardData.forecast_next_30d.reduce((sum, d) => sum + d.predicted_sales, 0) / 30).toLocaleString()
                      : 0}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="p-6">
                  <p className="text-sm text-muted-foreground mb-1">Confidence Range</p>
                  <p className="text-2xl font-bold">
                    ±{dashboardData?.forecast_next_30d?.[0]
                      ? Math.round((dashboardData.forecast_next_30d[0].confidence_upper - dashboardData.forecast_next_30d[0].confidence_lower) / 2)
                      : 0}
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
