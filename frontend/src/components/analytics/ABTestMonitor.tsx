/**
 * CONFIT — A/B Test Monitor
 * ===========================
 * Active test dashboard showing side-by-side variant comparison,
 * progress bars, metric charts, and statistical significance indicators.
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  FlaskConical,
  Play,
  Pause,
  CheckCircle2,
  Clock,
  TrendingUp,
  AlertTriangle,
  Award,
} from 'lucide-react';
import { useABTestStore } from '@/stores/abTestStore';
import type { ABTest, ABTestStatus } from '@/types/notificationAnalyticsTypes';

const STATUS_CONFIG: Record<ABTestStatus, {
  label: string;
  color: string;
  bg: string;
  icon: typeof Play;
}> = {
  draft: { label: 'Draft', color: 'text-gray-400', bg: 'bg-gray-500/10', icon: Clock },
  running: { label: 'Running', color: 'text-emerald-400', bg: 'bg-emerald-500/10', icon: Play },
  paused: { label: 'Paused', color: 'text-amber-400', bg: 'bg-amber-500/10', icon: Pause },
  completed: { label: 'Completed', color: 'text-blue-400', bg: 'bg-blue-500/10', icon: CheckCircle2 },
  archived: { label: 'Archived', color: 'text-gray-500', bg: 'bg-gray-600/10', icon: CheckCircle2 },
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null;
  return (
    <div className="rounded-xl border border-white/[0.08] bg-[hsl(220,25%,10%)] p-3 shadow-xl">
      <p className="text-xs font-medium text-muted-foreground mb-2">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium text-foreground">{(entry.value * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

function TestCard({ test }: { test: ABTest }) {
  const { startTest, pauseTest, completeTest, evaluateSignificance } = useABTestStore();
  const status = STATUS_CONFIG[test.status];
  const StatusIcon = status.icon;

  const totalSample = test.variants.reduce((s, v) => s + v.sample_size, 0);
  const significance = useMemo(
    () => evaluateSignificance(test.id, 'open_rate'),
    [test.id, evaluateSignificance]
  );

  // Chart data: compare variants
  const chartData = useMemo(() => {
    const metrics = ['delivery_rate', 'open_rate', 'click_rate', 'conversion_rate'] as const;
    const labels: Record<string, string> = {
      delivery_rate: 'Delivery',
      open_rate: 'Open',
      click_rate: 'Click',
      conversion_rate: 'Conversion',
    };

    return metrics.map((m) => {
      const row: Record<string, any> = { metric: labels[m] };
      test.variants.forEach((v) => {
        row[v.name] = v.metrics[m];
      });
      return row;
    });
  }, [test.variants]);

  // Days elapsed
  const daysElapsed = test.start_date
    ? Math.floor((Date.now() - new Date(test.start_date).getTime()) / 86400000)
    : 0;
  const progressPct = Math.min(100, (daysElapsed / test.duration_days) * 100);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FlaskConical className="h-4 w-4 text-purple-400" />
            <h4 className="text-sm font-semibold text-foreground">{test.name}</h4>
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${status.bg} ${status.color}`}>
              <StatusIcon className="h-3 w-3 inline mr-0.5" />
              {status.label}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{test.hypothesis}</p>
        </div>

        {/* Actions */}
        {test.status === 'draft' && (
          <button
            onClick={() => startTest(test.id)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-colors"
          >
            <Play className="h-3 w-3" /> Start
          </button>
        )}
        {test.status === 'running' && (
          <div className="flex gap-2">
            <button
              onClick={() => pauseTest(test.id)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 text-xs font-medium hover:bg-amber-500/20 transition-colors"
            >
              <Pause className="h-3 w-3" /> Pause
            </button>
            <button
              onClick={() => completeTest(test.id)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 text-xs font-medium hover:bg-blue-500/20 transition-colors"
            >
              <CheckCircle2 className="h-3 w-3" /> Complete
            </button>
          </div>
        )}
      </div>

      {/* Progress & Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div className="text-center">
          <div className="text-lg font-bold text-foreground font-sans">{totalSample}</div>
          <div className="text-[10px] text-muted-foreground uppercase">Sample Size</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-foreground font-sans">{test.traffic_percentage}%</div>
          <div className="text-[10px] text-muted-foreground uppercase">Traffic</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-foreground font-sans">{daysElapsed}/{test.duration_days}d</div>
          <div className="text-[10px] text-muted-foreground uppercase">Duration</div>
        </div>
        <div className="text-center">
          <div className={`text-lg font-bold font-sans ${significance.isSignificant ? 'text-emerald-400' : 'text-amber-400'}`}>
            p={significance.pValue.toFixed(3)}
          </div>
          <div className="text-[10px] text-muted-foreground uppercase">P-Value</div>
        </div>
      </div>

      {/* Progress bar */}
      {test.status === 'running' && (
        <div className="mb-4">
          <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.5 }}
              className="h-full rounded-full bg-gradient-to-r from-purple-500 to-amber-500"
            />
          </div>
        </div>
      )}

      {/* Significance indicator */}
      {totalSample > 0 && (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg mb-4 ${
          significance.isSignificant ? 'bg-emerald-500/10' : 'bg-amber-500/10'
        }`}>
          {significance.isSignificant ? (
            <>
              <Award className="h-4 w-4 text-emerald-400" />
              <span className="text-xs text-emerald-400 font-medium">
                Statistically Significant — Winner:{' '}
                {test.variants.find((v) => v.id === significance.winnerVariantId)?.name}
              </span>
            </>
          ) : (
            <>
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span className="text-xs text-amber-400 font-medium">
                Not yet significant — more data needed
              </span>
            </>
          )}
        </div>
      )}

      {/* Variant comparison chart */}
      {totalSample > 0 && (
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="metric"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <YAxis
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                domain={[0, 1]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.6)' }} />
              {test.variants.map((v, i) => (
                <Bar
                  key={v.id}
                  dataKey={v.name}
                  fill={i === 0 ? '#60a5fa' : '#c084fc'}
                  radius={[3, 3, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function ABTestMonitor() {
  const { tests, initialize, initialized } = useABTestStore();

  if (!initialized) initialize();

  const activeAndRecent = tests.filter((t) =>
    t.status === 'running' || t.status === 'draft' || t.status === 'paused'
  );
  const completedTests = tests.filter((t) => t.status === 'completed' || t.status === 'archived');

  return (
    <div className="space-y-6">
      {/* Active / Draft Tests */}
      {activeAndRecent.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            Active & Draft Tests ({activeAndRecent.length})
          </h3>
          <div className="space-y-4">
            {activeAndRecent.map((test) => (
              <TestCard key={test.id} test={test} />
            ))}
          </div>
        </div>
      )}

      {/* Completed Tests */}
      {completedTests.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-blue-400" />
            Completed Tests ({completedTests.length})
          </h3>
          <div className="space-y-4">
            {completedTests.map((test) => (
              <TestCard key={test.id} test={test} />
            ))}
          </div>
        </div>
      )}

      {tests.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <FlaskConical className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No A/B tests configured yet.</p>
          <p className="text-xs mt-1">Create your first test to start optimizing notifications.</p>
        </div>
      )}
    </div>
  );
}
