/**
 * CONFIT — Conversion & Business Impact Section
 * ================================================
 * Two-panel section: conversion correlation by channel and
 * owner response time by store.
 */

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  Cell,
} from 'recharts';
import { motion } from 'framer-motion';
import { ShoppingCart, Clock } from 'lucide-react';
import type {
  ConversionDataPoint,
  OwnerResponseTime,
  CohortComparison,
} from '@/types/notificationAnalyticsTypes';

interface ConversionImpactSectionProps {
  conversionData: ConversionDataPoint[];
  ownerResponseTimes: OwnerResponseTime[];
  cohortData: CohortComparison[];
}

const CHANNEL_COLORS: Record<string, string> = {
  in_app: '#34d399',
  email: '#60a5fa',
  push: '#c084fc',
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null;
  return (
    <div className="rounded-xl border border-white/[0.08] bg-[hsl(220,25%,10%)] p-3 shadow-xl backdrop-blur-xl">
      <p className="text-xs font-medium text-muted-foreground mb-2">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium text-foreground">
            {typeof entry.value === 'number'
              ? entry.name.includes('Rate') || entry.name.includes('rate')
                ? `${(entry.value * 100).toFixed(1)}%`
                : entry.name.includes('min')
                ? `${entry.value.toFixed(1)} min`
                : entry.value.toLocaleString()
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ConversionImpactSection({
  conversionData,
  ownerResponseTimes,
  cohortData,
}: ConversionImpactSectionProps) {
  // Transform conversion data for chart — group by period
  const conversionChartData = useMemo(() => {
    const periods = [7, 14, 30];
    return periods.map((period) => {
      const row: Record<string, any> = { period: `${period}d` };
      conversionData
        .filter((d) => d.period_days === period)
        .forEach((d) => {
          const label = d.channel === 'in_app' ? 'In-App' : d.channel === 'email' ? 'Email' : 'Push';
          row[label] = d.conversion_rate;
        });
      return row;
    });
  }, [conversionData]);

  // Transform owner response times for chart
  const responseChartData = useMemo(() =>
    ownerResponseTimes
      .sort((a, b) => a.avg_response_time_min - b.avg_response_time_min)
      .map((o) => ({
        store: o.store_name.replace('CONFIT ', ''),
        'Avg Response (min)': parseFloat(o.avg_response_time_min.toFixed(1)),
        'Median (min)': parseFloat(o.median_response_time_min.toFixed(1)),
        notifications: o.notification_count,
      })),
    [ownerResponseTimes]
  );

  const avgResponseAll = useMemo(() => {
    const total = ownerResponseTimes.reduce((s, o) => s + o.avg_response_time_min, 0);
    return total / (ownerResponseTimes.length || 1);
  }, [ownerResponseTimes]);

  // Cohort bar data
  const cohortChartData = useMemo(() =>
    cohortData.map((c) => ({
      period: c.period,
      'Notified': c.notified_purchase_rate,
      'Not Notified': c.non_notified_purchase_rate,
      'Lift': `+${c.lift_percentage.toFixed(0)}%`,
    })),
    [cohortData]
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Conversion by Channel */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.25 }}
        className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6"
      >
        <div className="flex items-center gap-2 mb-1">
          <ShoppingCart className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-foreground font-sans">
            Conversion by Channel
          </h3>
        </div>
        <p className="text-sm text-muted-foreground mb-5">
          Repeat purchase rate within 7/14/30 days of notification
        </p>

        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={conversionChartData} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="period"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <YAxis
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }} />
              <Bar dataKey="In-App" fill={CHANNEL_COLORS.in_app} radius={[4, 4, 0, 0]} />
              <Bar dataKey="Email" fill={CHANNEL_COLORS.email} radius={[4, 4, 0, 0]} />
              <Bar dataKey="Push" fill={CHANNEL_COLORS.push} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Owner Response Times */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6"
      >
        <div className="flex items-center gap-2 mb-1">
          <Clock className="h-5 w-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-foreground font-sans">
            Owner Response Times
          </h3>
        </div>
        <p className="text-sm text-muted-foreground mb-5">
          Average time from notification to owner action by store
        </p>

        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={responseChartData} layout="vertical" barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                type="number"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                unit=" min"
              />
              <YAxis
                type="category"
                dataKey="store"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                width={120}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                x={parseFloat(avgResponseAll.toFixed(1))}
                stroke="rgba(212,175,55,0.5)"
                strokeDasharray="4 4"
                label={{ value: 'Avg', fill: 'rgba(212,175,55,0.7)', fontSize: 11 }}
              />
              <Bar dataKey="Avg Response (min)" radius={[0, 4, 4, 0]}>
                {responseChartData.map((entry, idx) => (
                  <Cell
                    key={idx}
                    fill={entry['Avg Response (min)'] > avgResponseAll ? '#f87171' : '#34d399'}
                    fillOpacity={0.7}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Cohort Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.35 }}
        className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6 lg:col-span-2"
      >
        <div className="flex items-center gap-2 mb-1">
          <ShoppingCart className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-foreground font-sans">
            Cohort Analysis: Notified vs Non-Notified
          </h3>
        </div>
        <p className="text-sm text-muted-foreground mb-5">
          Purchase frequency comparison — customers who received notifications vs those who didn't
        </p>

        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cohortChartData} barGap={8}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="period"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <YAxis
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }} />
              <Bar dataKey="Notified" fill="#c084fc" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Not Notified" fill="rgba(255,255,255,0.15)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
}
