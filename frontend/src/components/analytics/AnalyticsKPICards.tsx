/**
 * CONFIT — Analytics KPI Cards
 * ==============================
 * Executive summary KPI cards with trend indicators.
 * Stagger-animated with Framer Motion for premium entrance.
 */

import { motion } from 'framer-motion';
import {
  Send,
  Eye,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus,
  Mail,
  Bell,
  MessageSquare,
  Users,
} from 'lucide-react';
import type { AnalyticsKPI, AnalyticsChannel } from '@/types/notificationAnalyticsTypes';

interface AnalyticsKPICardsProps {
  kpis: AnalyticsKPI;
  filterKey?: string;
}

const CHANNEL_LABELS: Record<AnalyticsChannel, string> = {
  in_app: 'In-App',
  email: 'Email',
  push: 'Push',
  toast: 'Toast',
};

const CHANNEL_ICONS: Record<AnalyticsChannel, typeof Bell> = {
  in_app: MessageSquare,
  email: Mail,
  push: Bell,
  toast: Zap,
};

function TrendBadge({ value, suffix = '' }: { value: number; suffix?: string }) {
  const isPositive = value > 0;
  const isZero = Math.abs(value) < 0.001;
  const Icon = isZero ? Minus : isPositive ? TrendingUp : TrendingDown;
  const color = isZero
    ? 'text-muted-foreground'
    : isPositive
    ? 'text-emerald-400'
    : 'text-red-400';
  const bg = isZero
    ? 'bg-muted/50'
    : isPositive
    ? 'bg-emerald-500/10'
    : 'bg-red-500/10';

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${color} ${bg}`}>
      <Icon className="h-3 w-3" />
      {isZero ? '0.0' : `${isPositive ? '+' : ''}${(value * 100).toFixed(1)}`}{suffix}
    </span>
  );
}

export function AnalyticsKPICards({ kpis, filterKey }: AnalyticsKPICardsProps) {
  const ChannelIcon = CHANNEL_ICONS[kpis.most_used_channel];
  const ConversionIcon = CHANNEL_ICONS[kpis.top_conversion_channel];

  const cards = [
    {
      label: 'Delivery Rate',
      value: `${(kpis.overall_delivery_rate * 100).toFixed(1)}%`,
      trend: kpis.delivery_rate_trend,
      icon: Send,
      accent: 'from-emerald-500/20 to-emerald-600/5',
      iconColor: 'text-emerald-400',
    },
    {
      label: 'Average Open Rate',
      value: `${(kpis.avg_open_rate * 100).toFixed(1)}%`,
      trend: kpis.open_rate_trend,
      icon: Eye,
      accent: 'from-blue-500/20 to-blue-600/5',
      iconColor: 'text-blue-400',
    },
    {
      label: 'Top Channel',
      value: CHANNEL_LABELS[kpis.most_used_channel],
      sub: `${kpis.most_used_channel_count.toLocaleString()} sent`,
      icon: ChannelIcon,
      accent: 'from-amber-500/20 to-amber-600/5',
      iconColor: 'text-amber-400',
    },
    {
      label: 'Best Conversion',
      value: CHANNEL_LABELS[kpis.top_conversion_channel],
      sub: `${(kpis.top_conversion_rate * 100).toFixed(1)}% CTR`,
      icon: ConversionIcon,
      accent: 'from-purple-500/20 to-purple-600/5',
      iconColor: 'text-purple-400',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => {
        const Icon = card.icon;
        return (
          <motion.div
            key={`${card.label}-${filterKey}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.08, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="relative overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-5"
          >
            {/* Gradient accent */}
            <div className={`absolute inset-0 bg-gradient-to-br ${card.accent} pointer-events-none`} />

            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  {card.label}
                </span>
                <div className={`h-8 w-8 rounded-lg bg-white/[0.05] flex items-center justify-center ${card.iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
              </div>

              <div className="text-2xl font-bold text-foreground font-sans tracking-tight">
                {card.value}
              </div>

              <div className="mt-2 flex items-center gap-2">
                {card.trend !== undefined && <TrendBadge value={card.trend} suffix="%" />}
                {card.sub && (
                  <span className="text-xs text-muted-foreground">{card.sub}</span>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
