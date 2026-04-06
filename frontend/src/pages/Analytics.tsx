import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { RefreshCw, Sparkles, Users, Activity, ArrowRight, TrendingUp } from "lucide-react";

import { MainLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { createTransition } from "@/motion";

import { api } from "@/lib/api";

type Range = "7d" | "30d" | "90d";

type AnalyticsMetricsResponse = {
  range: Range;
  window_days: number;
  overview: {
    dau_1d: number;
    active_users: number;
    retention_d7: number;
    conversion_rate: number;
    outfit_interactions: number;
    ai_usage: number;
  };
  dau_series: Array<{ date: string; dau: number }>;
  purchase_count: number;
  tryon_count: number;
  stylist_chat_count: number;
};

function fmtInt(v: number) {
  return Math.round(v).toLocaleString("en-US");
}

function fmtPct01(v: number) {
  // v is 0..1
  return `${(v * 100).toFixed(1)}%`;
}

const cardVariants = {
  hidden: { opacity: 0, y: 16, filter: "blur(6px)" },
  visible: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.45, ease: "easeInOut" } },
};

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<Range>("30d");
  const [data, setData] = useState<AnalyticsMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.get<AnalyticsMetricsResponse>("/analytics/metrics", { range: timeRange });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load metrics");
    } finally {
      setIsLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    void fetchMetrics();
  }, [fetchMetrics]);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await fetchMetrics();
    } finally {
      setRefreshing(false);
    }
  };

  const series = useMemo(() => data?.dau_series ?? [], [data]);

  if (isLoading) {
    return (
      <MainLayout>
        <div className="container py-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Array.from({ length: 6 }).map((_, idx) => (
              <Card key={idx} className="overflow-hidden">
                <CardContent className="p-6">
                  <Skeleton className="h-4 w-40 mb-4" />
                  <Skeleton className="h-8 w-28 mb-4" />
                  <Skeleton className="h-3 w-64" />
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="mt-6">
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      </MainLayout>
    );
  }

  if (error || !data) {
    return (
      <MainLayout>
        <div className="container py-8">
          <Card className="max-w-xl mx-auto">
            <CardContent className="p-6 text-center">
              <p className="text-destructive mb-4">{error || "No data available"}</p>
              <Button onClick={onRefresh} className="rounded-full">
                Try Again
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    );
  }

  const o = data.overview;

  return (
    <MainLayout>
      <div className="container py-8 space-y-8">
        <motion.div
          initial={{ opacity: 0, y: -18, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          className="flex flex-col md:flex-row md:items-center md:justify-between gap-4"
        >
          <div>
            <h1 className="heading-hero mb-2">Analytics Dashboard</h1>
            <p className="text-muted-foreground">Real engagement + conversion signals from CONFIT behavior logs.</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex gap-1 p-1 bg-muted rounded-lg">
              {(["7d", "30d", "90d"] as const).map((r) => (
                <Button
                  key={r}
                  variant={timeRange === r ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setTimeRange(r)}
                  className="h-8 rounded-full"
                >
                  {r === "7d" ? "7d" : r === "30d" ? "30d" : "90d"}
                </Button>
              ))}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={refreshing}
              className="h-10 rounded-full"
            >
              <motion.div
                animate={refreshing ? { rotate: 360 } : { rotate: 0 }}
                transition={createTransition({ duration: 1, repeat: refreshing ? Infinity : 0, ease: "linear" })}
              >
                <RefreshCw className="h-4 w-4" />
              </motion.div>
            </Button>
          </div>
        </motion.div>

        <motion.div variants={cardVariants} initial="hidden" animate="visible" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
          {[
            { title: "DAU (1d)", value: fmtInt(o.dau_1d), icon: Activity, badge: "active", badgeTone: "default" as const },
            { title: `Active (${data.window_days}d)`, value: fmtInt(o.active_users), icon: Users, badge: "reach", badgeTone: "secondary" as const },
            { title: "D7 Retention", value: fmtPct01(o.retention_d7), icon: Sparkles, badge: "sticky", badgeTone: "default" as const },
            { title: "Conversion", value: fmtPct01(o.conversion_rate), icon: TrendingUp, badge: "funnel", badgeTone: "secondary" as const },
            { title: "Outfit Interactions", value: fmtInt(o.outfit_interactions), icon: Activity, badge: "dopamine", badgeTone: "default" as const },
            { title: "AI Usage", value: fmtInt(o.ai_usage), icon: Sparkles, badge: "stylist", badgeTone: "secondary" as const },
          ].map((stat, idx) => (
            <motion.div key={stat.title} transition={createTransition({ delay: idx * 0.06 })}>
              <Card className="hover:shadow-lg transition-shadow duration-300">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <stat.icon className="h-5 w-5 text-accent" />
                    <Badge variant={stat.badgeTone} className="text-xs rounded-full">{stat.badge}</Badge>
                  </div>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <div className="text-sm text-muted-foreground mt-1">{stat.title}</div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-accent" />
              DAU trend (last 14 days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: "rgba(255,255,255,0.65)" }} />
                  <YAxis tick={{ fontSize: 12, fill: "rgba(255,255,255,0.65)" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15,15,20,0.95)",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: 10,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="dau"
                    stroke="#8b5cf6"
                    strokeWidth={2.25}
                    dot={false}
                    animationDuration={900}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
