/**
 * CONFIT User Personal Analytics Page
 * ====================================
 * Personal analytics dashboard for customers with sustainability metrics.
 * Access: Authenticated users (own data only).
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  User, ShoppingBag, Heart, Leaf, MapPin,
  Clock, Gift, RefreshCw, ArrowLeft,
  Loader2, ShieldAlert, TrendingUp, Package
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { analyticsService } from '@/services/analytics.service';
import type { UserSummaryData, WardrobeStats, ActivityItem } from '@/services/analytics.service';
import {
  KPICard, KPIGrid, ChartWrapper, DonutChart,
  EmptyState
} from '@/components/analytics/AnalyticsSharedComponents';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { EASE_LUXURY } from '@/motion';
import { cn } from '@/lib/utils';

// ===========================================
// User Analytics Page Component
// ===========================================

export default function UserAnalyticsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // State
  const [summaryData, setSummaryData] = useState<UserSummaryData | null>(null);
  const [wardrobeStats, setWardrobeStats] = useState<WardrobeStats | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch data
  const fetchData = useCallback(async () => {
    if (!user?.id) return;
    
    setLoading(true);
    setError(null);
    try {
      const [summary, wardrobe, activityData] = await Promise.all([
        analyticsService.getUserSummary(),
        analyticsService.getWardrobeStats(),
        analyticsService.getUserActivity(30, 50),
      ]);

      setSummaryData(summary);
      setWardrobeStats(wardrobe);
      setActivities(activityData.activities);
    } catch (err) {
      console.error('Failed to fetch user analytics:', err);
      setError('Failed to load your analytics data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  // Auth guard
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    fetchData();
  }, [authLoading, isAuthenticated, router, fetchData]);

  // Loading state
  if (authLoading || (loading && !summaryData)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="text-sm text-muted-foreground">Loading your analytics...</span>
        </motion.div>
      </div>
    );
  }

  // Error state
  if (error && !summaryData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <EmptyState
          icon={<ShieldAlert className="h-8 w-8 text-red-400" />}
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
  const categoryData = wardrobeStats?.category_breakdown
    ? Object.entries(wardrobeStats.category_breakdown).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  const brandData = wardrobeStats?.brand_breakdown
    ? Object.entries(wardrobeStats.brand_breakdown).slice(0, 5).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
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
                <User className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-foreground font-sans tracking-tight">
                  My Analytics
                </h1>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
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

        {/* KPI Grid */}
        <div className="mb-8">
          <KPIGrid columns={4}>
            <KPICard
              title="Outfits Saved"
              value={summaryData?.outfits_saved || 0}
              icon={<Heart className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Try-On Sessions (30d)"
              value={summaryData?.try_on_sessions_30d || 0}
              icon={<Package className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Money Saved (Coupons)"
              value={summaryData?.money_saved_via_coupons_egp || 0}
              format="currency"
              icon={<Gift className="h-5 w-5" />}
              loading={loading}
            />
            <KPICard
              title="Reuse Score"
              value={summaryData?.reuse_score || 0}
              format="percent"
              icon={<TrendingUp className="h-5 w-5" />}
              loading={loading}
            />
          </KPIGrid>
        </div>

        {/* Sustainability Impact Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-8"
        >
          <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/5 border-green-500/20">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-xl bg-green-500/20 flex items-center justify-center">
                  <Leaf className="h-5 w-5 text-green-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Your Sustainability Impact</h3>
                  <p className="text-sm text-muted-foreground">Environmental savings from re-wearing your wardrobe</p>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-background/50 rounded-lg">
                  <p className="text-3xl font-bold text-green-500">
                    {wardrobeStats?.sustainability_impact?.co2_saved_kg?.toFixed(1) || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">kg CO2 saved</p>
                </div>
                <div className="text-center p-4 bg-background/50 rounded-lg">
                  <p className="text-3xl font-bold text-blue-500">
                    {wardrobeStats?.sustainability_impact?.water_saved_liters?.toLocaleString() || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">Liters water saved</p>
                </div>
                <div className="text-center p-4 bg-background/50 rounded-lg">
                  <p className="text-3xl font-bold text-foreground">
                    {wardrobeStats?.times_worn_total || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">Times worn</p>
                </div>
                <div className="text-center p-4 bg-background/50 rounded-lg">
                  <p className="text-3xl font-bold text-foreground">
                    {wardrobeStats?.total_items || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">Wardrobe items</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Tabs Section */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="wardrobe">Wardrobe</TabsTrigger>
            <TabsTrigger value="activity">Activity</TabsTrigger>
            <TabsTrigger value="stores">Visited Stores</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Shopping Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-muted/30 rounded-lg">
                    <span className="text-muted-foreground">Total Orders</span>
                    <span className="font-semibold">{summaryData?.total_orders || 0}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted/30 rounded-lg">
                    <span className="text-muted-foreground">Total Spent</span>
                    <span className="font-semibold">{summaryData?.total_spent_egp?.toLocaleString() || 0} EGP</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted/30 rounded-lg">
                    <span className="text-muted-foreground">Outfits Saved (30d)</span>
                    <span className="font-semibold">{summaryData?.outfits_saved_30d || 0}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted/30 rounded-lg">
                    <span className="text-muted-foreground">Member Since</span>
                    <span className="font-semibold text-sm">
                      {summaryData?.member_since
                        ? new Date(summaryData.member_since).toLocaleDateString()
                        : 'N/A'}
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Savings Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-6">
                    <p className="text-4xl font-bold text-accent mb-2">
                      {summaryData?.money_saved_via_coupons_egp?.toLocaleString() || 0} EGP
                    </p>
                    <p className="text-sm text-muted-foreground">Total saved via coupons</p>
                  </div>
                  <div className="mt-4 p-4 bg-green-500/10 rounded-lg">
                    <div className="flex items-center gap-2 text-green-500">
                      <Leaf className="h-4 w-4" />
                      <span className="text-sm font-medium">Eco-Friendly Shopper</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Your reuse score of {summaryData?.reuse_score || 0}% shows you're making the most of your wardrobe!
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Wardrobe Tab */}
          <TabsContent value="wardrobe">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ChartWrapper
                title="Category Breakdown"
                subtitle="Items by category in your wardrobe"
                loading={loading}
              >
                <DonutChart data={categoryData} />
              </ChartWrapper>

              <ChartWrapper
                title="Brand Breakdown"
                subtitle="Top brands in your wardrobe"
                loading={loading}
              >
                <DonutChart data={brandData} />
              </ChartWrapper>
            </div>

            <div className="mt-6">
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold">Wardrobe Statistics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">{wardrobeStats?.total_items || 0}</p>
                      <p className="text-sm text-muted-foreground">Total Items</p>
                    </div>
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">{wardrobeStats?.times_worn_total || 0}</p>
                      <p className="text-sm text-muted-foreground">Times Worn</p>
                    </div>
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">{wardrobeStats?.reuse_score || 0}%</p>
                      <p className="text-sm text-muted-foreground">Reuse Score</p>
                    </div>
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                      <p className="text-2xl font-bold">
                        {Object.keys(wardrobeStats?.category_breakdown || {}).length}
                      </p>
                      <p className="text-sm text-muted-foreground">Categories</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Activity Tab */}
          <TabsContent value="activity">
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="text-lg font-semibold">Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3">
                    {activities.length === 0 ? (
                      <EmptyState
                        icon={<Clock className="h-8 w-8 text-muted-foreground" />}
                        title="No Recent Activity"
                        description="Start exploring to see your activity here!"
                      />
                    ) : (
                      activities.map((activity, index) => (
                        <motion.div
                          key={index}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.02 }}
                          className="flex items-start gap-3 p-3 bg-muted/30 rounded-lg"
                        >
                          <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
                            <Clock className="h-4 w-4 text-accent" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm">{activity.event_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(activity.date).toLocaleString()}
                            </p>
                          </div>
                          {Boolean((activity.details as Record<string, unknown>).store_id) && (
                            <Badge variant="outline" className="text-xs">
                              Store
                            </Badge>
                          )}
                        </motion.div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Visited Stores Tab */}
          <TabsContent value="stores">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {summaryData?.visited_stores?.length === 0 ? (
                <div className="col-span-full">
                  <EmptyState
                    icon={<MapPin className="h-8 w-8 text-muted-foreground" />}
                    title="No Store Visits Yet"
                    description="Visit stores to see them appear here!"
                  />
                </div>
              ) : (
                summaryData?.visited_stores?.map((store, index) => (
                  <motion.div
                    key={store.store_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-accent/30 transition-colors cursor-pointer">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <p className="font-semibold">{store.store_name}</p>
                            <p className="text-sm text-muted-foreground">{store.city}</p>
                          </div>
                          <Badge variant="secondary">{store.visit_count} visits</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{store.address}</p>
                        <p className="text-xs text-muted-foreground mt-2">
                          Last visited: {new Date(store.last_visited).toLocaleDateString()}
                        </p>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
