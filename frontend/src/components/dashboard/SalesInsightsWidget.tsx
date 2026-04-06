/**
 * CONFIT — Sales Insights Widget
 * =================================
 * Luxury B2B data visualization widget for the Store Owner Dashboard.
 * Provides four mini-visualizations that sync with table filters and enable drill-down.
 *
 * Features:
 * - Total Revenue Trend (Line Chart)
 * - Top-Performing Products (Horizontal Bar Chart)
 * - Profit Margin Distribution (Donut Chart)
 * - Return Rate Indicator (Compact Card)
 * - Bi-directional filter synchronization
 * - Drill-down from widget to table
 * - Loading and empty states
 * - Full accessibility support
 */

import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Package,
  AlertTriangle,
  RefreshCw,
  DollarSign,
  BarChart3,
  PieChart,
  RotateCcw,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  BarChart,
  Bar,
  Cell,
  PieChart as RechartsPie,
  Pie,
  Sector,
} from 'recharts';
import { cn } from '@/lib/utils';
import { format, parseISO, startOfDay, endOfDay, eachDayOfInterval, eachWeekOfInterval, startOfWeek, endOfWeek, isWithinInterval, differenceInDays } from 'date-fns';
import type { SaleRecord, SaleCategory, ReturnStatus } from '@/types/dashboard';
import { DURATION_LUXURY, DURATION_STANDARD, EASE_LUXURY, createTransition } from '@/motion';

// ─── Color Palette (CONFIT Luxury) ─────────────────────────────────

const COLORS = {
  gold: '#D4AF37',
  goldLight: 'rgba(212, 175, 55, 0.15)',
  goldGlow: 'rgba(212, 175, 55, 0.35)',
  purple: '#8B5CF6',
  purpleLight: 'rgba(139, 92, 246, 0.15)',
  purpleGlow: 'rgba(139, 92, 246, 0.35)',
  green: '#22C55E',
  greenLight: 'rgba(34, 197, 94, 0.15)',
  amber: '#FBBF24',
  amberLight: 'rgba(251, 191, 36, 0.15)',
  red: '#F87171',
  redLight: 'rgba(248, 113, 113, 0.15)',
  text: '#F5F7FF',
  textMuted: 'rgba(245, 247, 255, 0.70)',
  surface: '#0F1524',
  surfaceElevated: '#151B2E',
  border: 'rgba(255, 255, 255, 0.10)',
};

const MARGIN_COLORS = {
  high: COLORS.green,
  healthy: COLORS.amber,
  atRisk: COLORS.red,
};

// ─── Types ────────────────────────────────────────────────────────

export interface DrillDownFilters {
  productName?: string;
  category?: SaleCategory;
  dateSegment?: { start: string; end: string };
  marginRange?: 'high' | 'healthy' | 'atRisk';
  returnStatus?: ReturnStatus[];
}

export interface SalesInsightsWidgetProps {
  /** Filtered sale records to visualize */
  data: SaleRecord[];
  /** Show loading skeleton */
  isLoading?: boolean;
  /** Error message to display */
  error?: string | null;
  /** Callback when user drills down from widget */
  onDrillDown?: (filters: DrillDownFilters) => void;
  /** Additional CSS class */
  className?: string;
}

// ─── Helper Functions ─────────────────────────────────────────────

function formatCurrency(value: number): string {
  return `EGP ${value.toLocaleString()}`;
}

function formatCompactCurrency(value: number): string {
  if (value >= 1000000) return `EGP ${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `EGP ${(value / 1000).toFixed(0)}K`;
  return `EGP ${value}`;
}

function getMarginCategory(margin: number): 'high' | 'healthy' | 'atRisk' {
  if (margin >= 30) return 'high';
  if (margin >= 15) return 'healthy';
  return 'atRisk';
}

// ─── Custom Tooltip Component ─────────────────────────────────────

interface TooltipPayload {
  name: string;
  value: number;
  payload?: Record<string, unknown>;
}

function CustomTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
  formatter?: (value: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-surface-elevated border border-border/50 rounded-lg px-3 py-2 shadow-lg"
    >
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      {payload.map((entry, index) => (
        <p key={index} className="text-sm font-semibold text-foreground">
          {formatter ? formatter(entry.value) : entry.value.toLocaleString()}
        </p>
      ))}
    </motion.div>
  );
}

// ─── Revenue Trend Card ───────────────────────────────────────────

interface RevenueTrendCardProps {
  data: SaleRecord[];
  onDrillDown?: (filters: DrillDownFilters) => void;
  isLoading?: boolean;
}

function RevenueTrendCard({ data, onDrillDown, isLoading }: RevenueTrendCardProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const { chartData, totalRevenue, trendPercent, previousRevenue } = useMemo(() => {
    if (data.length === 0) {
      return { chartData: [], totalRevenue: 0, trendPercent: 0, previousRevenue: 0 };
    }

    // Determine date range from data
    const dates = data.map(d => parseISO(d.saleDate));
    const minDate = startOfDay(new Date(Math.min(...dates.map(d => d.getTime()))));
    const maxDate = endOfDay(new Date(Math.max(...dates.map(d => d.getTime()))));
    const dayDiff = differenceInDays(maxDate, minDate);

    // Auto-segment: daily if <=14 days, weekly if >14 days
    const useWeekly = dayDiff > 14;

    let segments: Date[] = [];
    if (useWeekly) {
      segments = eachWeekOfInterval({ start: minDate, end: maxDate }, { weekStartsOn: 0 });
    } else {
      segments = eachDayOfInterval({ start: minDate, end: maxDate });
    }

    // Calculate revenue per segment
    const revenueBySegment: Map<string, number> = new Map();
    
    segments.forEach((segStart, idx) => {
      const segEnd = useWeekly
        ? endOfWeek(segStart, { weekStartsOn: 0 })
        : endOfDay(segStart);
      
      const segKey = useWeekly
        ? `Week ${idx + 1}`
        : format(segStart, 'MMM dd');
      
      const segRevenue = data
        .filter(d => {
          const date = parseISO(d.saleDate);
          return isWithinInterval(date, { start: segStart, end: segEnd });
        })
        .reduce((sum, d) => sum + d.price * d.quantity, 0);
      
      revenueBySegment.set(segKey, segRevenue);
    });

    const chartData = Array.from(revenueBySegment.entries()).map(([date, revenue]) => ({
      date,
      revenue,
    }));

    const totalRevenue = chartData.reduce((sum, d) => sum + d.revenue, 0);
    
    // Calculate trend (compare first half vs second half)
    const midPoint = Math.floor(chartData.length / 2);
    const firstHalf = chartData.slice(0, midPoint).reduce((sum, d) => sum + d.revenue, 0);
    const secondHalf = chartData.slice(midPoint).reduce((sum, d) => sum + d.revenue, 0);
    const previousRevenue = firstHalf;
    const trendPercent = firstHalf > 0 ? ((secondHalf - firstHalf) / firstHalf) * 100 : 0;

    return { chartData, totalRevenue, trendPercent, previousRevenue };
  }, [data]);

  const handlePointClick = useCallback(
    (pointData: { date: string; revenue: number }) => {
      if (!onDrillDown || chartData.length === 0) return;

      // Find the date range for this segment
      const dates = data.map(d => parseISO(d.saleDate));
      const minDate = startOfDay(new Date(Math.min(...dates.map(d => d.getTime()))));
      const maxDate = endOfDay(new Date(Math.max(...dates.map(d => d.getTime()))));
      const dayDiff = differenceInDays(maxDate, minDate);
      const useWeekly = dayDiff > 14;

      let segments: Date[] = [];
      if (useWeekly) {
        segments = eachWeekOfInterval({ start: minDate, end: maxDate }, { weekStartsOn: 0 });
      } else {
        segments = eachDayOfInterval({ start: minDate, end: maxDate });
      }

      const idx = chartData.findIndex(d => d.date === pointData.date);
      if (idx >= 0 && idx < segments.length) {
        const segStart = segments[idx];
        const segEnd = useWeekly
          ? endOfWeek(segStart, { weekStartsOn: 0 })
          : endOfDay(segStart);

        onDrillDown({
          dateSegment: {
            start: segStart.toISOString(),
            end: segEnd.toISOString(),
          },
        });
      }
    },
    [onDrillDown, chartData, data]
  );

  const isPositiveTrend = trendPercent >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION_LUXURY, ease: EASE_LUXURY }}
      className="relative overflow-hidden rounded-2xl border border-border/50 bg-surface-elevated/50 backdrop-blur-xl p-5 h-full"
    >
      {/* Gradient accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-[rgba(212,175,55,0.08)] to-transparent pointer-events-none" />

      <div className="relative">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-goldLight flex items-center justify-center">
              <TrendingUp className="h-4 w-4" style={{ color: COLORS.gold }} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Revenue Trend</h3>
              <p className="text-xs text-muted-foreground">Over selected period</p>
            </div>
          </div>
          {trendPercent !== 0 && (
            <div
              className={cn(
                'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                isPositiveTrend ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
              )}
            >
              {isPositiveTrend ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {isPositiveTrend ? '+' : ''}{trendPercent.toFixed(1)}%
            </div>
          )}
        </div>

        {/* Total */}
        <div className="mb-4">
          <p className="text-2xl font-bold text-foreground font-sans tracking-tight">
            {formatCompactCurrency(totalRevenue)}
          </p>
        </div>

        {/* Chart */}
        <div className="h-[120px] w-full">
          {isLoading ? (
            <div className="h-full w-full flex items-center justify-center">
              <div className="h-4 w-3/4 rounded bg-muted/30 animate-pulse" />
            </div>
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
                onMouseMove={(_, index) => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
                onClick={(chartData) => {
                  if (chartData && 'activePayload' in chartData) {
                    const payload = chartData.activePayload?.[0]?.payload;
                    if (payload) {
                      handlePointClick(payload as { date: string; revenue: number });
                    }
                  }
                }}
              >
                <defs>
                  <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={COLORS.gold} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={COLORS.gold} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: COLORS.textMuted, fontSize: 10 }}
                  interval="preserveStartEnd"
                  tickFormatter={(value) => value.length > 8 ? value.slice(0, 8) : value}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: COLORS.textMuted, fontSize: 10 }}
                  tickFormatter={(value) => formatCompactCurrency(value).replace('EGP ', '')}
                  width={45}
                />
                <RechartsTooltip
                  content={<CustomTooltip formatter={formatCurrency} />}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke={COLORS.gold}
                  strokeWidth={2}
                  fill="url(#revenueGradient)"
                  dot={false}
                  activeDot={{
                    r: 5,
                    fill: COLORS.gold,
                    stroke: COLORS.surface,
                    strokeWidth: 2,
                    style: { cursor: onDrillDown ? 'pointer' : 'default' },
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
              No data available
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Top Products Card ────────────────────────────────────────────

interface TopProductsCardProps {
  data: SaleRecord[];
  onDrillDown?: (filters: DrillDownFilters) => void;
  isLoading?: boolean;
}

function TopProductsCard({ data, onDrillDown, isLoading }: TopProductsCardProps) {
  const topProducts = useMemo(() => {
    const productRevenue: Map<string, { revenue: number; quantity: number; margin: number; count: number }> = new Map();

    data.forEach(record => {
      const existing = productRevenue.get(record.productName) || { revenue: 0, quantity: 0, margin: 0, count: 0 };
      productRevenue.set(record.productName, {
        revenue: existing.revenue + record.price * record.quantity,
        quantity: existing.quantity + record.quantity,
        margin: existing.margin + record.profitMargin,
        count: existing.count + 1,
      });
    });

    return Array.from(productRevenue.entries())
      .map(([name, stats]) => ({
        name,
        revenue: stats.revenue,
        quantity: stats.quantity,
        avgMargin: Math.round(stats.margin / stats.count),
      }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 5);
  }, [data]);

  const handleBarClick = useCallback(
    (productName: string) => {
      if (onDrillDown) {
        onDrillDown({ productName });
      }
    },
    [onDrillDown]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION_LUXURY, delay: 0.1, ease: EASE_LUXURY }}
      className="relative overflow-hidden rounded-2xl border border-border/50 bg-surface-elevated/50 backdrop-blur-xl p-5 h-full"
    >
      {/* Gradient accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-purpleLight to-transparent pointer-events-none" />

      <div className="relative">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <div className="h-8 w-8 rounded-lg bg-purpleLight flex items-center justify-center">
            <BarChart3 className="h-4 w-4" style={{ color: COLORS.purple }} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Top Products</h3>
            <p className="text-xs text-muted-foreground">By revenue</p>
          </div>
        </div>

        {/* Chart */}
        <div className="h-[180px] w-full">
          {isLoading ? (
            <div className="space-y-3 py-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="h-3 w-20 rounded bg-muted/30 animate-pulse" />
                  <div className="flex-1 h-3 rounded bg-muted/20 animate-pulse" />
                </div>
              ))}
            </div>
          ) : topProducts.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={topProducts}
                layout="vertical"
                margin={{ top: 5, right: 60, left: 0, bottom: 5 }}
              >
                <XAxis
                  type="number"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: COLORS.textMuted, fontSize: 10 }}
                  tickFormatter={(value) => formatCompactCurrency(value).replace('EGP ', '')}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: COLORS.textMuted, fontSize: 10 }}
                  width={80}
                  tickFormatter={(value) => value.length > 12 ? `${value.slice(0, 12)}...` : value}
                />
                <RechartsTooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    const data = payload[0].payload as { name: string; revenue: number; quantity: number; avgMargin: number };
                    return (
                      <div className="bg-surface-elevated border border-border/50 rounded-lg px-3 py-2 shadow-lg">
                        <p className="text-sm font-semibold text-foreground mb-1">{data.name}</p>
                        <p className="text-xs text-muted-foreground">Revenue: {formatCurrency(data.revenue)}</p>
                        <p className="text-xs text-muted-foreground">Qty: {data.quantity} sold</p>
                        <p className="text-xs text-muted-foreground">Avg Margin: {data.avgMargin}%</p>
                      </div>
                    );
                  }}
                />
                <Bar
                  dataKey="revenue"
                  radius={[0, 4, 4, 0]}
                  onClick={(data: { name: string }) => handleBarClick(data.name)}
                  style={{ cursor: onDrillDown ? 'pointer' : 'default' }}
                >
                  {topProducts.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={index === 0 ? COLORS.gold : COLORS.purple}
                      fillOpacity={index === 0 ? 1 : 0.7}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
              No data available
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Profit Margin Distribution Card ───────────────────────────────

interface MarginDistributionCardProps {
  data: SaleRecord[];
  onDrillDown?: (filters: DrillDownFilters) => void;
  isLoading?: boolean;
}

function MarginDistributionCard({ data, onDrillDown, isLoading }: MarginDistributionCardProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const { chartData, avgMargin, totalSales } = useMemo(() => {
    const categories = {
      high: { name: 'High', value: 0, count: 0, color: COLORS.green, range: '>30%' },
      healthy: { name: 'Healthy', value: 0, count: 0, color: COLORS.amber, range: '15-30%' },
      atRisk: { name: 'At Risk', value: 0, count: 0, color: COLORS.red, range: '<15%' },
    };

    let totalMargin = 0;
    const totalSales = data.length;

    data.forEach(record => {
      const category = getMarginCategory(record.profitMargin);
      categories[category].value += record.price * record.quantity;
      categories[category].count += 1;
      totalMargin += record.profitMargin;
    });

    const chartData = Object.values(categories)
      .filter(c => c.count > 0)
      .map(c => ({
        name: c.name,
        value: c.value,
        count: c.count,
        color: c.color,
        range: c.range,
      }));

    const avgMargin = totalSales > 0 ? Math.round(totalMargin / totalSales) : 0;

    return { chartData, avgMargin, totalSales };
  }, [data]);

  const handleSegmentClick = useCallback(
    (segmentName: string) => {
      if (!onDrillDown) return;

      const marginMap: Record<string, 'high' | 'healthy' | 'atRisk'> = {
        'High': 'high',
        'Healthy': 'healthy',
        'At Risk': 'atRisk',
      };

      onDrillDown({ marginRange: marginMap[segmentName] });
    },
    [onDrillDown]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION_LUXURY, delay: 0.2, ease: EASE_LUXURY }}
      className="relative overflow-hidden rounded-2xl border border-border/50 bg-surface-elevated/50 backdrop-blur-xl p-5 h-full"
    >
      {/* Gradient accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-greenLight to-transparent pointer-events-none" />

      <div className="relative">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <div className="h-8 w-8 rounded-lg bg-greenLight flex items-center justify-center">
            <PieChart className="h-4 w-4" style={{ color: COLORS.green }} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Profit Margin</h3>
            <p className="text-xs text-muted-foreground">Distribution</p>
          </div>
        </div>

        {/* Avg Margin */}
        <div className="mb-4">
          <p className="text-2xl font-bold text-foreground font-sans tracking-tight">
            {avgMargin}%
            <span className="text-sm font-normal text-muted-foreground ml-2">avg</span>
          </p>
        </div>

        {/* Chart */}
        <div className="h-[140px] w-full flex items-center justify-center">
          {isLoading ? (
            <div className="h-20 w-20 rounded-full border-4 border-muted/30 animate-pulse" />
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <RechartsPie>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={60}
                  paddingAngle={2}
                  dataKey="value"
                  onMouseEnter={(_, index) => setActiveIndex(index)}
                  onMouseLeave={() => setActiveIndex(null)}
                  onClick={(data) => handleSegmentClick(data.name)}
                  style={{ cursor: onDrillDown ? 'pointer' : 'default' }}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.color}
                      fillOpacity={activeIndex === index ? 1 : 0.75}
                      stroke={COLORS.surface}
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <RechartsTooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    const data = payload[0].payload as { name: string; value: number; count: number; range: string; color: string };
                    return (
                      <div 
                        className="bg-surface-elevated border border-border/50 rounded-lg px-3 py-2 shadow-lg"
                        style={{ '--tooltip-accent': data.color } as React.CSSProperties}
                      >
                        <p className="text-sm font-semibold mb-1 text-[var(--tooltip-accent)]">
                          {data.name} ({data.range})
                        </p>
                        <p className="text-xs text-muted-foreground">Revenue: {formatCurrency(data.value)}</p>
                        <p className="text-xs text-muted-foreground">{data.count} sales</p>
                      </div>
                    );
                  }}
                />
              </RechartsPie>
            </ResponsiveContainer>
          ) : (
            <div className="text-muted-foreground text-sm">No data available</div>
          )}
        </div>

        {/* Legend */}
        {!isLoading && chartData.length > 0 && (
          <div className="flex justify-center gap-4 mt-2">
            {chartData.map((entry) => (
              <button
                key={entry.name}
                onClick={() => handleSegmentClick(entry.name)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                aria-label={`Filter by ${entry.name} margin`}
              >
                <span
                  className="h-2 w-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: entry.color } as React.CSSProperties}
                />
                {entry.name}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─── Return Rate Card ──────────────────────────────────────────────

interface ReturnRateCardProps {
  data: SaleRecord[];
  onDrillDown?: (filters: DrillDownFilters) => void;
  isLoading?: boolean;
}

function ReturnRateCard({ data, onDrillDown, isLoading }: ReturnRateCardProps) {
  const { returnRate, returnedCount, pendingCount, totalSales, status } = useMemo(() => {
    const totalSales = data.length;
    const returned = data.filter(d => d.returnStatus === 'Returned').length;
    const pending = data.filter(d => d.returnStatus === 'Pending Return').length;
    const returnRate = totalSales > 0 ? ((returned + pending) / totalSales) * 100 : 0;

    let status: 'Low' | 'Moderate' | 'High';
    if (returnRate < 5) status = 'Low';
    else if (returnRate < 15) status = 'Moderate';
    else status = 'High';

    return { returnRate, returnedCount: returned, pendingCount: pending, totalSales, status };
  }, [data]);

  const statusColor = useMemo(() => {
    switch (status) {
      case 'Low': return { bg: 'bg-green-500/10', text: 'text-green-400', bar: COLORS.green };
      case 'Moderate': return { bg: 'bg-amber-500/10', text: 'text-amber-400', bar: COLORS.amber };
      case 'High': return { bg: 'bg-red-500/10', text: 'text-red-400', bar: COLORS.red };
    }
  }, [status]);

  const handleClick = useCallback(() => {
    if (onDrillDown && (returnedCount > 0 || pendingCount > 0)) {
      onDrillDown({ returnStatus: ['Returned', 'Pending Return'] });
    }
  }, [onDrillDown, returnedCount, pendingCount]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION_LUXURY, delay: 0.3, ease: EASE_LUXURY }}
      onClick={handleClick}
      className={cn(
        'relative overflow-hidden rounded-2xl border border-border/50 bg-surface-elevated/50 backdrop-blur-xl p-5 h-full',
        onDrillDown && (returnedCount > 0 || pendingCount > 0) && 'cursor-pointer hover:border-border/80 transition-colors'
      )}
      role={onDrillDown ? 'button' : undefined}
      tabIndex={onDrillDown && (returnedCount > 0 || pendingCount > 0) ? 0 : undefined}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`Return rate: ${returnRate.toFixed(1)}%. ${returnedCount} returned, ${pendingCount} pending. Click to filter.`}
    >
      {/* Gradient accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-redLight to-transparent pointer-events-none" />

      <div className="relative">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <div className="h-8 w-8 rounded-lg bg-redLight flex items-center justify-center">
            <RotateCcw className="h-4 w-4" style={{ color: COLORS.red }} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Return Rate</h3>
            <p className="text-xs text-muted-foreground">Returns & pending</p>
          </div>
        </div>

        {/* Main Metric */}
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-10 w-24 rounded bg-muted/30 animate-pulse" />
            <div className="h-3 w-32 rounded bg-muted/20 animate-pulse" />
          </div>
        ) : (
          <>
            <div className="flex items-baseline gap-3 mb-4">
              <p className="text-3xl font-bold text-foreground font-sans tracking-tight">
                {returnRate.toFixed(1)}%
              </p>
              <span
                className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  statusColor.bg,
                  statusColor.text
                )}
              >
                {status}
              </span>
            </div>

            {/* Progress bar */}
            <div className="mb-4">
              <div className="h-2 w-full rounded-full bg-muted/20 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(returnRate, 100)}%` }}
                  transition={{ duration: DURATION_STANDARD, ease: EASE_LUXURY }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: statusColor.bar }}
                />
              </div>
            </div>

            {/* Details */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>
                <span className="text-red-400 font-medium">{returnedCount}</span> returned
              </span>
              <span>
                <span className="text-amber-400 font-medium">{pendingCount}</span> pending
              </span>
            </div>

            <p className="text-xs text-muted-foreground mt-2">
              {totalSales} total sales
            </p>
          </>
        )}
      </div>
    </motion.div>
  );
}

// ─── Empty State ───────────────────────────────────────────────────

function WidgetEmptyState({ onClearFilters }: { onClearFilters?: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION_LUXURY, ease: EASE_LUXURY }}
      className="col-span-full rounded-2xl border border-border/50 bg-surface-elevated/50 backdrop-blur-xl p-12 text-center"
    >
      <div className="h-16 w-16 rounded-2xl bg-muted/20 flex items-center justify-center mx-auto mb-4">
        <Package className="h-8 w-8 text-muted-foreground/40" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2 font-sans">
        No sales data available
      </h3>
      <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-6">
        No sales match your current filters. Try adjusting your filter criteria.
      </p>
      {onClearFilters && (
        <button
          onClick={onClearFilters}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-accent/30 text-accent text-sm hover:bg-accent/10 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Clear All Filters
        </button>
      )}
    </motion.div>
  );
}

// ─── Error State ───────────────────────────────────────────────────

function WidgetErrorState({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION_LUXURY, ease: EASE_LUXURY }}
      className="col-span-full rounded-2xl border border-border/50 bg-surface-elevated/50 backdrop-blur-xl p-12 text-center"
    >
      <div className="h-16 w-16 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="h-8 w-8 text-destructive/60" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2 font-sans">
        Unable to Load Insights
      </h3>
      <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-6">
        {error || 'Something went wrong while loading sales insights. Please try again.'}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-accent/30 text-accent text-sm hover:bg-accent/10 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </button>
      )}
    </motion.div>
  );
}

// ─── Main Widget Component ────────────────────────────────────────

export function SalesInsightsWidget({
  data,
  isLoading = false,
  error = null,
  onDrillDown,
  className,
}: SalesInsightsWidgetProps) {
  // Error state
  if (error) {
    return (
      <div className={cn('grid grid-cols-1 md:grid-cols-2 gap-4', className)}>
        <WidgetErrorState error={error} />
      </div>
    );
  }

  // Empty state (only if not loading)
  if (!isLoading && data.length === 0) {
    return (
      <div className={cn('grid grid-cols-1 md:grid-cols-2 gap-4', className)}>
        <WidgetEmptyState />
      </div>
    );
  }

  return (
    <div
      className={cn('grid grid-cols-1 md:grid-cols-2 gap-4', className)}
      role="region"
      aria-label="Sales insights dashboard"
    >
      <AnimatePresence mode="wait">
        {/* Revenue Trend */}
        <RevenueTrendCard
          data={data}
          onDrillDown={onDrillDown}
          isLoading={isLoading}
        />

        {/* Top Products */}
        <TopProductsCard
          data={data}
          onDrillDown={onDrillDown}
          isLoading={isLoading}
        />

        {/* Margin Distribution */}
        <MarginDistributionCard
          data={data}
          onDrillDown={onDrillDown}
          isLoading={isLoading}
        />

        {/* Return Rate */}
        <ReturnRateCard
          data={data}
          onDrillDown={onDrillDown}
          isLoading={isLoading}
        />
      </AnimatePresence>
    </div>
  );
}

export default SalesInsightsWidget;
