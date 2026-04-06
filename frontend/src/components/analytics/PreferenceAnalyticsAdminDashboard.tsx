"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw, Settings, Download, Users, Bell, TrendingUp, AlertTriangle, Lightbulb } from "lucide-react";
import { PreferenceDistributionChart } from "./PreferenceDistributionChart";
import { PreferenceEngagementHeatmap } from "./PreferenceEngagementHeatmap";
import { CohortPerformanceCards } from "./CohortPerformanceCards";
import { PreferenceRecommendationPanel } from "./PreferenceRecommendationPanel";
import { FatigueIndicatorsPanel } from "./FatigueIndicatorsPanel";
import { PreferenceABTestResultsPanel } from "./PreferenceABTestResultsPanel";

interface AnalyticsSummary {
  users: {
    customer: number;
    owner: number;
  };
  engagement: {
    customer: {
      avg_engagement_score: number;
      avg_open_rate: number;
      avg_click_rate: number;
    };
    owner: {
      avg_engagement_score: number;
      avg_open_rate: number;
      avg_click_rate: number;
    };
  };
  recommendations: {
    pending: number;
    accepted: number;
    rejected: number;
    acceptance_rate: number;
  };
  ab_tests: {
    active: number;
  };
  fatigue: {
    users_at_risk: number;
  };
}

interface PreferenceAnalyticsAdminDashboardProps {
  apiBaseUrl?: string;
  onExport?: (format: "csv" | "json") => void;
}

export function PreferenceAnalyticsAdminDashboard({
  apiBaseUrl = "/api/analytics/preferences",
  onExport,
}: PreferenceAnalyticsAdminDashboardProps) {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [distribution, setDistribution] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [fatigueData, setFatigueData] = useState([]);
  const [abTests, setAbTests] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch all data in parallel
      const [summaryRes, distRes, heatmapRes, cohortsRes, recsRes, fatigueRes, testsRes] = await Promise.all([
        fetch(`${apiBaseUrl}/summary`).then((r) => r.json()).catch(() => null),
        fetch(`${apiBaseUrl}/distribution`).then((r) => r.json()).catch(() => []),
        fetch(`${apiBaseUrl}/heatmap`).then((r) => r.json()).catch(() => []),
        fetch(`${apiBaseUrl}/cohorts`).then((r) => r.json()).catch(() => []),
        fetch(`${apiBaseUrl}/recommendations`).then((r) => r.json()).catch(() => []),
        fetch(`${apiBaseUrl}/fatigue-indicators`).then((r) => r.json()).catch(() => []),
        fetch(`${apiBaseUrl}/ab-tests`).then((r) => r.json()).catch(() => []),
      ]);

      setSummary(summaryRes);
      setDistribution(distRes);
      setHeatmap(heatmapRes);
      setCohorts(cohortsRes);
      setRecommendations(recsRes);
      setFatigueData(fatigueRes);
      setAbTests(testsRes);
    } catch (error) {
      console.error("Failed to fetch analytics data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const handleAcceptRecommendation = async (recommendationId: string) => {
    const response = await fetch(`${apiBaseUrl}/recommendations/accept`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recommendation_id: recommendationId }),
    });
    if (response.ok) {
      fetchData();
    }
  };

  const handleRejectRecommendation = async (recommendationId: string, reason?: string) => {
    const response = await fetch(`${apiBaseUrl}/recommendations/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recommendation_id: recommendationId, reason }),
    });
    if (response.ok) {
      fetchData();
    }
  };

  const handleCreateTest = async (config: {
    test_name: string;
    hypothesis: string;
    recommendation_type: string;
    segment_type: string;
    duration_days: number;
  }) => {
    const response = await fetch(`${apiBaseUrl}/ab-tests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (response.ok) {
      fetchData();
    }
  };

  const handleStartTest = async (testId: string) => {
    const response = await fetch(`${apiBaseUrl}/ab-tests/${testId}/start`, { method: "POST" });
    if (response.ok) {
      fetchData();
    }
  };

  const handleCompleteTest = async (testId: string) => {
    const response = await fetch(`${apiBaseUrl}/ab-tests/${testId}/complete`, { method: "POST" });
    if (response.ok) {
      fetchData();
    }
  };

  const handleRolloutTest = async (testId: string) => {
    const response = await fetch(`${apiBaseUrl}/ab-tests/${testId}/rollout`, { method: "POST" });
    if (response.ok) {
      fetchData();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Preference Analytics</h1>
          <p className="text-muted-foreground">
            Monitor notification preferences, engagement patterns, and recommendations
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onExport && (
            <Button variant="outline" onClick={() => onExport("csv")}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          )}
          <Button variant="outline" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Users</p>
                  <p className="text-2xl font-bold">
                    {(summary.users.customer + summary.users.owner).toLocaleString()}
                  </p>
                </div>
                <Users className="h-8 w-8 text-blue-500" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                {summary.users.customer.toLocaleString()} customers, {summary.users.owner.toLocaleString()} owners
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg Engagement</p>
                  <p className="text-2xl font-bold">
                    {summary.engagement.customer?.avg_engagement_score?.toFixed(1) || "0"}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-500" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                Open rate: {((summary.engagement.customer?.avg_open_rate || 0) * 100).toFixed(1)}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Recommendations</p>
                  <p className="text-2xl font-bold">{summary.recommendations.pending}</p>
                </div>
                <Lightbulb className="h-8 w-8 text-yellow-500" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                {(summary.recommendations.acceptance_rate * 100).toFixed(0)}% acceptance rate
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Fatigue Risk</p>
                  <p className="text-2xl font-bold text-red-600">{summary.fatigue.users_at_risk}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-red-500" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                Users with high ignore rates
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active Tests</p>
                  <p className="text-2xl font-bold">{summary.ab_tests.active}</p>
                </div>
                <Bell className="h-8 w-8 text-purple-500" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                A/B experiments running
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Owner Engagement</p>
                  <p className="text-2xl font-bold">
                    {summary.engagement.owner?.avg_engagement_score?.toFixed(1) || "0"}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-cyan-500" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                Store/factory owners
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="cohorts">Cohorts</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          <TabsTrigger value="fatigue">Fatigue</TabsTrigger>
          <TabsTrigger value="ab-tests">A/B Tests</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <PreferenceDistributionChart data={distribution} loading={loading} />
            <PreferenceEngagementHeatmap data={heatmap} loading={loading} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Recent Recommendation Activity</CardTitle>
                <CardDescription>Latest preference recommendations and their status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recommendations.slice(0, 5).map((rec: Record<string, unknown>, i: number) => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted">
                      <div>
                        <p className="font-medium">{rec.title as string}</p>
                        <p className="text-sm text-muted-foreground">{rec.recommendation_type as string}</p>
                      </div>
                      <Badge variant={rec.status === "accepted" ? "default" : "secondary"}>
                        {rec.status as string}
                      </Badge>
                    </div>
                  ))}
                  {recommendations.length === 0 && (
                    <p className="text-center text-muted-foreground py-4">No recent recommendations</p>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>Common administrative tasks</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full justify-start" variant="outline">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Regenerate Recommendations
                </Button>
                <Button className="w-full justify-start" variant="outline">
                  <Users className="h-4 w-4 mr-2" />
                  Update Cohort Assignments
                </Button>
                <Button className="w-full justify-start" variant="outline">
                  <AlertTriangle className="h-4 w-4 mr-2" />
                  Review Fatigue Alerts
                </Button>
                <Button className="w-full justify-start" variant="outline">
                  <Settings className="h-4 w-4 mr-2" />
                  Configure Thresholds
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="cohorts" className="mt-6">
          <CohortPerformanceCards cohorts={cohorts} loading={loading} />
        </TabsContent>

        <TabsContent value="recommendations" className="mt-6">
          <PreferenceRecommendationPanel
            recommendations={recommendations}
            loading={loading}
            onAccept={handleAcceptRecommendation}
            onReject={handleRejectRecommendation}
            onRefresh={fetchData}
          />
        </TabsContent>

        <TabsContent value="fatigue" className="mt-6">
          <FatigueIndicatorsPanel data={fatigueData} loading={loading} />
        </TabsContent>

        <TabsContent value="ab-tests" className="mt-6">
          <PreferenceABTestResultsPanel
            tests={abTests}
            loading={loading}
            onCreateTest={handleCreateTest}
            onStartTest={handleStartTest}
            onCompleteTest={handleCompleteTest}
            onRollout={handleRolloutTest}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default PreferenceAnalyticsAdminDashboard;
