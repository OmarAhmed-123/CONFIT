/**
 * AI Cost Admin Dashboard
 * Shows budget status, daily cost reports, kill-switch control, and per-service breakdowns.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  DollarSign, AlertTriangle, Power, PowerOff, RefreshCw,
  BarChart3, Users, Clock, Zap, Loader2, TrendingUp, Shield,
} from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  aiAdminService,
  type AIBudgetStatus,
  type AIDailyReport,
  type AIServiceCostSummary,
} from '@/services/aiFeaturesService';
import { toast } from 'sonner';

const stagger = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08 },
  }),
};

export default function AIAdminDashboardPage() {
  const [budget, setBudget] = useState<AIBudgetStatus | null>(null);
  const [report, setReport] = useState<AIDailyReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [killSwitchLoading, setKillSwitchLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [b, r] = await Promise.all([
        aiAdminService.getBudgetStatus(),
        aiAdminService.getDailyReport(),
      ]);
      setBudget(b);
      setReport(r);
    } catch (err) {
      toast.error('Failed to load AI admin data', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleKillSwitch = async (activate: boolean) => {
    setKillSwitchLoading(true);
    try {
      const result = await aiAdminService.toggleKillSwitch(activate);
      toast.success(result.message);
      await fetchData();
    } catch (err) {
      toast.error('Failed to toggle kill-switch', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setKillSwitchLoading(false);
    }
  };

  const budgetPercent = budget ? Math.min(budget.percent_used, 100) : 0;
  const budgetColor =
    budgetPercent >= 90 ? 'bg-red-500' :
    budgetPercent >= 70 ? 'bg-amber-500' :
    'bg-emerald-500';

  return (
    <MainLayout>
      <div className="container py-8 px-4 md:px-8 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div>
            <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full mb-4">
              <Shield className="h-4 w-4" />
              <span className="text-sm font-medium">Admin Only</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold mb-2">AI Cost Dashboard</h1>
            <p className="text-muted-foreground">
              Monitor AI service costs, budget status, and kill-switch control.
            </p>
          </div>
          <Button variant="outline" onClick={fetchData} disabled={isLoading} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </motion.div>

        {isLoading && !budget ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-accent" />
          </div>
        ) : (
          <>
            {/* Budget Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <motion.div custom={0} variants={stagger} initial="hidden" animate="visible">
                <Card className="bg-card/80 backdrop-blur-sm">
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-muted-foreground">Daily Budget</span>
                      <DollarSign className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="text-2xl font-bold">${budget?.daily_budget_usd.toFixed(2) ?? '—'}</p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div custom={1} variants={stagger} initial="hidden" animate="visible">
                <Card className="bg-card/80 backdrop-blur-sm">
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-muted-foreground">Spent Today</span>
                      <TrendingUp className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="text-2xl font-bold">${budget?.spent_usd.toFixed(4) ?? '—'}</p>
                    <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden" aria-label={`Budget usage: ${budgetPercent.toFixed(1)}%`}>
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${budgetColor}`}
                        style={{ width: `${budgetPercent}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {budgetPercent.toFixed(1)}% of daily budget
                    </p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div custom={2} variants={stagger} initial="hidden" animate="visible">
                <Card className="bg-card/80 backdrop-blur-sm">
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-muted-foreground">Remaining</span>
                      <BarChart3 className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="text-2xl font-bold">${budget?.remaining_usd.toFixed(2) ?? '—'}</p>
                    {budget?.is_warning && (
                      <Badge variant="outline" className="mt-2 text-amber-500 border-amber-500/50">
                        <AlertTriangle className="h-3 w-3 mr-1" /> Warning
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div custom={3} variants={stagger} initial="hidden" animate="visible">
                <Card className={`bg-card/80 backdrop-blur-sm ${budget?.kill_switch_active ? 'border-red-500/50' : ''}`}>
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-muted-foreground">Kill Switch</span>
                      {budget?.kill_switch_active ? (
                        <PowerOff className="h-5 w-5 text-red-500" />
                      ) : (
                        <Power className="h-5 w-5 text-emerald-500" />
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={budget?.kill_switch_active ? 'destructive' : 'default'}>
                        {budget?.kill_switch_active ? 'ACTIVE' : 'INACTIVE'}
                      </Badge>
                      <Button
                        size="sm"
                        variant={budget?.kill_switch_active ? 'outline' : 'destructive'}
                        onClick={() => toggleKillSwitch(!budget?.kill_switch_active)}
                        disabled={killSwitchLoading}
                        className="gap-1"
                      >
                        {killSwitchLoading ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : budget?.kill_switch_active ? (
                          <>
                            <Power className="h-3 w-3" /> Re-enable
                          </>
                        ) : (
                          <>
                            <PowerOff className="h-3 w-3" /> Activate
                          </>
                        )}
                      </Button>
                    </div>
                    {budget?.is_exceeded && (
                      <p className="text-xs text-red-500 mt-2">Budget exceeded — non-critical AI disabled.</p>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Daily Report */}
            <Card className="bg-card/80 backdrop-blur-sm mb-8">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-accent" />
                    Daily Cost Report — {report?.date ?? '—'}
                  </CardTitle>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <DollarSign className="h-4 w-4" />
                      Total: ${report?.total_cost_usd.toFixed(4) ?? '—'}
                    </span>
                    <span className="flex items-center gap-1">
                      <BarChart3 className="h-4 w-4" />
                      Calls: {report?.total_calls ?? 0}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {report && report.services.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left py-3 px-4 font-medium text-muted-foreground">Service</th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">Cost (USD)</th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">Calls</th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">Tokens In</th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">Tokens Out</th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">Avg Latency</th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">Success Rate</th>
                          <th className="text-right py-3 px-4 font-medium text-muted-foreground">Users</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.services.map((svc: AIServiceCostSummary, i: number) => (
                          <motion.tr
                            key={svc.service}
                            className="border-b border-border/50 hover:bg-muted/30 transition-colors"
                            custom={i}
                            variants={stagger}
                            initial="hidden"
                            animate="visible"
                          >
                            <td className="py-3 px-4">
                              <Badge variant="outline">{svc.service}</Badge>
                            </td>
                            <td className="text-right py-3 px-4 font-mono">${svc.total_cost_usd.toFixed(4)}</td>
                            <td className="text-right py-3 px-4">{svc.total_calls.toLocaleString()}</td>
                            <td className="text-right py-3 px-4">{svc.total_tokens_in.toLocaleString()}</td>
                            <td className="text-right py-3 px-4">{svc.total_tokens_out.toLocaleString()}</td>
                            <td className="text-right py-3 px-4">{svc.avg_latency_ms.toFixed(0)}ms</td>
                            <td className="text-right py-3 px-4">
                              <span className={svc.success_rate >= 0.95 ? 'text-emerald-500' : 'text-amber-500'}>
                                {(svc.success_rate * 100).toFixed(1)}%
                              </span>
                            </td>
                            <td className="text-right py-3 px-4">{svc.unique_users}</td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-30" />
                    <p>No AI cost data available for today.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </MainLayout>
  );
}
