/**
 * CONFIT — Channel Performance Chart
 * =====================================
 * Recharts ComposedChart showing delivery, open, and click rates
 * across channels with trend lines over time.
 */

import { useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
} from 'recharts';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp } from 'lucide-react';
import type { ChannelMetrics, DashboardPeriod, AnalyticsChannel } from '@/types/notificationAnalyticsTypes';

interface ChannelPerformanceChartProps {
  metrics: ChannelMetrics[];
  dailyTrend: Array<{
    date: string;
    delivery_rate: number;
    open_rate: number;
    click_rate: number;
    count: number;
  }>;
  period: DashboardPeriod;
}

const CHANNEL_LABELS: Record<AnalyticsChannel, string> = {
  in_app: 'In-App',
  email: 'Email',
  push: 'Push',
  toast: 'Toast',
};

const CHART_COLORS = {
  delivery: '#34d399',  // Emerald
  open: '#60a5fa',      // Blue
  click: '#c084fc',     // Purple
  volume: 'rgba(212, 175, 55, 0.3)', // Gold muted
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null;
  return (
    <div className="rounded-xl border border-white/[0.08] bg-[hsl(220,25%,10%)] p-3 shadow-xl backdrop-blur-xl">
      <p className="text-xs font-medium text-muted-foreground mb-2">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium text-foreground">
            {typeof entry.value === 'number'
              ? entry.value < 1
                ? `${(entry.value * 100).toFixed(1)}%`
                : entry.value.toLocaleString()
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ChannelPerformanceChart({ metrics, dailyTrend, period }: ChannelPerformanceChartProps) {
  const [view, setView] = useState<'comparison' | 'trend'>('comparison');

  const barData = useMemo(() =>
    metrics.map((m) => ({
      channel: CHANNEL_LABELS[m.channel],
      'Delivery Rate': m.delivery_rate,
      'Open Rate': m.open_rate,
      'Click-Through': m.click_through_rate,
      'Total Sent': m.total_sent,
    })),
    [metrics]
  );

  const trendData = useMemo(() =>
    dailyTrend.map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      'Delivery Rate': d.delivery_rate,
      'Open Rate': d.open_rate,
      'Click Rate': d.click_rate,
      Volume: d.count,
    })),
    [dailyTrend]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-foreground font-sans">
            Channel Performance
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Delivery, open, and click-through rates by channel
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg bg-white/[0.04] p-1">
          <button
            onClick={() => setView('comparison')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              view === 'comparison'
                ? 'bg-white/[0.08] text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <BarChart3 className="h-3.5 w-3.5" />
            Compare
          </button>
          <button
            onClick={() => setView('trend')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              view === 'trend'
                ? 'bg-white/[0.08] text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            Trend
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          {view === 'comparison' ? (
            <BarChart data={barData} barGap={4} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="channel"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <YAxis
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                domain={[0, 1]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}
              />
              <Bar dataKey="Delivery Rate" fill={CHART_COLORS.delivery} radius={[4, 4, 0, 0]} />
              <Bar dataKey="Open Rate" fill={CHART_COLORS.open} radius={[4, 4, 0, 0]} />
              <Bar dataKey="Click-Through" fill={CHART_COLORS.click} radius={[4, 4, 0, 0]} />
            </BarChart>
          ) : (
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="date"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                domain={[0, 1]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}
              />
              <Line
                type="monotone"
                dataKey="Delivery Rate"
                stroke={CHART_COLORS.delivery}
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="Open Rate"
                stroke={CHART_COLORS.open}
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="Click Rate"
                stroke={CHART_COLORS.click}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
