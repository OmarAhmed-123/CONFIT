/**
 * CONFIT Analytics Shared Components
 * Reusable components for analytics dashboards
 */

import { motion } from 'framer-motion';
import {
  TrendingUp, TrendingDown, Users, ShoppingBag, DollarSign,
  Eye, RefreshCw, MapPin, Clock, Package, AlertTriangle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell, LineChart, Line, Legend
} from 'recharts';
import { cn } from '@/lib/utils';
import { EASE_LUXURY } from '@/motion';
import type { ReactNode } from 'react';

// ===========================================
// KPI Card Component
// ===========================================

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  format?: 'number' | 'currency' | 'percent';
  currency?: string;
  loading?: boolean;
  positive?: boolean;
}

export function KPICard({
  title,
  value,
  change,
  changeLabel = 'vs last period',
  icon,
  format = 'number',
  currency = 'EGP',
  loading = false,
  positive = true,
}: KPICardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === 'number') {
      switch (format) {
        case 'currency':
          return `${val.toLocaleString()} ${currency}`;
        case 'percent':
          return `${val.toFixed(1)}%`;
        default:
          return val.toLocaleString();
      }
    }
    return val;
  };

  if (loading) {
    return (
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="p-6">
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-8 w-32 mb-1" />
          <Skeleton className="h-3 w-20" />
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE_LUXURY }}
    >
      <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-accent/30 transition-colors">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm text-muted-foreground font-medium">{title}</p>
              <p className="text-2xl font-bold mt-1 text-foreground">
                {formatValue(value)}
              </p>
              {change !== undefined && (
                <div className={cn(
                  "flex items-center gap-1 mt-2 text-xs",
                  change >= 0 ? "text-green-500" : "text-red-500"
                )}>
                  {change >= 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  <span>{Math.abs(change).toFixed(1)}%</span>
                  <span className="text-muted-foreground">{changeLabel}</span>
                </div>
              )}
            </div>
            {icon && (
              <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center">
                <span className="text-accent">{icon}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ===========================================
// KPI Grid Component
// ===========================================

interface KPIGridProps {
  children: ReactNode;
  columns?: 2 | 3 | 4;
}

export function KPIGrid({ children, columns = 4 }: KPIGridProps) {
  const gridCols = {
    2: 'sm:grid-cols-2',
    3: 'sm:grid-cols-2 lg:grid-cols-3',
    4: 'sm:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={cn("grid gap-4", gridCols[columns])}>
      {children}
    </div>
  );
}

// ===========================================
// Chart Wrapper Component
// ===========================================

interface ChartWrapperProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  loading?: boolean;
  className?: string;
  action?: ReactNode;
}

export function ChartWrapper({
  title,
  subtitle,
  children,
  loading = false,
  className,
  action,
}: ChartWrapperProps) {
  return (
    <Card className={cn("bg-card/50 backdrop-blur-sm border-border/50", className)}>
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div>
          <CardTitle className="text-lg font-semibold">{title}</CardTitle>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        {action}
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-[300px] flex items-center justify-center">
            <Skeleton className="h-full w-full" />
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}

// ===========================================
// Heatmap Component
// ===========================================

interface HeatmapCell {
  hour: number;
  day_of_week: number;
  visitor_count: number;
}

interface HeatmapProps {
  data: HeatmapCell[];
  loading?: boolean;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

export function VisitorHeatmap({ data, loading = false }: HeatmapProps) {
  if (loading) {
    return (
      <div className="h-[200px]">
        <Skeleton className="h-full w-full" />
      </div>
    );
  }

  const maxValue = Math.max(...data.map(d => d.visitor_count), 1);

  const getColor = (value: number) => {
    const intensity = value / maxValue;
    if (intensity === 0) return 'bg-muted/20';
    if (intensity < 0.25) return 'bg-accent/20';
    if (intensity < 0.5) return 'bg-accent/40';
    if (intensity < 0.75) return 'bg-accent/60';
    return 'bg-accent';
  };

  const getCellValue = (day: number, hour: number) => {
    const cell = data.find(d => d.day_of_week === day && d.hour === hour);
    return cell?.visitor_count || 0;
  };

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[600px]">
        <div className="flex">
          <div className="w-12" />
          {HOURS.map(hour => (
            <div
              key={hour}
              className="w-8 text-center text-xs text-muted-foreground"
            >
              {hour.toString().padStart(2, '0')}
            </div>
          ))}
        </div>
        {DAYS.map((day, dayIndex) => (
          <div key={day} className="flex items-center mt-1">
            <div className="w-12 text-xs text-muted-foreground pr-2 text-right">
              {day}
            </div>
            {HOURS.map(hour => {
              const value = getCellValue(dayIndex, hour);
              return (
                <div
                  key={hour}
                  className={cn(
                    "w-8 h-6 rounded-sm mx-0.5 flex items-center justify-center text-xs",
                    getColor(value)
                  )}
                  title={`${day} ${hour}:00 - ${value} visitors`}
                >
                  {value > 0 ? value : ''}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

// ===========================================
// Top Products Table
// ===========================================

interface TopProduct {
  product_id: string | null;
  sku: string;
  view_count?: number;
  purchase_count?: number;
  revenue_egp?: number;
}

interface TopProductsTableProps {
  products: TopProduct[];
  type: 'viewed' | 'purchased';
  loading?: boolean;
}

export function TopProductsTable({ products, type, loading = false }: TopProductsTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  const valueKey = type === 'viewed' ? 'view_count' : 'purchase_count';
  const valueLabel = type === 'viewed' ? 'Views' : 'Purchases';

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left p-3 text-sm font-medium text-muted-foreground">SKU</th>
            <th className="text-right p-3 text-sm font-medium text-muted-foreground">{valueLabel}</th>
            {type === 'purchased' && (
              <th className="text-right p-3 text-sm font-medium text-muted-foreground">Revenue</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {products.map((product, index) => (
            <motion.tr
              key={product.sku || index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className="hover:bg-muted/30 transition-colors"
            >
              <td className="p-3 text-sm font-medium">{product.sku}</td>
              <td className="p-3 text-sm text-right text-muted-foreground">
                {product[valueKey]?.toLocaleString() || 0}
              </td>
              {type === 'purchased' && (
                <td className="p-3 text-sm text-right text-muted-foreground">
                  {product.revenue_egp?.toLocaleString()} EGP
                </td>
              )}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ===========================================
// Regional Sales Chart
// ===========================================

interface RegionalData {
  city: string;
  sales_count: number;
  revenue_egp: number;
}

interface RegionalSalesChartProps {
  data: RegionalData[];
  loading?: boolean;
}

const CHART_COLORS = [
  '#8884d8', '#83a6ed', '#8dd1e1', '#82ca9d', '#a4de6c',
  '#d0ed57', '#ffc658', '#ff8042', '#d8884d', '#b884d8'
];

export function RegionalSalesChart({ data, loading = false }: RegionalSalesChartProps) {
  if (loading) {
    return (
      <div className="h-[300px]">
        <Skeleton className="h-full w-full" />
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data.slice(0, 10)} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={12} />
        <YAxis
          type="category"
          dataKey="city"
          stroke="hsl(var(--muted-foreground))"
          fontSize={12}
          width={80}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
        <Bar dataKey="revenue_egp" fill="hsl(var(--accent))" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ===========================================
// Donut Chart Component
// ===========================================

interface DonutData {
  name: string;
  value: number;
}

interface DonutChartProps {
  data: DonutData[];
  loading?: boolean;
  innerRadius?: number;
  outerRadius?: number;
}

export function DonutChart({
  data,
  loading = false,
  innerRadius = 60,
  outerRadius = 80,
}: DonutChartProps) {
  if (loading) {
    return (
      <div className="h-[200px] flex items-center justify-center">
        <Skeleton className="h-40 w-40 rounded-full" />
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={innerRadius}
          outerRadius={outerRadius}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
        <Legend
          verticalAlign="bottom"
          height={36}
          formatter={(value) => (
            <span className="text-sm text-muted-foreground">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

// ===========================================
// Line Chart Component
// ===========================================

interface LineData {
  date: string;
  value: number;
  [key: string]: string | number;
}

interface LineChartComponentProps {
  data: LineData[];
  lines: { key: string; color?: string; name?: string }[];
  loading?: boolean;
  xKey?: string;
}

export function LineChartComponent({
  data,
  lines,
  loading = false,
  xKey = 'date',
}: LineChartComponentProps) {
  if (loading) {
    return (
      <div className="h-[300px]">
        <Skeleton className="h-full w-full" />
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey={xKey}
          stroke="hsl(var(--muted-foreground))"
          fontSize={12}
          tickFormatter={(value) => {
            if (typeof value === 'string' && value.includes('-')) {
              const parts = value.split('-');
              return `${parts[1]}/${parts[2]?.slice(2)}`;
            }
            return value;
          }}
        />
        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
        <Legend />
        {lines.map((line, index) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name || line.key}
            stroke={line.color || CHART_COLORS[index % CHART_COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// ===========================================
// Area Chart Component
// ===========================================

interface AreaData {
  date: string;
  value: number;
}

interface AreaChartComponentProps {
  data: AreaData[];
  loading?: boolean;
  color?: string;
}

export function AreaChartComponent({
  data,
  loading = false,
  color = 'hsl(var(--accent))',
}: AreaChartComponentProps) {
  if (loading) {
    return (
      <div className="h-[200px]">
        <Skeleton className="h-full w-full" />
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey="date"
          stroke="hsl(var(--muted-foreground))"
          fontSize={12}
          tickFormatter={(value) => {
            const parts = value.split('-');
            return `${parts[1]}/${parts[2]?.slice(2)}`;
          }}
        />
        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          fillOpacity={1}
          fill="url(#colorValue)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ===========================================
// Status Badge Component
// ===========================================

interface StatusBadgeProps {
  status: 'success' | 'warning' | 'error' | 'info';
  children: ReactNode;
}

export function StatusBadge({ status, children }: StatusBadgeProps) {
  const variants = {
    success: 'bg-green-500/10 text-green-500 border-green-500/20',
    warning: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    error: 'bg-red-500/10 text-red-500 border-red-500/20',
    info: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  };

  return (
    <Badge variant="outline" className={cn('font-medium', variants[status])}>
      {children}
    </Badge>
  );
}

// ===========================================
// Empty State Component
// ===========================================

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-12 text-center"
    >
      {icon && (
        <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </motion.div>
  );
}

// ===========================================
// Loading Spinner Component
// ===========================================

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div className={cn('animate-spin', sizes[size], className)}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        className="text-accent"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </div>
  );
}
