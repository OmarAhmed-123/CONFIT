"use client";

import React, { useState } from "react";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Lightbulb,
  Check,
  X,
  ChevronRight,
  TrendingUp,
  Users,
  Sparkles,
  RefreshCw,
} from "lucide-react";

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

interface PreferenceRecommendationPanelProps {
  recommendations: Recommendation[];
  loading?: boolean;
  onAccept?: (recommendationId: string) => Promise<void>;
  onReject?: (recommendationId: string, reason?: string) => Promise<void>;
  onRefresh?: () => Promise<void>;
}

export function PreferenceRecommendationPanel({
  recommendations,
  loading = false,
  onAccept,
  onReject,
  onRefresh,
}: PreferenceRecommendationPanelProps) {
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [showDialog, setShowDialog] = useState(false);
  const [processing, setProcessing] = useState(false);

  const pendingRecs = (recommendations || []).filter((r) => r.status === "pending");

  const handleAccept = async () => {
    if (!selectedRec || !onAccept) return;
    setProcessing(true);
    try {
      await onAccept(selectedRec.id);
      setShowDialog(false);
      setSelectedRec(null);
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRec || !onReject) return;
    setProcessing(true);
    try {
      await onReject(selectedRec.id);
      setShowDialog(false);
      setSelectedRec(null);
    } finally {
      setProcessing(false);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "frequency_optimization":
        return "⏰";
      case "channel_optimization":
        return "📡";
      case "fatigue_prevention":
        return "🔋";
      case "engagement_improvement":
        return "📈";
      case "batch_vs_realtime":
        return "📦";
      default:
        return "💡";
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "frequency_optimization":
        return "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300";
      case "channel_optimization":
        return "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300";
      case "fatigue_prevention":
        return "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300";
      case "engagement_improvement":
        return "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300";
      case "batch_vs_realtime":
        return "bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300";
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5" />
            Recommendations
          </CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-20 bg-muted rounded-lg" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                Personalized Recommendations
              </CardTitle>
              <CardDescription>
                {pendingRecs.length > 0
                  ? `${pendingRecs.length} suggestions to improve your notification experience`
                  : "No new recommendations at this time"}
              </CardDescription>
            </div>
            {onRefresh && (
              <Button variant="outline" size="sm" onClick={onRefresh}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {pendingRecs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Sparkles className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>You're all set!</p>
              <p className="text-sm">We'll notify you when we have new suggestions.</p>
            </div>
          ) : (
            pendingRecs
              .sort((a, b) => b.priority_score - a.priority_score)
              .map((rec) => (
                <div
                  key={rec.id}
                  className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer"
                  onClick={() => {
                    setSelectedRec(rec);
                    setShowDialog(true);
                  }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">{getTypeIcon(rec.recommendation_type)}</span>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium">{rec.title}</h4>
                          <Badge className={getTypeColor(rec.recommendation_type)}>
                            {rec.recommendation_type.replace(/_/g, " ")}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {rec.description}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {rec.similar_users_count} similar users
                          </span>
                          <span className="flex items-center gap-1 text-green-600">
                            <TrendingUp className="h-3 w-3" />
                            +{rec.similar_users_improvement.toFixed(0)}% improvement
                          </span>
                        </div>
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-muted-foreground">Relevance</span>
                      <span className="font-medium">{rec.priority_score.toFixed(0)}%</span>
                    </div>
                    <Progress value={rec.priority_score} className="h-1.5" />
                  </div>
                </div>
              ))
          )}
        </CardContent>
      </Card>

      {/* Recommendation Detail Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-lg">
          {selectedRec && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span className="text-2xl">{getTypeIcon(selectedRec.recommendation_type)}</span>
                  {selectedRec.title}
                </DialogTitle>
                <DialogDescription>{selectedRec.expected_outcome}</DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Why this recommendation?</h4>
                  <p className="text-sm text-muted-foreground">{selectedRec.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-muted">
                    <div className="text-xs text-muted-foreground mb-1">Similar Users</div>
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
                  <h4 className="text-sm font-medium mb-2">Suggested Changes</h4>
                  <div className="p-3 rounded-lg bg-muted text-sm font-mono">
                    {JSON.stringify(selectedRec.suggested_changes, null, 2)}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Expected Impact</h4>
                  <div className="space-y-2">
                    {Object.entries(selectedRec.expected_metrics).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{key.replace(/_/g, " ")}</span>
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
                  onClick={handleReject}
                  disabled={processing}
                >
                  <X className="h-4 w-4 mr-2" />
                  Not Now
                </Button>
                <Button onClick={handleAccept} disabled={processing}>
                  <Check className="h-4 w-4 mr-2" />
                  Apply Changes
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}

export default PreferenceRecommendationPanel;
