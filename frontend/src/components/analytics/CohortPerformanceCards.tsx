"use client";

import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Users,
  TrendingUp,
  TrendingDown,
  Mail,
  Bell,
  Clock,
  Star,
  AlertTriangle,
} from "lucide-react";

interface CohortPerformance {
  cohort_id: string;
  cohort_name: string;
  cohort_slug: string;
  member_count: number;
  avg_engagement_score: number;
  avg_open_rate: number;
  avg_click_rate: number;
  avg_ignore_rate: number;
  avg_response_time_hours?: number;
  avg_satisfaction_score?: number;
}

interface CohortPerformanceCardsProps {
  cohorts: CohortPerformance[];
  loading?: boolean;
  onSelectCohort?: (cohortId: string) => void;
  selectedCohortId?: string;
}

export function CohortPerformanceCards({
  cohorts,
  loading = false,
  onSelectCohort,
  selectedCohortId,
}: CohortPerformanceCardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 bg-muted rounded w-1/2" />
              <div className="h-3 bg-muted rounded w-1/3 mt-2" />
            </CardHeader>
            <CardContent>
              <div className="h-20 bg-muted rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!cohorts || cohorts.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No cohort data available
        </CardContent>
      </Card>
    );
  }

  // Sort cohorts by engagement
  const sortedCohorts = [...cohorts].sort(
    (a, b) => b.avg_engagement_score - a.avg_engagement_score
  );

  const getEngagementBadge = (score: number) => {
    if (score >= 70) return { variant: "default" as const, label: "High" };
    if (score >= 50) return { variant: "secondary" as const, label: "Medium" };
    return { variant: "destructive" as const, label: "Low" };
  };

  const getIgnoreRateColor = (rate: number) => {
    if (rate <= 0.2) return "text-green-600";
    if (rate <= 0.4) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Cohort Performance</h3>
        {onSelectCohort && (
          <Select value={selectedCohortId} onValueChange={onSelectCohort}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select cohort" />
            </SelectTrigger>
            <SelectContent>
              {cohorts.map((cohort) => (
                <SelectItem key={cohort.cohort_id} value={cohort.cohort_id}>
                  {cohort.cohort_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedCohorts.map((cohort) => {
          const badge = getEngagementBadge(cohort.avg_engagement_score);
          const isSelected = selectedCohortId === cohort.cohort_id;

          return (
            <Card
              key={cohort.cohort_id}
              className={`cursor-pointer transition-all hover:shadow-md ${
                isSelected ? "ring-2 ring-primary" : ""
              }`}
              onClick={() => onSelectCohort?.(cohort.cohort_id)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{cohort.cohort_name}</CardTitle>
                  <Badge variant={badge.variant}>{badge.label}</Badge>
                </div>
                <CardDescription className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {cohort.member_count.toLocaleString()} members
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Engagement Score */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Engagement</span>
                    <span className="font-medium">{cohort.avg_engagement_score.toFixed(1)}</span>
                  </div>
                  <Progress
                    value={cohort.avg_engagement_score}
                    className="h-2"
                  />
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center gap-1.5">
                    <Mail className="h-3.5 w-3.5 text-blue-500" />
                    <span className="text-muted-foreground">Open:</span>
                    <span className="font-medium">
                      {(cohort.avg_open_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Bell className="h-3.5 w-3.5 text-purple-500" />
                    <span className="text-muted-foreground">Click:</span>
                    <span className="font-medium">
                      {(cohort.avg_click_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-orange-500" />
                    <span className="text-muted-foreground">Ignore:</span>
                    <span className={`font-medium ${getIgnoreRateColor(cohort.avg_ignore_rate)}`}>
                      {(cohort.avg_ignore_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Owner-specific metrics */}
                {cohort.avg_response_time_hours !== undefined && (
                  <div className="pt-2 border-t flex items-center gap-1.5 text-sm">
                    <Clock className="h-3.5 w-3.5 text-green-500" />
                    <span className="text-muted-foreground">Response:</span>
                    <span className="font-medium">
                      {cohort.avg_response_time_hours.toFixed(1)}h avg
                    </span>
                  </div>
                )}

                {cohort.avg_satisfaction_score !== undefined && (
                  <div className="flex items-center gap-1.5 text-sm">
                    <Star className="h-3.5 w-3.5 text-yellow-500" />
                    <span className="text-muted-foreground">Satisfaction:</span>
                    <span className="font-medium">
                      {cohort.avg_satisfaction_score.toFixed(1)}/5
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Summary Stats */}
      <Card className="bg-muted/50">
        <CardContent className="py-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold">
                {cohorts.reduce((sum, c) => sum + c.member_count, 0).toLocaleString()}
              </div>
              <div className="text-sm text-muted-foreground">Total Members</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {(
                  cohorts.reduce((sum, c) => sum + c.avg_engagement_score, 0) / cohorts.length
                ).toFixed(1)}
              </div>
              <div className="text-sm text-muted-foreground">Avg Engagement</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {cohorts.filter((c) => c.avg_engagement_score >= 70).length}
              </div>
              <div className="text-sm text-muted-foreground">High Performers</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">
                {cohorts.filter((c) => c.avg_ignore_rate > 0.5).length}
              </div>
              <div className="text-sm text-muted-foreground">Fatigue Risk</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default CohortPerformanceCards;
