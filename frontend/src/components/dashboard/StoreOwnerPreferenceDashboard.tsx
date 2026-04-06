"use client";

import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Bell,
  Mail,
  Smartphone,
  Clock,
  Star,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  XCircle,
  Lightbulb,
  RefreshCw,
  Package,
  MessageSquare,
  Users,
  Target,
  Zap,
  BarChart3,
} from "lucide-react";

interface BusinessOutcome {
  owner_id: string;
  store_id: string;
  avg_response_time_hours?: number;
  avg_satisfaction_score?: number;
  orders_received: number;
  orders_processed: number;
  notification_action_rate: number;
  batch_inquiries_pct: number;
  active_preferences: Record<string, unknown>;
}

interface UserEngagement {
  recipient_id: string;
  recipient_type: string;
  engagement_score: number;
  open_rate: number;
  click_rate: number;
  ignore_rate: number;
  unsubscribe_events: number;
  channel_metrics: Record<string, Record<string, number>>;
  active_preferences: Record<string, unknown>;
}

interface Recommendation {
  id: string;
  recipient_id: string;
  recipient_type: string;
  recommendation_type: string;
  title: string;
  description: string;
  suggested_changes: Record<string, unknown>;
  expected_outcome: string;
  expected_metrics: Record<string, number>;
  similar_users_count: number;
  similar_users_improvement: number;
  priority_score: number;
  status: string;
  created_at: string;
}

interface PeerComparison {
  your_engagement_score: number;
  comparisons: Array<{
    cohort_name: string;
    your_score: number;
    cohort_avg: number;
    percentile: number;
    comparison: string;
  }>;
}

interface StoreOwnerPreferenceDashboardProps {
  apiBaseUrl?: string;
}

export function StoreOwnerPreferenceDashboard({
  apiBaseUrl = "/api/analytics/preferences",
}: StoreOwnerPreferenceDashboardProps) {
  const [loading, setLoading] = useState(true);
  const [businessOutcomes, setBusinessOutcomes] = useState<BusinessOutcome | null>(null);
  const [engagement, setEngagement] = useState<UserEngagement | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [peerComparison, setPeerComparison] = useState<PeerComparison | null>(null);
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [showRecDialog, setShowRecDialog] = useState(false);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [outcomesRes, engagementRes, recsRes, comparisonRes] = await Promise.all([
        fetch(`${apiBaseUrl}/business-outcomes/me`).then((r) => r.json()).catch(() => null),
        fetch(`${apiBaseUrl}/engagement/me`).then((r) => r.json()).catch(() => null),
        fetch(`${apiBaseUrl}/recommendations`).then((r) => r.json()).catch(() => []),
        fetch(`${apiBaseUrl}/engagement/compare`).then((r) => r.json()).catch(() => null),
      ]);

      setBusinessOutcomes(outcomesRes);
      setEngagement(engagementRes);
      setRecommendations(Array.isArray(recsRes) ? recsRes : []);
      setPeerComparison(comparisonRes);
    } catch (error) {
      console.error("Failed to fetch owner analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptRecommendation = async (recommendationId: string) => {
    setProcessing(true);
    try {
      const response = await fetch(`${apiBaseUrl}/recommendations/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recommendation_id: recommendationId }),
      });
      if (response.ok) {
        setShowRecDialog(false);
        setSelectedRec(null);
        fetchData();
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleRejectRecommendation = async (recommendationId: string) => {
    setProcessing(true);
    try {
      const response = await fetch(`${apiBaseUrl}/recommendations/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recommendation_id: recommendationId }),
      });
      if (response.ok) {
        setShowRecDialog(false);
        setSelectedRec(null);
        fetchData();
      }
    } finally {
      setProcessing(false);
    }
  };

  const pendingRecs = recommendations.filter((r) => r.status === "pending");

  const getResponseTimeStatus = (hours?: number) => {
    if (!hours) return { color: "text-gray-400", label: "No data" };
    if (hours <= 1) return { color: "text-green-600", label: "Excellent" };
    if (hours <= 4) return { color: "text-blue-600", label: "Good" };
    if (hours <= 12) return { color: "text-yellow-600", label: "Fair" };
    return { color: "text-red-600", label: "Needs Improvement" };
  };

  const getSatisfactionStatus = (score?: number) => {
    if (!score) return { color: "text-gray-400", label: "No data" };
    if (score >= 4.5) return { color: "text-green-600", label: "Excellent" };
    if (score >= 3.5) return { color: "text-blue-600", label: "Good" };
    if (score >= 2.5) return { color: "text-yellow-600", label: "Fair" };
    return { color: "text-red-600", label: "Needs Attention" };
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-32 bg-muted rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 bg-muted rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Notification Performance</h1>
          <p className="text-muted-foreground">
            Optimize your notification settings for better customer engagement
          </p>
        </div>
        <Button variant="outline" onClick={fetchData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Key Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Engagement Score</p>
                <p className="text-2xl font-bold">{engagement?.engagement_score.toFixed(1) || "0"}</p>
              </div>
              <div className="p-3 rounded-full bg-green-100 dark:bg-green-900">
                <TrendingUp className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <Progress value={engagement?.engagement_score || 0} className="mt-3 h-2" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Response Time</p>
                <p className="text-2xl font-bold">
                  {businessOutcomes?.avg_response_time_hours?.toFixed(1) || "—"}
                  <span className="text-sm font-normal text-muted-foreground ml-1">hrs</span>
                </p>
              </div>
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900">
                <Clock className="h-6 w-6 text-blue-600" />
              </div>
            </div>
            <p className={`text-sm mt-2 ${getResponseTimeStatus(businessOutcomes?.avg_response_time_hours).color}`}>
              {getResponseTimeStatus(businessOutcomes?.avg_response_time_hours).label}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Satisfaction</p>
                <p className="text-2xl font-bold">
                  {businessOutcomes?.avg_satisfaction_score?.toFixed(1) || "—"}
                  <span className="text-sm font-normal text-muted-foreground ml-1">/5</span>
                </p>
              </div>
              <div className="p-3 rounded-full bg-yellow-100 dark:bg-yellow-900">
                <Star className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
            <p className={`text-sm mt-2 ${getSatisfactionStatus(businessOutcomes?.avg_satisfaction_score).color}`}>
              {getSatisfactionStatus(businessOutcomes?.avg_satisfaction_score).label}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Orders This Month</p>
                <p className="text-2xl font-bold">{businessOutcomes?.orders_received || 0}</p>
              </div>
              <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900">
                <Package className="h-6 w-6 text-purple-600" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              {businessOutcomes?.orders_processed || 0} processed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="recommendations" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="recommendations" className="relative">
            Recommendations
            {pendingRecs.length > 0 && (
              <Badge className="ml-2 h-5 w-5 p-0 flex items-center justify-center">
                {pendingRecs.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="comparison">Peer Comparison</TabsTrigger>
        </TabsList>

        {/* Recommendations Tab */}
        <TabsContent value="recommendations" className="mt-6 space-y-4">
          {pendingRecs.length > 0 ? (
            <>
              <Card className="border-yellow-200 bg-yellow-50/50 dark:border-yellow-800 dark:bg-yellow-950/20">
                <CardContent className="py-4">
                  <div className="flex items-start gap-3">
                    <Lightbulb className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <p className="font-medium">Personalized Recommendations Available</p>
                      <p className="text-sm text-muted-foreground">
                        Based on your engagement patterns and similar store owners' success
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="space-y-3">
                {pendingRecs
                  .sort((a, b) => b.priority_score - a.priority_score)
                  .map((rec) => (
                    <Card
                      key={rec.id}
                      className="cursor-pointer hover:shadow-md transition-shadow"
                      onClick={() => {
                        setSelectedRec(rec);
                        setShowRecDialog(true);
                      }}
                    >
                      <CardContent className="py-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex items-start gap-3">
                            {rec.recommendation_type === "batch_vs_realtime" ? (
                              <div className="p-2 rounded-lg bg-cyan-100 dark:bg-cyan-900">
                                <Zap className="h-5 w-5 text-cyan-600" />
                              </div>
                            ) : rec.recommendation_type === "frequency_optimization" ? (
                              <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900">
                                <Clock className="h-5 w-5 text-blue-600" />
                              </div>
                            ) : (
                              <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900">
                                <Bell className="h-5 w-5 text-purple-600" />
                              </div>
                            )}
                            <div>
                              <h4 className="font-medium">{rec.title}</h4>
                              <p className="text-sm text-muted-foreground mt-1">
                                {rec.description.substring(0, 150)}...
                              </p>
                              <div className="flex items-center gap-4 mt-2 text-sm">
                                <span className="flex items-center gap-1 text-muted-foreground">
                                  <Users className="h-4 w-4" />
                                  {rec.similar_users_count} similar owners
                                </span>
                                <span className="flex items-center gap-1 text-green-600">
                                  <TrendingUp className="h-4 w-4" />
                                  +{rec.similar_users_improvement.toFixed(0)}% improvement
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge
                              variant={rec.priority_score >= 80 ? "default" : "secondary"}
                            >
                              {rec.priority_score >= 80 ? "High Priority" : "Suggested"}
                            </Badge>
                            <div className="mt-2 text-sm text-muted-foreground">
                              Relevance: {rec.priority_score.toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
              </div>
            </>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                <h3 className="text-lg font-medium">All Optimized!</h3>
                <p className="text-muted-foreground mt-1">
                  Your notification settings are well-tuned. We'll notify you when we have new suggestions.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Engagement Metrics
                </CardTitle>
                <CardDescription>How customers interact with your notifications</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Open Rate</span>
                    <div className="flex items-center gap-2">
                      <Progress value={(engagement?.open_rate || 0) * 100} className="w-24 h-2" />
                      <span className="text-sm font-medium">
                        {((engagement?.open_rate || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Click Rate</span>
                    <div className="flex items-center gap-2">
                      <Progress value={(engagement?.click_rate || 0) * 100} className="w-24 h-2" />
                      <span className="text-sm font-medium">
                        {((engagement?.click_rate || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Ignore Rate</span>
                    <div className="flex items-center gap-2">
                      <Progress
                        value={(engagement?.ignore_rate || 0) * 100}
                        className={`w-24 h-2 ${(engagement?.ignore_rate || 0) > 0.3 ? "[&>div]:bg-red-500" : ""}`}
                      />
                      <span className={`text-sm font-medium ${(engagement?.ignore_rate || 0) > 0.3 ? "text-red-600" : ""}`}>
                        {((engagement?.ignore_rate || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>

                {(engagement?.ignore_rate || 0) > 0.3 && (
                  <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800">
                    <div className="flex items-start gap-2">
                      <XCircle className="h-4 w-4 text-red-600 mt-0.5" />
                      <div className="text-sm">
                        <p className="font-medium text-red-700 dark:text-red-300">High Ignore Rate</p>
                        <p className="text-red-600 dark:text-red-400">
                          Consider reducing notification frequency or adjusting timing.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Business Impact
                </CardTitle>
                <CardDescription>How notifications affect your business</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-muted">
                    <div className="text-sm text-muted-foreground">Action Rate</div>
                    <div className="text-2xl font-bold">
                      {((businessOutcomes?.notification_action_rate || 0) * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Notifications → Actions</div>
                  </div>
                  <div className="p-4 rounded-lg bg-muted">
                    <div className="text-sm text-muted-foreground">Batch Inquiries</div>
                    <div className="text-2xl font-bold">
                      {((businessOutcomes?.batch_inquiries_pct || 0) * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Efficiency gain</div>
                  </div>
                </div>

                <div className="p-4 rounded-lg border">
                  <h4 className="text-sm font-medium mb-2">Current Configuration</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Batch Processing</span>
                      <Badge variant={
                        (businessOutcomes?.active_preferences as Record<string, unknown>)?.batch_settings ? "default" : "outline"
                      }>
                        {(businessOutcomes?.active_preferences as Record<string, unknown>)?.batch_settings ? "Enabled" : "Disabled"}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Real-time Alerts</span>
                      <Badge variant="default">Active</Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Channels Tab */}
        <TabsContent value="channels" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Channel Performance</CardTitle>
              <CardDescription>Effectiveness of each notification channel</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(engagement?.channel_metrics || {}).map(([channel, metrics]) => {
                  const delivered = metrics.delivered || 0;
                  const read = metrics.read || 0;
                  const clicked = metrics.clicked || 0;
                  const openRate = delivered > 0 ? read / delivered : 0;

                  return (
                    <div key={channel} className="p-4 rounded-lg border">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          {channel === "email" ? (
                            <Mail className="h-5 w-5 text-blue-500" />
                          ) : channel === "push" ? (
                            <Smartphone className="h-5 w-5 text-purple-500" />
                          ) : (
                            <Bell className="h-5 w-5 text-green-500" />
                          )}
                          <span className="font-medium capitalize">{channel.replace("_", " ")}</span>
                        </div>
                        <Badge variant={openRate > 0.3 ? "default" : "secondary"}>
                          {(openRate * 100).toFixed(0)}% open rate
                        </Badge>
                      </div>
                      <div className="grid grid-cols-4 gap-4 text-sm text-center">
                        <div>
                          <div className="text-lg font-bold">{delivered}</div>
                          <div className="text-muted-foreground">Delivered</div>
                        </div>
                        <div>
                          <div className="text-lg font-bold">{read}</div>
                          <div className="text-muted-foreground">Read</div>
                        </div>
                        <div>
                          <div className="text-lg font-bold">{clicked}</div>
                          <div className="text-muted-foreground">Clicked</div>
                        </div>
                        <div>
                          <div className="text-lg font-bold">{metrics.dismissed || 0}</div>
                          <div className="text-muted-foreground">Dismissed</div>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {Object.keys(engagement?.channel_metrics || {}).length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    No channel metrics available yet
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Peer Comparison Tab */}
        <TabsContent value="comparison" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>How You Compare</CardTitle>
              <CardDescription>Your performance relative to similar store owners</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {peerComparison?.comparisons.map((comp, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{comp.cohort_name}</span>
                    <Badge
                      variant={comp.comparison === "above" ? "default" : comp.comparison === "below" ? "destructive" : "secondary"}
                    >
                      {comp.comparison === "above" ? "Above Average" : comp.comparison === "below" ? "Below Average" : "At Average"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span>Your Score: {comp.your_score.toFixed(1)}</span>
                        <span className="text-muted-foreground">Cohort Avg: {comp.cohort_avg.toFixed(1)}</span>
                      </div>
                      <div className="relative h-4 bg-muted rounded-full overflow-hidden">
                        <div
                          className="absolute h-full bg-green-500 rounded-full"
                          style={{ width: `${comp.percentile}%` }}
                        />
                        <div
                          className="absolute h-0.5 bg-gray-400"
                          style={{ left: "50%", right: "50%", top: 0 }}
                        />
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">{comp.percentile.toFixed(0)}th</div>
                      <div className="text-xs text-muted-foreground">percentile</div>
                    </div>
                  </div>
                </div>
              ))}

              {!peerComparison?.comparisons.length && (
                <div className="text-center py-8 text-muted-foreground">
                  No peer comparison data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Recommendation Dialog */}
      <Dialog open={showRecDialog} onOpenChange={setShowRecDialog}>
        <DialogContent className="max-w-lg">
          {selectedRec && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedRec.title}</DialogTitle>
                <DialogDescription>{selectedRec.expected_outcome}</DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">{selectedRec.description}</p>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-muted">
                    <div className="text-xs text-muted-foreground mb-1">Similar Owners</div>
                    <div className="text-xl font-bold">{selectedRec.similar_users_count}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-green-50 dark:bg-green-950">
                    <div className="text-xs text-green-600 dark:text-green-400 mb-1">
                      Avg Improvement
                    </div>
                    <div className="text-xl font-bold text-green-600 dark:text-green-400">
                      +{selectedRec.similar_users_improvement.toFixed(0)}%
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Expected Impact</h4>
                  <div className="space-y-2">
                    {Object.entries(selectedRec.expected_metrics).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground capitalize">
                          {key.replace(/_/g, " ")}
                        </span>
                        <span className="font-medium text-green-600">
                          +{(value * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <DialogFooter className="gap-2 sm:gap-0">
                <Button
                  variant="outline"
                  onClick={() => handleRejectRecommendation(selectedRec.id)}
                  disabled={processing}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Not Now
                </Button>
                <Button onClick={() => handleAcceptRecommendation(selectedRec.id)} disabled={processing}>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Apply Changes
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default StoreOwnerPreferenceDashboard;
