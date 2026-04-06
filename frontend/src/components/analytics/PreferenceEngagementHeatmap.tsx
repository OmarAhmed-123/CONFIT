"use client";

import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";

interface EngagementHeatmapCell {
  preference_key: string;
  preference_value: string;
  user_count: number;
  avg_engagement_score: number;
  avg_open_rate: number;
  avg_click_rate: number;
  avg_ignore_rate: number;
}

interface PreferenceEngagementHeatmapProps {
  data: EngagementHeatmapCell[];
  loading?: boolean;
}

export function PreferenceEngagementHeatmap({
  data,
  loading = false,
}: PreferenceEngagementHeatmapProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Engagement by Preference</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="animate-pulse text-muted-foreground">Loading heatmap data...</div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Engagement by Preference</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="text-muted-foreground">No engagement heatmap data found</div>
        </CardContent>
      </Card>
    );
  }

  // Calculate baseline for comparison
  const baselineEngagement =
    data.reduce((sum, item) => sum + item.avg_engagement_score * item.user_count, 0) /
    data.reduce((sum, item) => sum + item.user_count, 0);

  // Sort by engagement score
  const sortedData = [...data].sort(
    (a, b) => b.avg_engagement_score - a.avg_engagement_score
  );

  // Get color based on engagement relative to baseline
  const getEngagementColor = (score: number) => {
    const ratio = score / baselineEngagement;
    if (ratio >= 1.2) return "text-green-600 bg-green-50 dark:bg-green-950";
    if (ratio >= 1.0) return "text-blue-600 bg-blue-50 dark:bg-blue-950";
    if (ratio >= 0.8) return "text-yellow-600 bg-yellow-50 dark:bg-yellow-950";
    return "text-red-600 bg-red-50 dark:bg-red-950";
  };

  const getTrendIcon = (score: number) => {
    const ratio = score / baselineEngagement;
    if (ratio >= 1.1) return <ArrowUp className="h-4 w-4 text-green-600" />;
    if (ratio <= 0.9) return <ArrowDown className="h-4 w-4 text-red-600" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Engagement by Preference</span>
          <Badge variant="outline" className="font-normal">
            Baseline: {baselineEngagement.toFixed(1)}
          </Badge>
        </CardTitle>
        <CardDescription>
          How different preference configurations correlate with engagement
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Preference</TableHead>
                <TableHead>Value</TableHead>
                <TableHead className="text-right">Users</TableHead>
                <TableHead className="text-right">Engagement</TableHead>
                <TableHead className="text-right">Open Rate</TableHead>
                <TableHead className="text-right">Ignore Rate</TableHead>
                <TableHead className="text-center">vs Baseline</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedData.map((row, index) => (
                <TableRow key={`${row.preference_key}-${row.preference_value}-${index}`}>
                  <TableCell className="font-medium">
                    {row.preference_key.replace(/_/g, " ")}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{row.preference_value}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {row.user_count.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span className={getEngagementColor(row.avg_engagement_score)}>
                        {row.avg_engagement_score.toFixed(1)}
                      </span>
                      {getTrendIcon(row.avg_engagement_score)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    {(row.avg_open_rate * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span
                        className={
                          row.avg_ignore_rate > 0.5
                            ? "text-red-600"
                            : row.avg_ignore_rate > 0.3
                            ? "text-yellow-600"
                            : "text-green-600"
                        }
                      >
                        {(row.avg_ignore_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col items-center gap-1">
                      <Progress
                        value={(row.avg_engagement_score / 100) * 100}
                        className="h-2 w-16"
                      />
                      <span className="text-xs text-muted-foreground">
                        {((row.avg_engagement_score / baselineEngagement - 1) * 100).toFixed(
                          0
                        )}
                        %
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800">
            <div className="text-sm font-medium text-green-700 dark:text-green-300">
              High Performers
            </div>
            <div className="text-2xl font-bold text-green-600">
              {sortedData.filter((d) => d.avg_engagement_score > baselineEngagement * 1.1).length}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
            <div className="text-sm font-medium text-blue-700 dark:text-blue-300">
              At Baseline
            </div>
            <div className="text-2xl font-bold text-blue-600">
              {
                sortedData.filter(
                  (d) =>
                    d.avg_engagement_score >= baselineEngagement * 0.9 &&
                    d.avg_engagement_score <= baselineEngagement * 1.1
                ).length
              }
            </div>
          </div>
          <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800">
            <div className="text-sm font-medium text-yellow-700 dark:text-yellow-300">
              Below Baseline
            </div>
            <div className="text-2xl font-bold text-yellow-600">
              {
                sortedData.filter(
                  (d) =>
                    d.avg_engagement_score < baselineEngagement * 0.9 &&
                    d.avg_engagement_score >= baselineEngagement * 0.8
                ).length
              }
            </div>
          </div>
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800">
            <div className="text-sm font-medium text-red-700 dark:text-red-300">
              Low Performers
            </div>
            <div className="text-2xl font-bold text-red-600">
              {sortedData.filter((d) => d.avg_engagement_score < baselineEngagement * 0.8).length}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default PreferenceEngagementHeatmap;
