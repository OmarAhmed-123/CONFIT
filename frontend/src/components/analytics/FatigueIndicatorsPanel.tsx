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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertTriangle,
  BellOff,
  TrendingDown,
  Users,
  Mail,
  Smartphone,
} from "lucide-react";

interface FatigueIndicator {
  recipient_id: string;
  recipient_type: string;
  ignore_rate: number;
  unsubscribe_events: number;
  fatigue_channel?: string;
  recommendation?: string;
}

interface FatigueIndicatorsPanelProps {
  data: FatigueIndicator[];
  loading?: boolean;
  onSendRecommendation?: (recipientId: string) => Promise<void>;
}

export function FatigueIndicatorsPanel({
  data,
  loading = false,
  onSendRecommendation,
}: FatigueIndicatorsPanelProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            Fatigue Indicators
          </CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-16 bg-muted rounded-lg" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  const highRiskUsers = data.filter((u) => u.ignore_rate > 0.7 || u.unsubscribe_events > 0);
  const mediumRiskUsers = data.filter(
    (u) => u.ignore_rate > 0.5 && u.ignore_rate <= 0.7 && u.unsubscribe_events === 0
  );
  const lowRiskUsers = data.filter(
    (u) => u.ignore_rate <= 0.5 && u.unsubscribe_events === 0
  );

  const getRiskLevel = (user: FatigueIndicator) => {
    if (user.ignore_rate > 0.7 || user.unsubscribe_events > 0) {
      return { level: "high", color: "destructive", label: "High Risk" };
    }
    if (user.ignore_rate > 0.5) {
      return { level: "medium", color: "secondary", label: "Medium Risk" };
    }
    return { level: "low", color: "outline", label: "Low Risk" };
  };

  const getChannelIcon = (channel?: string) => {
    if (!channel) return <BellOff className="h-4 w-4" />;
    switch (channel) {
      case "email":
        return <Mail className="h-4 w-4" />;
      case "push":
        return <Smartphone className="h-4 w-4" />;
      default:
        return <BellOff className="h-4 w-4" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            Fatigue Indicators
          </div>
          <Badge variant="destructive">{data.length} users at risk</Badge>
        </CardTitle>
        <CardDescription>
          Users showing signs of notification fatigue
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <span className="text-sm font-medium text-red-700 dark:text-red-300">
                High Risk
              </span>
            </div>
            <div className="text-2xl font-bold text-red-600">{highRiskUsers.length}</div>
            <div className="text-xs text-red-600/70">Immediate action needed</div>
          </div>

          <div className="p-4 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="h-4 w-4 text-yellow-600" />
              <span className="text-sm font-medium text-yellow-700 dark:text-yellow-300">
                Medium Risk
              </span>
            </div>
            <div className="text-2xl font-bold text-yellow-600">{mediumRiskUsers.length}</div>
            <div className="text-xs text-yellow-600/70">Monitor closely</div>
          </div>

          <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                Low Risk
              </span>
            </div>
            <div className="text-2xl font-bold text-blue-600">{lowRiskUsers.length}</div>
            <div className="text-xs text-blue-600/70">Minor concerns</div>
          </div>
        </div>

        {/* Detailed Table */}
        {data.length > 0 && (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Ignore Rate</TableHead>
                  <TableHead className="text-center">Unsubscribes</TableHead>
                  <TableHead>Fatigue Channel</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Recommendation</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.slice(0, 20).map((user, index) => {
                  const risk = getRiskLevel(user);
                  return (
                    <TableRow key={user.recipient_id || index}>
                      <TableCell className="font-mono text-xs">
                        {user.recipient_id.substring(0, 8)}...
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{user.recipient_type}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Progress
                            value={user.ignore_rate * 100}
                            className={`h-2 w-16 ${
                              user.ignore_rate > 0.7
                                ? "[&>div]:bg-red-500"
                                : user.ignore_rate > 0.5
                                ? "[&>div]:bg-yellow-500"
                                : "[&>div]:bg-blue-500"
                            }`}
                          />
                          <span
                            className={`text-sm font-medium ${
                              user.ignore_rate > 0.7
                                ? "text-red-600"
                                : user.ignore_rate > 0.5
                                ? "text-yellow-600"
                                : "text-blue-600"
                            }`}
                          >
                            {(user.ignore_rate * 100).toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        {user.unsubscribe_events > 0 ? (
                          <Badge variant="destructive">{user.unsubscribe_events}</Badge>
                        ) : (
                          <span className="text-muted-foreground">0</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          {getChannelIcon(user.fatigue_channel)}
                          <span className="text-sm capitalize">
                            {user.fatigue_channel || "Multiple"}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={risk.color as "destructive" | "secondary" | "outline"}>
                          {risk.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {user.recommendation || "Reduce frequency"}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}

        {/* Action Recommendations */}
        <div className="p-4 rounded-lg bg-muted">
          <h4 className="text-sm font-medium mb-3">Recommended Actions</h4>
          <div className="space-y-2 text-sm">
            {highRiskUsers.length > 0 && (
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />
                <span>
                  <strong>High Priority:</strong> Send personalized recommendations to{" "}
                  {highRiskUsers.length} users at high risk of churning.
                </span>
              </div>
            )}
            {mediumRiskUsers.length > 0 && (
              <div className="flex items-start gap-2">
                <TrendingDown className="h-4 w-4 text-yellow-500 mt-0.5" />
                <span>
                  <strong>Monitor:</strong> Track engagement trends for {mediumRiskUsers.length}{" "}
                  medium-risk users over the next week.
                </span>
              </div>
            )}
            <div className="flex items-start gap-2">
              <BellOff className="h-4 w-4 text-blue-500 mt-0.5" />
              <span>
                <strong>Prevention:</strong> Consider proactive batch settings for users
                approaching fatigue thresholds.
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default FatigueIndicatorsPanel;
