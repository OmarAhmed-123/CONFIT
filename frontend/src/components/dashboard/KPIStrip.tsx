/**
 * CONFIT — KPI Strip
 * ====================
 * Four animated KPI cards for the Store Owner Dashboard.
 * Responds to filter changes via AnimatePresence keyed re-renders.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, TrendingDown, DollarSign, Percent, RotateCcw, ShoppingBag } from 'lucide-react';
import type { KPIData, KPIValue } from '@/types/dashboard';
import { cn } from '@/lib/utils';
import { EASE_LUXURY } from '@/motion';

interface KPIStripProps {
  data: KPIData;
  filterKey: string; // changes trigger re-animation
}

interface KPICardDef {
  label: string;
  icon: React.ReactNode;
  value: KPIValue;
  invertDelta?: boolean; // true for return rate where lower is better
}

export function KPIStrip({ data, filterKey }: KPIStripProps) {
  const cards: KPICardDef[] = [
    {
      label: 'Total Sales',
      icon: <DollarSign className="h-5 w-5" />,
      value: data.totalSales,
    },
    {
      label: 'Conversion Rate',
      icon: <ShoppingBag className="h-5 w-5" />,
      value: data.conversionRate,
    },
    {
      label: 'Return Rate',
      icon: <RotateCcw className="h-5 w-5" />,
      value: data.returnRate,
      invertDelta: true,
    },
    {
      label: 'Avg Order Value',
      icon: <Percent className="h-5 w-5" />,
      value: data.avgOrderValue,
    },
  ];

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={filterKey}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: { opacity: 0 },
          visible: {
            opacity: 1,
            transition: { staggerChildren: 0.08, delayChildren: 0.05 },
          },
        }}
      >
        {cards.map((card, i) => (
          <KPICard key={card.label} card={card} index={i} />
        ))}
      </motion.div>
    </AnimatePresence>
  );
}

function KPICard({ card, index }: { card: KPICardDef; index: number }) {
  const isPositive = card.invertDelta ? card.value.delta <= 0 : card.value.delta >= 0;
  const TrendIcon = card.value.delta >= 0 ? TrendingUp : TrendingDown;

  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.5, ease: EASE_LUXURY },
        },
      }}
      className="glass-card rounded-2xl p-5 lg:p-6 group"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-muted-foreground text-sm font-medium">{card.label}</span>
        <div className="h-9 w-9 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
          {card.icon}
        </div>
      </div>

      {/* Value */}
      <div className="text-2xl lg:text-3xl font-bold text-foreground tracking-tight font-sans mb-2">
        {card.value.formatted}
      </div>

      {/* Trend */}
      <div className="flex items-center gap-1.5">
        <div
          className={cn(
            'flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold',
            isPositive
              ? 'bg-green-500/10 text-green-400'
              : 'bg-red-500/10 text-red-400'
          )}
        >
          <TrendIcon className="h-3 w-3" />
          {Math.abs(card.value.delta)}%
        </div>
        <span className="text-xs text-muted-foreground">vs prev period</span>
      </div>
    </motion.div>
  );
}

export default KPIStrip;
