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
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";

interface ChannelDistribution {
  [key: string]: { enabled: number; disabled: number };
}

interface FrequencyDistribution {
  [key: string]: {
    real_time: number;
    daily_digest: number;
    weekly_summary: number;
    disabled: number;
  };
}

interface PreferenceDistribution {
  snapshot_date: string;
  recipient_type: string;
  channel_distribution: ChannelDistribution;
  frequency_distribution: FrequencyDistribution;
  type_distribution: Record<string, Record<string, number>>;
  total_users: number;
}

interface PreferenceDistributionChartProps {
  data: PreferenceDistribution[];
  loading?: boolean;
}

const COLORS = {
  enabled: "#22c55e",
  disabled: "#ef4444",
  real_time: "#3b82f6",
  daily_digest: "#8b5cf6",
  weekly_summary: "#f59e0b",
  disabled_freq: "#6b7280",
};

const PIE_COLORS = ["#22c55e", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444", "#6b7280"];

export function PreferenceDistributionChart({
  data,
  loading = false,
}: PreferenceDistributionChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Preference Distribution</CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="animate-pulse text-muted-foreground">Loading chart data...</div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Preference Distribution</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="text-muted-foreground">No preference distribution data found</div>
        </CardContent>
      </Card>
    );
  }

  // Aggregate data across all snapshots
  const latestSnapshot = data[0];

  // Transform channel distribution for bar chart
  const channelData = Object.entries(latestSnapshot.channel_distribution || {}).map(
    ([channel, stats]) => ({
      channel: channel.replace("_enabled", "").replace("_", " ").toUpperCase(),
      enabled: stats.enabled || 0,
      disabled: stats.disabled || 0,
    })
  );

  // Transform frequency distribution for stacked bar chart
  const frequencyData = Object.entries(latestSnapshot.frequency_distribution || {}).map(
    ([channel, stats]) => ({
      channel: channel.replace("_frequency", "").replace("_", " ").toUpperCase(),
      real_time: stats.real_time || 0,
      daily_digest: stats.daily_digest || 0,
      weekly_summary: stats.weekly_summary || 0,
      disabled: stats.disabled || 0,
    })
  );

  // Pie chart data for overall channel usage
  const channelPieData = channelData.map((item) => ({
    name: item.channel,
    value: item.enabled,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Preference Distribution</span>
          <Badge variant="secondary">{latestSnapshot.total_users.toLocaleString()} users</Badge>
        </CardTitle>
        <CardDescription>
          How users configure their notification preferences
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="channels" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="channels">Channels</TabsTrigger>
            <TabsTrigger value="frequency">Frequency</TabsTrigger>
            <TabsTrigger value="overview">Overview</TabsTrigger>
          </TabsList>

          <TabsContent value="channels" className="mt-4">
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={channelData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="channel" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Bar
                    dataKey="enabled"
                    stackId="a"
                    fill={COLORS.enabled}
                    name="Enabled"
                    radius={[0, 0, 0, 0]}
                  />
                  <Bar
                    dataKey="disabled"
                    stackId="a"
                    fill={COLORS.disabled}
                    name="Disabled"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          <TabsContent value="frequency" className="mt-4">
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={frequencyData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="channel" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Bar
                    dataKey="real_time"
                    stackId="a"
                    fill={COLORS.real_time}
                    name="Real-time"
                  />
                  <Bar
                    dataKey="daily_digest"
                    stackId="a"
                    fill={COLORS.daily_digest}
                    name="Daily Digest"
                  />
                  <Bar
                    dataKey="weekly_summary"
                    stackId="a"
                    fill={COLORS.weekly_summary}
                    name="Weekly Summary"
                  />
                  <Bar
                    dataKey="disabled"
                    stackId="a"
                    fill={COLORS.disabled_freq}
                    name="Disabled"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          <TabsContent value="overview" className="mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="h-[300px]">
                <h4 className="text-sm font-medium mb-2 text-center">Channel Usage</h4>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={channelPieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {channelPieData.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={PIE_COLORS[index % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium mb-2">Key Insights</h4>
                <div className="space-y-2">
                  {channelData.map((item) => {
                    const total = item.enabled + item.disabled;
                    const enabledPct = total > 0 ? (item.enabled / total) * 100 : 0;
                    return (
                      <div key={item.channel} className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">{item.channel}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500"
                              style={{ width: `${enabledPct}%` }}
                            />
                          </div>
                          <span className="text-xs font-medium">
                            {enabledPct.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

export default PreferenceDistributionChart;
