/**
 * CONFIT — Engagement Heatmap
 * =============================
 * Day-of-week × hour-of-day heatmap showing notification engagement.
 * Toggle between customer and owner views.
 * Color scale from muted to gold (high engagement).
 */

import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Grid3X3, Users, Store } from 'lucide-react';
import type { HeatmapCell, AnalyticsRecipientType } from '@/types/notificationAnalyticsTypes';

interface EngagementHeatmapProps {
  customerData: HeatmapCell[];
  ownerData: HeatmapCell[];
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOUR_LABELS = Array.from({ length: 24 }, (_, i) =>
  i === 0 ? '12a' : i < 12 ? `${i}a` : i === 12 ? '12p' : `${i - 12}p`
);

function getCellColor(rate: number, maxRate: number): string {
  if (maxRate === 0) return 'rgba(255,255,255,0.02)';
  const intensity = rate / maxRate;
  if (intensity < 0.1) return 'rgba(255,255,255,0.02)';
  if (intensity < 0.25) return 'rgba(212,175,55,0.08)';
  if (intensity < 0.4) return 'rgba(212,175,55,0.18)';
  if (intensity < 0.55) return 'rgba(212,175,55,0.30)';
  if (intensity < 0.7) return 'rgba(212,175,55,0.45)';
  if (intensity < 0.85) return 'rgba(212,175,55,0.60)';
  return 'rgba(212,175,55,0.80)';
}

export function EngagementHeatmap({ customerData, ownerData }: EngagementHeatmapProps) {
  const [recipientView, setRecipientView] = useState<AnalyticsRecipientType>('customer');
  const [hoveredCell, setHoveredCell] = useState<HeatmapCell | null>(null);
  const [metric, setMetric] = useState<'open_rate' | 'click_rate'>('open_rate');

  const data = recipientView === 'customer' ? customerData : ownerData;

  const maxRate = useMemo(() => {
    return Math.max(...data.map((c) => c[metric]), 0.01);
  }, [data, metric]);

  // Build grid: rows = days, cols = hours
  const grid = useMemo(() => {
    const map = new Map<string, HeatmapCell>();
    data.forEach((c) => map.set(`${c.day}-${c.hour}`, c));
    return DAY_LABELS.map((_, dayIdx) =>
      HOUR_LABELS.map((_, hourIdx) => map.get(`${dayIdx}-${hourIdx}`) || {
        day: dayIdx, hour: hourIdx, open_rate: 0, click_rate: 0, event_count: 0,
      })
    );
  }, [data]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <Grid3X3 className="h-5 w-5 text-amber-400" />
            <h3 className="text-lg font-semibold text-foreground font-sans">
              Engagement Heatmap
            </h3>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Peak engagement windows by day and hour
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Metric toggle */}
          <div className="flex items-center gap-1 rounded-lg bg-white/[0.04] p-1">
            <button
              onClick={() => setMetric('open_rate')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                metric === 'open_rate' ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Open Rate
            </button>
            <button
              onClick={() => setMetric('click_rate')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                metric === 'click_rate' ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Click Rate
            </button>
          </div>

          {/* Recipient toggle */}
          <div className="flex items-center gap-1 rounded-lg bg-white/[0.04] p-1">
            <button
              onClick={() => setRecipientView('customer')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                recipientView === 'customer' ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              Customers
            </button>
            <button
              onClick={() => setRecipientView('owner')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                recipientView === 'owner' ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Store className="h-3.5 w-3.5" />
              Owners
            </button>
          </div>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          {/* Hour labels */}
          <div className="flex ml-12 mb-1">
            {HOUR_LABELS.map((label, i) => (
              <div
                key={i}
                className="flex-1 text-center text-[10px] text-muted-foreground"
                style={{ minWidth: 24 }}
              >
                {i % 3 === 0 ? label : ''}
              </div>
            ))}
          </div>

          {/* Grid rows */}
          {grid.map((row, dayIdx) => (
            <div key={dayIdx} className="flex items-center gap-1 mb-1">
              <div className="w-10 text-xs text-muted-foreground text-right pr-2 font-medium">
                {DAY_LABELS[dayIdx]}
              </div>
              <div className="flex flex-1 gap-[2px]">
                {row.map((cell, hourIdx) => (
                  <div
                    key={hourIdx}
                    className="flex-1 rounded-[3px] cursor-pointer transition-all duration-150 hover:ring-1 hover:ring-white/20"
                    style={{
                      backgroundColor: getCellColor(cell[metric], maxRate),
                      minWidth: 24,
                      height: 28,
                    }}
                    onMouseEnter={() => setHoveredCell(cell)}
                    onMouseLeave={() => setHoveredCell(null)}
                    title={`${DAY_LABELS[cell.day]} ${HOUR_LABELS[cell.hour]} — ${(cell[metric] * 100).toFixed(1)}% (${cell.event_count} events)`}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Tooltip / Legend */}
      <div className="flex items-center justify-between mt-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Low</span>
          <div className="flex gap-[2px]">
            {[0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95].map((v) => (
              <div
                key={v}
                className="w-5 h-3 rounded-sm"
                style={{ backgroundColor: getCellColor(v, 1) }}
              />
            ))}
          </div>
          <span className="text-xs text-muted-foreground">High</span>
        </div>

        {hoveredCell && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-muted-foreground"
          >
            {DAY_LABELS[hoveredCell.day]} {HOUR_LABELS[hoveredCell.hour]}:{' '}
            <span className="text-foreground font-medium">
              {(hoveredCell[metric] * 100).toFixed(1)}%
            </span>{' '}
            ({hoveredCell.event_count} events)
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
