/**
 * CONFIT — SOSTAC Strategic Dashboard
 * =====================================
 * Implements the SOSTAC framework as a functional analytics/planning module.
 * Situation | Objectives | Strategy | Tactics | Action | Control
 */

import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3,
  Target,
  Compass,
  Lightbulb,
  Zap,
  Gauge,
  TrendingUp,
  TrendingDown,
  Users,
  ShoppingBag,
  Sparkles,
  ArrowRight,
  Calendar,
  Bell,
  CheckCircle,
  AlertTriangle,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { MainLayout } from '@/components/layout';
import { createTransition } from '@/motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from 'recharts';

// ─── Tab Definition ───
const TABS = [
  { id: 'situation', label: 'Situation', icon: <BarChart3 className="h-4 w-4" />, color: 'text-blue-400' },
  { id: 'objectives', label: 'Objectives', icon: <Target className="h-4 w-4" />, color: 'text-green-400' },
  { id: 'strategy', label: 'Strategy', icon: <Compass className="h-4 w-4" />, color: 'text-violet-400' },
  { id: 'tactics', label: 'Tactics', icon: <Lightbulb className="h-4 w-4" />, color: 'text-amber-400' },
  { id: 'action', label: 'Action', icon: <Zap className="h-4 w-4" />, color: 'text-orange-400' },
  { id: 'control', label: 'Control', icon: <Gauge className="h-4 w-4" />, color: 'text-red-400' },
];

// ─── Mock Data ───
const BROWSING_DATA = [
  { name: 'Dresses', views: 4200, purchases: 380, returns: 45 },
  { name: 'Shoes', views: 3800, purchases: 290, returns: 32 },
  { name: 'Accessories', views: 2900, purchases: 420, returns: 18 },
  { name: 'Tops', views: 3400, purchases: 310, returns: 28 },
  { name: 'Pants', views: 2100, purchases: 190, returns: 22 },
  { name: 'Outerwear', views: 1800, purchases: 140, returns: 15 },
];

const TREND_DATA = [
  { month: 'Jan', conversions: 12.4, returns: 8.2, outfits: 320 },
  { month: 'Feb', conversions: 13.1, returns: 7.8, outfits: 380 },
  { month: 'Mar', conversions: 14.8, returns: 6.5, outfits: 450 },
  { month: 'Apr', conversions: 15.2, returns: 5.9, outfits: 520 },
];

const OCCASION_PIE = [
  { name: 'Casual', value: 35, color: '#60a5fa' },
  { name: 'Work', value: 25, color: '#a78bfa' },
  { name: 'Wedding', value: 15, color: '#f59e0b' },
  { name: 'Party', value: 15, color: '#f472b6' },
  { name: 'Sport', value: 10, color: '#34d399' },
];

const OBJECTIVES_DATA = [
  { id: '1', title: 'Reduce return rate', target: 5, current: 5.9, unit: '%', direction: 'down' as const },
  { id: '2', title: 'Increase outfit completion rate', target: 75, current: 62, unit: '%', direction: 'up' as const },
  { id: '3', title: 'Boost cross-brand purchases', target: 40, current: 28, unit: '%', direction: 'up' as const },
  { id: '4', title: 'Virtual try-on adoption', target: 50, current: 35, unit: '%', direction: 'up' as const },
];

const STRATEGY_ITEMS = [
  { brand: 'Zahra', recommendation: 'Expand evening wear for upcoming wedding season. User data shows 3x increase in wedding-related searches.', confidence: 92 },
  { brand: 'Town Team', recommendation: 'Double down on casual/streetwear. 78% of your buyers are under 30 and browse primarily casual categories.', confidence: 87 },
  { brand: 'Tie House', recommendation: 'Bundle formal shirts with ties — outfit completion rate increases 45% when accessories are suggested.', confidence: 95 },
  { brand: 'Tomato', recommendation: 'Launch a sport-casual crossover collection. Smart casual searches from your audience grew 120% QoQ.', confidence: 81 },
];

const TACTICS_DATA = [
  { id: '1', title: 'Weekend Flash Sale — Shoes', type: 'Promotion', occasion: 'Casual', impact: 'High', status: 'Suggested' },
  { id: '2', title: 'Wedding Season Featured Placement', type: 'Featured', occasion: 'Wedding', impact: 'Very High', status: 'Suggested' },
  { id: '3', title: '"Complete the Look" Push Campaign', type: 'Push Notification', occasion: 'All', impact: 'Medium', status: 'Approved' },
  { id: '4', title: 'Smart Casual Work Outfits Bundle', type: 'Promotion', occasion: 'Work', impact: 'High', status: 'Active' },
];

const ACTIONS_DATA = [
  { id: '1', title: 'Schedule "Wedding Season" campaign', scheduled: '2026-04-10', type: 'Promotion', status: 'pending' },
  { id: '2', title: 'Push notification: New arrivals for Work', scheduled: '2026-04-05', type: 'Push', status: 'scheduled' },
  { id: '3', title: 'Sponsored placement: Zahra Evening Gowns', scheduled: '2026-04-07', type: 'Placement', status: 'active' },
  { id: '4', title: 'Flash sale trigger: Low-stock items', scheduled: 'Auto', type: 'Automated', status: 'active' },
];

const KPI_DATA = [
  { name: 'Outfit-to-Purchase Ratio', value: '62%', change: '+4.2%', trend: 'up' as const },
  { name: 'Return Rate Reduction', value: '5.9%', change: '-1.3%', trend: 'down' as const },
  { name: 'Avg. Style Score', value: '8.4/10', change: '+0.6', trend: 'up' as const },
  { name: 'User Engagement', value: '4.2 min', change: '+0.8 min', trend: 'up' as const },
  { name: 'Conversion Rate', value: '15.2%', change: '+2.1%', trend: 'up' as const },
  { name: 'Cross-Brand Cart', value: '28%', change: '+5%', trend: 'up' as const },
];

// ─── Sub-Components ───

function SituationTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Users className="h-4 w-4 text-blue-400" />
            <span className="text-xs text-muted-foreground">Total Users</span>
          </div>
          <p className="text-2xl font-bold">12,847</p>
          <p className="text-xs text-green-400 mt-1">+18% this month</p>
        </div>
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <ShoppingBag className="h-4 w-4 text-violet-400" />
            <span className="text-xs text-muted-foreground">Total Orders</span>
          </div>
          <p className="text-2xl font-bold">3,420</p>
          <p className="text-xs text-green-400 mt-1">+12% this month</p>
        </div>
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown className="h-4 w-4 text-amber-400" />
            <span className="text-xs text-muted-foreground">Return Rate</span>
          </div>
          <p className="text-2xl font-bold">5.9%</p>
          <p className="text-xs text-green-400 mt-1">-1.3% vs last month</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card rounded-xl p-5">
          <h3 className="text-sm font-semibold mb-4">Browsing Patterns by Category</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={BROWSING_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
              <YAxis tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
              <Tooltip contentStyle={{ background: 'hsl(220 25% 10%)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: 12 }} />
              <Bar dataKey="views" fill="#60a5fa" radius={[4, 4, 0, 0]} name="Views" />
              <Bar dataKey="purchases" fill="#a78bfa" radius={[4, 4, 0, 0]} name="Purchases" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card rounded-xl p-5">
          <h3 className="text-sm font-semibold mb-4">Popular Occasions</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={OCCASION_PIE} cx="50%" cy="50%" outerRadius={80} innerRadius={50} paddingAngle={4} dataKey="value">
                {OCCASION_PIE.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: 'hsl(220 25% 10%)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-3 justify-center mt-2">
            {OCCASION_PIE.map(item => (
              <div key={item.name} className="flex items-center gap-1.5 text-xs">
                <div className="h-2 w-2 rounded-full" style={{ background: item.color }} />
                {item.name} ({item.value}%)
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ObjectivesTab() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">Set measurable goals and track progress in real time.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {OBJECTIVES_DATA.map(obj => {
          const progress = obj.direction === 'up'
            ? Math.min(100, (obj.current / obj.target) * 100)
            : Math.min(100, obj.current <= obj.target ? 100 : ((2 * obj.target - obj.current) / obj.target) * 100);
          const isOnTrack = obj.direction === 'up' ? obj.current >= obj.target * 0.7 : obj.current <= obj.target * 1.3;

          return (
            <div key={obj.id} className="glass-card rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-medium text-sm">{obj.title}</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Target: {obj.target}{obj.unit} • Current: {obj.current}{obj.unit}
                  </p>
                </div>
                {isOnTrack ? (
                  <Badge variant="outline" className="text-[10px] bg-green-500/10 text-green-400 border-green-500/20">On Track</Badge>
                ) : (
                  <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-400 border-amber-500/20">Needs Attention</Badge>
                )}
              </div>
              <Progress value={progress} className="h-2" />
              <p className="text-xs text-muted-foreground mt-2">{Math.round(progress)}% of target</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StrategyTab() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">AI-driven positioning recommendations based on user behavior data.</p>
      <div className="space-y-4">
        {STRATEGY_ITEMS.map((item, i) => (
          <motion.div
            key={item.brand}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass-card rounded-xl p-5"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-violet-400" />
                <h4 className="font-semibold text-sm">{item.brand}</h4>
              </div>
              <Badge variant="outline" className="text-[10px] bg-violet-500/10 text-violet-400 border-violet-500/20">
                {item.confidence}% confidence
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{item.recommendation}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function TacticsTab() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">Actionable campaign suggestions: promotions, placements, and targeting.</p>
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/30 border-b border-border">
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Campaign</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Occasion</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Impact</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
            </tr>
          </thead>
          <tbody>
            {TACTICS_DATA.map(t => (
              <tr key={t.id} className="border-b border-border/50 hover:bg-muted/20">
                <td className="px-4 py-3 font-medium">{t.title}</td>
                <td className="px-4 py-3 text-muted-foreground">{t.type}</td>
                <td className="px-4 py-3">{t.occasion}</td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className={cn('text-[10px]',
                    t.impact === 'Very High' ? 'text-green-400 border-green-500/20' :
                    t.impact === 'High' ? 'text-blue-400 border-blue-500/20' :
                    'text-muted-foreground'
                  )}>{t.impact}</Badge>
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className={cn('text-[10px]',
                    t.status === 'Active' ? 'bg-green-500/10 text-green-400' :
                    t.status === 'Approved' ? 'bg-blue-500/10 text-blue-400' :
                    'bg-muted text-muted-foreground'
                  )}>{t.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ActionTab() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">Schedule and manage promotional triggers, push notifications, and placements.</p>
      <div className="space-y-3">
        {ACTIONS_DATA.map((action) => (
          <div key={action.id} className="glass-card rounded-xl p-4 flex items-center gap-4">
            <div className={cn('h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0',
              action.status === 'active' ? 'bg-green-500/10' :
              action.status === 'scheduled' ? 'bg-blue-500/10' :
              'bg-muted'
            )}>
              {action.type === 'Push' ? <Bell className="h-4 w-4" /> :
               action.type === 'Promotion' ? <Zap className="h-4 w-4" /> :
               action.type === 'Placement' ? <Eye className="h-4 w-4" /> :
               <Zap className="h-4 w-4" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm">{action.title}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                <Calendar className="h-3 w-3" />
                <span>{action.scheduled}</span>
                <span>•</span>
                <span>{action.type}</span>
              </div>
            </div>
            <Badge variant="outline" className={cn('text-[10px] capitalize',
              action.status === 'active' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
              action.status === 'scheduled' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
              'bg-amber-500/10 text-amber-400 border-amber-500/20'
            )}>{action.status}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

function ControlTab() {
  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {KPI_DATA.map(kpi => (
          <div key={kpi.name} className="glass-card rounded-xl p-4">
            <p className="text-xs text-muted-foreground mb-1">{kpi.name}</p>
            <p className="text-xl font-bold">{kpi.value}</p>
            <p className={cn('text-xs mt-1 flex items-center gap-1',
              kpi.trend === 'up' ? 'text-green-400' : 'text-green-400'
            )}>
              {kpi.trend === 'up' ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {kpi.change}
            </p>
          </div>
        ))}
      </div>

      {/* Conversion Trend Chart */}
      <div className="glass-card rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-4">Conversion & Return Trends</h3>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={TREND_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
            <YAxis tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
            <Tooltip contentStyle={{ background: 'hsl(220 25% 10%)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: 12 }} />
            <Area type="monotone" dataKey="conversions" stroke="#a78bfa" fill="rgba(167,139,250,0.15)" name="Conversion %" />
            <Area type="monotone" dataKey="returns" stroke="#f87171" fill="rgba(248,113,113,0.1)" name="Return %" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Outfit Completions */}
      <div className="glass-card rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-4">Outfit Completion Trend</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={TREND_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
            <YAxis tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
            <Tooltip contentStyle={{ background: 'hsl(220 25% 10%)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: 12 }} />
            <Line type="monotone" dataKey="outfits" stroke="#D4AF37" strokeWidth={2} dot={{ fill: '#D4AF37' }} name="Outfits Completed" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Main Component ───

const TAB_COMPONENTS: Record<string, React.FC> = {
  situation: SituationTab,
  objectives: ObjectivesTab,
  strategy: StrategyTab,
  tactics: TacticsTab,
  action: ActionTab,
  control: ControlTab,
};

export default function SOSTACDashboard() {
  const [activeTab, setActiveTab] = useState('situation');
  const ActiveComponent = TAB_COMPONENTS[activeTab] || SituationTab;

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
              <Gauge className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
                SOSTAC Analytics
              </h1>
              <p className="text-sm text-muted-foreground">Strategic planning & performance control</p>
            </div>
          </div>
        </div>

        {/* Tab Bar */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-muted/30 border border-border mb-8 overflow-x-auto no-scrollbar">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap',
                activeTab === tab.id
                  ? 'bg-card shadow-sm text-foreground border border-border'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
              )}
            >
              <span className={cn(activeTab === tab.id && tab.color)}>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Active Tab */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ duration: 0.2 })}
        >
          <ActiveComponent />
        </motion.div>
      </div>
    </MainLayout>
  );
}
