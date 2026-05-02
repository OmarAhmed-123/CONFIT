/**
 * Wardrobe Analytics Panel
 * E.5 — Integrates wardrobe analytics into the wardrobe view
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  BarChart3,
  Leaf,
  Palette,
  Shirt,
  TrendingUp,
  ArrowRight,
  AlertTriangle,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getFullAnalytics,
  getSustainabilityInsights,
  getWardrobeConfidence,
  recalculateSustainability,
  type WardrobeAnalytics,
  type SustainabilityInsights,
  type WardrobeConfidence,
} from '@/services/wardrobeAnalyticsService';

// ═══════════════════════════════════════════════════════════════════
// Helper Components
// ═══════════════════════════════════════════════════════════════════

const StatPill = ({ label, value, icon, color }: { label: string; value: string; icon: React.ReactNode; color: string }) => (
  <div className={`flex items-center gap-3 p-3 rounded-lg bg-${color}-50 dark:bg-${color}-950/20`}>
    <div className={`p-2 rounded-md bg-${color}-100 dark:bg-${color}-900/30 text-${color}-600`}>
      {icon}
    </div>
    <div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  </div>
);

const ConfidenceBar = ({ label, value }: { label: string; value: number }) => (
  <div className="space-y-1">
    <div className="flex justify-between text-sm">
      <span>{label}</span>
      <span className="font-medium">{Math.round(value * 100)}%</span>
    </div>
    <div className="h-2 bg-muted rounded-full overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${value * 100}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className={`h-full rounded-full ${
          value >= 0.7 ? 'bg-green-500' : value >= 0.4 ? 'bg-amber-500' : 'bg-red-500'
        }`}
      />
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════
// Main Panel Component
// ═══════════════════════════════════════════════════════════════════

export default function WardrobeAnalyticsPanel() {
  const [activeTab, setActiveTab] = useState('overview');

  const {
    data: analytics,
    isLoading: analyticsLoading,
    error: analyticsError,
  } = useQuery({
    queryKey: ['wardrobe-analytics'],
    queryFn: getFullAnalytics,
    retry: 1,
  });

  const {
    data: sustainability,
    isLoading: sustainabilityLoading,
  } = useQuery({
    queryKey: ['wardrobe-sustainability'],
    queryFn: getSustainabilityInsights,
    retry: 1,
  });

  const {
    data: confidence,
    isLoading: confidenceLoading,
  } = useQuery({
    queryKey: ['wardrobe-confidence'],
    queryFn: getWardrobeConfidence,
    retry: 1,
  });

  const handleRecalculate = async () => {
    try {
      const result = await recalculateSustainability();
      toast.success(`Sustainability score updated: ${result.sustainability_score}`);
    } catch {
      toast.error('Failed to recalculate sustainability metrics');
    }
  };

  const isLoading = analyticsLoading || sustainabilityLoading || confidenceLoading;

  if (isLoading) {
    return (
      <Card className="border-border/60">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-muted rounded w-1/3" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 bg-muted rounded-lg" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (analyticsError) {
    return (
      <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/10">
        <CardContent className="p-6 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          <div>
            <p className="font-medium">Analytics temporarily unavailable</p>
            <p className="text-sm text-muted-foreground">Try refreshing the page later.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/60 overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <CardTitle>Wardrobe Intelligence</CardTitle>
          </div>
          <Button variant="ghost" size="sm" onClick={handleRecalculate}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        </div>
        <CardDescription>AI-powered insights about your wardrobe</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-6">
            <TabsTrigger value="overview" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary">
              Overview
            </TabsTrigger>
            <TabsTrigger value="sustainability" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary">
              Sustainability
            </TabsTrigger>
            <TabsTrigger value="confidence" className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary">
              Confidence
            </TabsTrigger>
          </TabsList>

          <AnimatePresence mode="wait">
            {/* Overview Tab */}
            <TabsContent value="overview" className="p-6 space-y-6">
              {analytics && (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatPill
                      label="Total Items"
                      value={String(analytics.overview.total_items)}
                      icon={<Shirt className="h-4 w-4" />}
                      color="blue"
                    />
                    <StatPill
                      label="Active Items"
                      value={String(analytics.overview.active_items)}
                      icon={<Sparkles className="h-4 w-4" />}
                      color="purple"
                    />
                    <StatPill
                      label="Total Wears"
                      value={String(analytics.overview.total_wears)}
                      icon={<TrendingUp className="h-4 w-4" />}
                      color="green"
                    />
                    <StatPill
                      label="Unused Items"
                      value={String(analytics.overview.unused_items)}
                      icon={<AlertTriangle className="h-4 w-4" />}
                      color="amber"
                    />
                  </div>

                  {analytics.category_distribution.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium mb-3">Category Breakdown</h4>
                      <div className="flex flex-wrap gap-2">
                        {analytics.category_distribution.map((cat) => (
                          <Badge
                            key={cat.category}
                            variant={cat.is_gap ? 'destructive' : 'secondary'}
                            className="flex items-center gap-1"
                          >
                            {cat.category}
                            <span className="opacity-70">({cat.count})</span>
                            {cat.is_gap && <AlertTriangle className="h-3 w-3 ml-1" />}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {analytics.confidence.improvements.length > 0 && (
                    <div className="bg-muted/50 rounded-lg p-4">
                      <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-primary" />
                        Quick Improvements
                      </h4>
                      <ul className="space-y-1">
                        {analytics.confidence.improvements.slice(0, 3).map((improvement, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                            <ArrowRight className="h-3 w-3 mt-1 shrink-0" />
                            {improvement}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </TabsContent>

            {/* Sustainability Tab */}
            <TabsContent value="sustainability" className="p-6 space-y-6">
              {sustainability && (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-950/20">
                      <Leaf className="h-8 w-8 text-green-600" />
                      <div>
                        <p className="text-2xl font-bold">{sustainability.sustainability_score}</p>
                        <p className="text-xs text-muted-foreground">Sustainability Score</p>
                      </div>
                    </div>
                    <div className="p-4 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">{sustainability.total_co2_saved_kg.toFixed(1)} kg</p>
                      <p className="text-xs text-muted-foreground">CO₂ Saved</p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">${sustainability.money_saved.toFixed(0)}</p>
                      <p className="text-xs text-muted-foreground">Money Saved</p>
                    </div>
                  </div>

                  {sustainability.sustainability_tips.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium">Sustainability Tips</h4>
                      <div className="grid gap-2">
                        {sustainability.sustainability_tips.slice(0, 3).map((tip, i) => (
                          <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-green-50/50 dark:bg-green-950/10 text-sm">
                            <Leaf className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                            {tip}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </TabsContent>

            {/* Confidence Tab */}
            <TabsContent value="confidence" className="p-6 space-y-6">
              {confidence && (
                <>
                  <div className="flex items-center gap-4">
                    <div className="relative w-24 h-24">
                      <svg className="w-24 h-24 transform -rotate-90">
                        <circle cx="48" cy="48" r="44" stroke="currentColor" strokeWidth="6" fill="none" className="text-muted" />
                        <circle
                          cx="48"
                          cy="48"
                          r="44"
                          stroke="url(#confidenceGradient)"
                          strokeWidth="6"
                          fill="none"
                          strokeDasharray={`${confidence.overall_confidence * 276} 276`}
                          strokeLinecap="round"
                        />
                        <defs>
                          <linearGradient id="confidenceGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#8b5cf6" />
                            <stop offset="100%" stopColor="#3b82f6" />
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-xl font-bold">{Math.round(confidence.overall_confidence * 100)}%</span>
                      </div>
                    </div>
                    <div>
                      <p className="font-medium">Wardrobe Confidence</p>
                      <p className="text-sm text-muted-foreground">How versatile and complete your wardrobe is</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <ConfidenceBar label="Variety" value={confidence.dimensions.variety} />
                    <ConfidenceBar label="Versatility" value={confidence.dimensions.versatility} />
                    <ConfidenceBar label="Utilization" value={confidence.dimensions.utilization} />
                    <ConfidenceBar label="Cohesion" value={confidence.dimensions.cohesion} />
                    <ConfidenceBar label="Seasonality" value={confidence.dimensions.seasonality} />
                    <ConfidenceBar label="Quality" value={confidence.dimensions.quality} />
                  </div>

                  {confidence.top_improvements.length > 0 && (
                    <div className="bg-muted/50 rounded-lg p-4">
                      <h4 className="text-sm font-medium mb-2">Top Improvements</h4>
                      <ul className="space-y-1">
                        {confidence.top_improvements.slice(0, 3).map((improvement, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                            <ArrowRight className="h-3 w-3 mt-1 shrink-0" />
                            {improvement}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </TabsContent>
          </AnimatePresence>
        </Tabs>
      </CardContent>
    </Card>
  );
}
