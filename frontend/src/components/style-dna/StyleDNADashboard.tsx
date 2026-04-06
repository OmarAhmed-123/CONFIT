/**
 * Style DNA Dashboard Component
 * Main dashboard for displaying user's unique style fingerprint
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Palette,
  Shirt,
  Sparkles,
  TrendingUp,
  Users,
  Target,
  ChevronRight,
  RefreshCw,
  Info,
  Zap,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';

import { StyleMapVisualization } from './StyleMapVisualization';
import { ColorWheelVisualization } from './ColorWheelVisualization';
import { BrandUniverseVisualization } from './BrandUniverseVisualization';
import { EvolutionTimeline } from './EvolutionTimeline';
import { StyleInsights } from './StyleInsights';
import { StyleQuiz } from './StyleQuiz';

import { styleDNAApi, StyleDNADashboardData } from '@/lib/api/style-dna';

const COLOR_BADGE_CLASSES: Record<string, string> = {
  black: 'bg-black text-white border-black/20',
  white: 'bg-white text-black border-black/20',
  gray: 'bg-gray-500 text-white border-gray-500/30',
  navy: 'bg-slate-800 text-white border-slate-800/30',
  blue: 'bg-blue-500 text-white border-blue-500/30',
  red: 'bg-red-500 text-white border-red-500/30',
  green: 'bg-green-500 text-white border-green-500/30',
  yellow: 'bg-yellow-400 text-black border-yellow-400/40',
  orange: 'bg-orange-500 text-white border-orange-500/30',
  pink: 'bg-pink-500 text-white border-pink-500/30',
  purple: 'bg-purple-500 text-white border-purple-500/30',
  brown: 'bg-amber-900 text-white border-amber-900/30',
  beige: 'bg-stone-200 text-black border-stone-300',
  cream: 'bg-amber-50 text-black border-amber-100',
  coral: 'bg-orange-400 text-white border-orange-400/30',
  peach: 'bg-orange-200 text-black border-orange-200/50',
  gold: 'bg-yellow-500 text-black border-yellow-500/30',
  silver: 'bg-zinc-300 text-black border-zinc-300/50',
  emerald: 'bg-emerald-500 text-white border-emerald-500/30',
  lavender: 'bg-violet-200 text-black border-violet-200/60',
  rose: 'bg-rose-500 text-white border-rose-500/30',
};

function getColorBadgeClass(colorName: string): string {
  return COLOR_BADGE_CLASSES[colorName.toLowerCase()] || 'bg-muted text-foreground border-border';
}

interface StyleDNADashboardProps {
  className?: string;
}

export const StyleDNADashboard: React.FC<StyleDNADashboardProps> = ({ className }) => {
  const [dashboardData, setDashboardData] = useState<StyleDNADashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const data = await styleDNAApi.getDashboard();
      setDashboardData(data);
    } catch (error) {
      console.error('Failed to load Style DNA dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      await styleDNAApi.analyzeStyle(true);
      await loadDashboardData();
    } catch (error) {
      console.error('Failed to analyze style:', error);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleQuizComplete = async () => {
    setShowQuiz(false);
    await loadDashboardData();
  };

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (showQuiz) {
    return <StyleQuiz onComplete={handleQuizComplete} onCancel={() => setShowQuiz(false)} />;
  }

  const profile = dashboardData?.profile;
  const completeness = profile?.profile_completeness || 0;

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Style DNA</h1>
          <p className="text-muted-foreground">Your unique style fingerprint</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowQuiz(true)}
            className="gap-2"
          >
            <Sparkles className="h-4 w-4" />
            Retake Quiz
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleAnalyze}
            disabled={analyzing}
            className="gap-2"
          >
            {analyzing ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" />
                Analyze Style
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Profile Completeness Banner */}
      {completeness < 100 && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Target className="h-5 w-5 text-primary" />
                  <div>
                    <p className="font-medium">Complete your Style DNA</p>
                    <p className="text-sm text-muted-foreground">
                      {completeness.toFixed(0)}% complete - Add more details for better recommendations
                    </p>
                  </div>
                </div>
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              </div>
              <Progress value={completeness} className="mt-3 h-2" />
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="style-map">Style Map</TabsTrigger>
          <TabsTrigger value="colors">Colors</TabsTrigger>
          <TabsTrigger value="brands">Brands</TabsTrigger>
          <TabsTrigger value="evolution">Evolution</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Primary Style Card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Shirt className="h-4 w-4" />
                  Primary Style
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold capitalize">
                  {profile?.primary_style?.replace('_', ' ') || 'Not set'}
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {profile?.secondary_styles?.slice(0, 3).map((style) => (
                    <Badge key={style} variant="secondary" className="text-xs">
                      {style.replace('_', ' ')}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Style Confidence */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Style Confidence
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {((profile?.style_confidence || 0) * 100).toFixed(0)}%
                </div>
                <Progress
                  value={(profile?.style_confidence || 0) * 100}
                  className="mt-2 h-2"
                />
              </CardContent>
            </Card>

            {/* Budget Level */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  Budget Level
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold capitalize">
                  {profile?.budget_level?.replace('_', ' ') || 'Moderate'}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {profile?.budget_range?.per_item_max
                    ? `Up to $${profile.budget_range.per_item_max} per item`
                    : 'Budget range not set'}
                </p>
              </CardContent>
            </Card>

            {/* Fit Preference */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Fit Preference
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold capitalize">
                  {profile?.fit_preference || 'Regular'}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Based on your preferences
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Visualizations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Style Map Preview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" />
                  Style Position
                </CardTitle>
                <CardDescription>
                  Where you fall on the style spectrum
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboardData?.style_map && (
                  <StyleMapVisualization
                    data={dashboardData.style_map}
                    compact
                  />
                )}
              </CardContent>
            </Card>

            {/* Color Wheel Preview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  Color Preferences
                </CardTitle>
                <CardDescription>
                  Your favorite colors and undertones
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboardData?.color_wheel && (
                  <ColorWheelVisualization
                    data={dashboardData.color_wheel}
                    compact
                  />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Style Insights */}
          {dashboardData?.style_insights && (
            <StyleInsights insights={dashboardData.style_insights} />
          )}
        </TabsContent>

        {/* Style Map Tab */}
        <TabsContent value="style-map">
          <Card>
            <CardHeader>
              <CardTitle>Interactive Style Map</CardTitle>
              <CardDescription>
                Explore your style dimensions and see how they relate
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboardData?.style_map && (
                <StyleMapVisualization data={dashboardData.style_map} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Colors Tab */}
        <TabsContent value="colors">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Color Wheel</CardTitle>
                <CardDescription>
                  Your color preferences and recommendations
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboardData?.color_wheel && (
                  <ColorWheelVisualization data={dashboardData.color_wheel} />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Color Analysis</CardTitle>
                <CardDescription>
                  Detailed breakdown of your color preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Primary Colors</h4>
                  <div className="flex flex-wrap gap-2">
                    {profile?.color_preferences?.primary?.map((color) => (
                      <Badge
                        key={color}
                        className={cn('flex items-center gap-2 border', getColorBadgeClass(color))}
                      >
                        {color}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Undertone</h4>
                  <p className="text-muted-foreground capitalize">
                    {profile?.color_preferences?.undertone || 'Not detected'}
                  </p>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Recommended Colors</h4>
                  <div className="flex flex-wrap gap-2">
                    {dashboardData?.color_wheel?.recommended?.map((color: string) => (
                      <Badge
                        key={color}
                        variant="outline"
                        className="flex items-center gap-2"
                      >
                        <span className={cn('w-3 h-3 rounded-full border', getColorBadgeClass(color))} />
                        {color}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Brands Tab */}
        <TabsContent value="brands">
          <Card>
            <CardHeader>
              <CardTitle>Brand Universe</CardTitle>
              <CardDescription>
                Brands you love and brands we think you'll love
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboardData?.brand_universe && (
                <BrandUniverseVisualization data={dashboardData.brand_universe} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Evolution Tab */}
        <TabsContent value="evolution">
          <Card>
            <CardHeader>
              <CardTitle>Style Evolution Timeline</CardTitle>
              <CardDescription>
                Track how your style has evolved over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboardData?.evolution_timeline && (
                <EvolutionTimeline events={dashboardData.evolution_timeline} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Loading skeleton
const DashboardSkeleton: React.FC = () => (
  <div className="space-y-6">
    <div className="flex items-center justify-between">
      <div>
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-5 w-48 mt-2" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-9 w-28" />
        <Skeleton className="h-9 w-28" />
      </div>
    </div>

    <Skeleton className="h-24 w-full" />

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardContent className="p-6">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-16 mt-2" />
          </CardContent>
        </Card>
      ))}
    </div>

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    </div>
  </div>
);

export default StyleDNADashboard;
