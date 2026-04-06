/**
 * CONFIT — SOSTAC Marketing Planning Model Integration
 * =====================================================
 * SOSTAC framework for marketing planning and analytics:
 * - Situation: Current market position analysis
 * - Objectives: SMART goals definition
 * - Strategy: High-level approach to achieve objectives
 * - Tactics: Detailed action plans and tools
 * - Action: Implementation timeline and responsibilities
 * - Control: KPIs, monitoring, and measurement
 */

import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Target,
    TrendingUp,
    Lightbulb,
    ListTodo,
    PlayCircle,
    BarChart3,
    ChevronRight,
    ChevronDown,
    CheckCircle2,
    AlertCircle,
    Clock,
    DollarSign,
    Users,
    ShoppingBag,
    Globe,
    Zap,
    Edit3,
    Save,
    X,
    Plus,
    Trash2,
    Calendar,
    Percent,
    ArrowUpRight,
    ArrowDownRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

// Types
export interface KPI {
    id: string;
    name: string;
    target: number;
    current: number;
    unit: string;
    trend: 'up' | 'down' | 'stable';
}

export interface Objective {
    id: string;
    title: string;
    description: string;
    targetDate: string;
    status: 'on_track' | 'at_risk' | 'achieved' | 'behind';
    kpis: KPI[];
}

export interface Tactic {
    id: string;
    title: string;
    channel: string;
    budget: number;
    spent: number;
    status: 'planned' | 'active' | 'completed' | 'paused';
    startDate: string;
    endDate: string;
}

export interface ActionItem {
    id: string;
    title: string;
    owner: string;
    dueDate: string;
    status: 'pending' | 'in_progress' | 'completed' | 'blocked';
    priority: 'high' | 'medium' | 'low';
}

export interface SOSTACPlan {
    situation: {
        swot: { strengths: string[]; weaknesses: string[]; opportunities: string[]; threats: string[] };
        marketPosition: string;
        competitors: string[];
    };
    objectives: Objective[];
    strategy: {
        targetAudience: string;
        valueProposition: string;
        positioning: string;
        keyMessages: string[];
    };
    tactics: Tactic[];
    actions: ActionItem[];
    control: {
        reviewFrequency: 'weekly' | 'biweekly' | 'monthly';
        reportingTools: string[];
        successCriteria: string[];
    };
}

// Default mock data
const DEFAULT_SOSTAC: SOSTACPlan = {
    situation: {
        swot: {
            strengths: ['Strong brand identity', 'Quality products', 'Loyal customer base'],
            weaknesses: ['Limited online presence', 'Higher price point', 'Small marketing budget'],
            opportunities: ['Growing athleisure market', 'E-commerce expansion', 'Sustainability trend'],
            threats: ['Fast fashion competition', 'Economic uncertainty', 'Supply chain disruptions'],
        },
        marketPosition: 'Premium athletic wear brand positioned in the upper-mid segment',
        competitors: ['Lululemon', 'Nike', 'Under Armour', 'Alo Yoga'],
    },
    objectives: [
        {
            id: 'obj-1',
            title: 'Increase Revenue by 25%',
            description: 'Achieve $500K quarterly revenue through organic growth and paid acquisition',
            targetDate: '2026-06-30',
            status: 'on_track',
            kpis: [
                { id: 'kpi-1', name: 'Quarterly Revenue', target: 500000, current: 284750, unit: '$', trend: 'up' },
                { id: 'kpi-2', name: 'Conversion Rate', target: 10, current: 7.5, unit: '%', trend: 'up' },
            ],
        },
        {
            id: 'obj-2',
            title: 'Grow Customer Base',
            description: 'Acquire 5,000 new customers through multi-channel campaigns',
            targetDate: '2026-09-30',
            status: 'at_risk',
            kpis: [
                { id: 'kpi-3', name: 'New Customers', target: 5000, current: 2100, unit: '', trend: 'up' },
                { id: 'kpi-4', name: 'CAC', target: 25, current: 32, unit: '$', trend: 'down' },
            ],
        },
    ],
    strategy: {
        targetAudience: 'Health-conscious millennials and Gen Z (25-40) with disposable income',
        valueProposition: 'Premium sustainable athletic wear that performs as good as it looks',
        positioning: 'The confident choice for those who value quality over fast fashion',
        keyMessages: ['Sustainable by design', 'Performance meets style', 'Wear your confidence'],
    },
    tactics: [
        { id: 'tac-1', title: 'Instagram Influencer Campaign', channel: 'Social Media', budget: 5000, spent: 2400, status: 'active', startDate: '2026-03-01', endDate: '2026-05-31' },
        { id: 'tac-2', title: 'Email Marketing Automation', channel: 'Email', budget: 500, spent: 200, status: 'active', startDate: '2026-02-01', endDate: '2026-12-31' },
        { id: 'tac-3', title: 'Google Shopping Ads', channel: 'Paid Search', budget: 3000, spent: 0, status: 'planned', startDate: '2026-04-01', endDate: '2026-06-30' },
    ],
    actions: [
        { id: 'act-1', title: 'Launch Spring Collection', owner: 'Marketing Team', dueDate: '2026-04-15', status: 'in_progress', priority: 'high' },
        { id: 'act-2', title: 'Set up Google Analytics 4', owner: 'Tech Team', dueDate: '2026-04-01', status: 'completed', priority: 'medium' },
        { id: 'act-3', title: 'Create Lookbook PDF', owner: 'Design Team', dueDate: '2026-04-20', status: 'pending', priority: 'low' },
    ],
    control: {
        reviewFrequency: 'biweekly',
        reportingTools: ['Google Analytics', 'Shopify Analytics', 'Custom Dashboard'],
        successCriteria: ['Revenue growth >20%', 'CAC <$30', 'NPS >50'],
    },
};

// Component for each SOSTAC section
function SituationSection({ 
    data, 
    onUpdate, 
    isExpanded, 
    onToggle 
}: { 
    data: SOSTACPlan['situation']; 
    onUpdate: (data: SOSTACPlan['situation']) => void;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    const [editing, setEditing] = useState(false);
    const [localData, setLocalData] = useState(data);

    const handleSave = () => {
        onUpdate(localData);
        setEditing(false);
    };

    return (
        <Card className="overflow-hidden">
            <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={onToggle}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                            <Globe className="h-5 w-5 text-blue-500" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Situation Analysis</CardTitle>
                            <CardDescription>Where are we now?</CardDescription>
                        </div>
                    </div>
                    {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                </div>
            </CardHeader>
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <CardContent className="pt-4 border-t">
                            {editing ? (
                                <div className="space-y-4">
                                    <div>
                                        <label className="text-sm font-medium">Market Position</label>
                                        <Textarea 
                                            value={localData.marketPosition} 
                                            onChange={e => setLocalData({ ...localData, marketPosition: e.target.value })}
                                            className="mt-1"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-sm font-medium">Strengths</label>
                                            <Textarea 
                                                value={localData.swot.strengths.join('\n')} 
                                                onChange={e => setLocalData({ 
                                                    ...localData, 
                                                    swot: { ...localData.swot, strengths: e.target.value.split('\n').filter(Boolean) }
                                                })}
                                                className="mt-1"
                                                placeholder="One per line"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-sm font-medium">Weaknesses</label>
                                            <Textarea 
                                                value={localData.swot.weaknesses.join('\n')} 
                                                onChange={e => setLocalData({ 
                                                    ...localData, 
                                                    swot: { ...localData.swot, weaknesses: e.target.value.split('\n').filter(Boolean) }
                                                })}
                                                className="mt-1"
                                                placeholder="One per line"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-sm font-medium">Opportunities</label>
                                            <Textarea 
                                                value={localData.swot.opportunities.join('\n')} 
                                                onChange={e => setLocalData({ 
                                                    ...localData, 
                                                    swot: { ...localData.swot, opportunities: e.target.value.split('\n').filter(Boolean) }
                                                })}
                                                className="mt-1"
                                                placeholder="One per line"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-sm font-medium">Threats</label>
                                            <Textarea 
                                                value={localData.swot.threats.join('\n')} 
                                                onChange={e => setLocalData({ 
                                                    ...localData, 
                                                    swot: { ...localData.swot, threats: e.target.value.split('\n').filter(Boolean) }
                                                })}
                                                className="mt-1"
                                                placeholder="One per line"
                                            />
                                        </div>
                                    </div>
                                    <div className="flex justify-end gap-2">
                                        <Button variant="outline" size="sm" onClick={() => setEditing(false)}><X className="h-4 w-4 mr-1" />Cancel</Button>
                                        <Button size="sm" onClick={handleSave}><Save className="h-4 w-4 mr-1" />Save</Button>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <div>
                                        <p className="text-sm text-muted-foreground mb-2">Market Position</p>
                                        <p className="text-sm">{data.marketPosition}</p>
                                    </div>
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                        <div className="p-3 bg-green-500/5 rounded-lg border border-green-500/20">
                                            <p className="text-xs font-medium text-green-600 mb-2">Strengths</p>
                                            <ul className="text-xs space-y-1">
                                                {data.swot.strengths.map((s, i) => <li key={i}>• {s}</li>)}
                                            </ul>
                                        </div>
                                        <div className="p-3 bg-red-500/5 rounded-lg border border-red-500/20">
                                            <p className="text-xs font-medium text-red-600 mb-2">Weaknesses</p>
                                            <ul className="text-xs space-y-1">
                                                {data.swot.weaknesses.map((w, i) => <li key={i}>• {w}</li>)}
                                            </ul>
                                        </div>
                                        <div className="p-3 bg-blue-500/5 rounded-lg border border-blue-500/20">
                                            <p className="text-xs font-medium text-blue-600 mb-2">Opportunities</p>
                                            <ul className="text-xs space-y-1">
                                                {data.swot.opportunities.map((o, i) => <li key={i}>• {o}</li>)}
                                            </ul>
                                        </div>
                                        <div className="p-3 bg-amber-500/5 rounded-lg border border-amber-500/20">
                                            <p className="text-xs font-medium text-amber-600 mb-2">Threats</p>
                                            <ul className="text-xs space-y-1">
                                                {data.swot.threats.map((t, i) => <li key={i}>• {t}</li>)}
                                            </ul>
                                        </div>
                                    </div>
                                    <div className="flex justify-end">
                                        <Button variant="ghost" size="sm" onClick={() => setEditing(true)}><Edit3 className="h-4 w-4 mr-1" />Edit</Button>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}

function ObjectivesSection({ 
    data, 
    onUpdate, 
    isExpanded, 
    onToggle 
}: { 
    data: Objective[]; 
    onUpdate: (data: Objective[]) => void;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    const [editingId, setEditingId] = useState<string | null>(null);

    const getStatusColor = (status: Objective['status']) => {
        switch (status) {
            case 'achieved': return 'bg-green-500/10 text-green-600 border-green-500/20';
            case 'on_track': return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
            case 'at_risk': return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
            case 'behind': return 'bg-red-500/10 text-red-600 border-red-500/20';
        }
    };

    return (
        <Card className="overflow-hidden">
            <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={onToggle}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                            <Target className="h-5 w-5 text-green-500" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Objectives</CardTitle>
                            <CardDescription>Where do we want to be? (SMART Goals)</CardDescription>
                        </div>
                    </div>
                    {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                </div>
            </CardHeader>
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <CardContent className="pt-4 border-t space-y-4">
                            {data.map((obj) => (
                                <div key={obj.id} className="p-4 bg-muted/30 rounded-lg space-y-3">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <h4 className="font-medium">{obj.title}</h4>
                                            <p className="text-sm text-muted-foreground">{obj.description}</p>
                                        </div>
                                        <Badge className={cn('border', getStatusColor(obj.status))}>
                                            {obj.status.replace('_', ' ')}
                                        </Badge>
                                    </div>
                                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                                        {obj.kpis.map((kpi) => {
                                            const progress = (kpi.current / kpi.target) * 100;
                                            return (
                                                <div key={kpi.id} className="p-3 bg-background rounded-lg border">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <span className="text-xs text-muted-foreground">{kpi.name}</span>
                                                        {kpi.trend === 'up' ? (
                                                            <ArrowUpRight className="h-3 w-3 text-green-500" />
                                                        ) : kpi.trend === 'down' ? (
                                                            <ArrowDownRight className="h-3 w-3 text-red-500" />
                                                        ) : null}
                                                    </div>
                                                    <div className="flex items-baseline gap-1">
                                                        <span className="text-lg font-bold">
                                                            {kpi.unit === '$' ? '$' : ''}{kpi.current.toLocaleString()}
                                                        </span>
                                                        <span className="text-xs text-muted-foreground">/ {kpi.unit === '$' ? '$' : ''}{kpi.target.toLocaleString()}</span>
                                                    </div>
                                                    <Progress value={Math.min(progress, 100)} className="h-1.5 mt-2" />
                                                </div>
                                            );
                                        })}
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <Calendar className="h-3 w-3" />
                                        Target: {new Date(obj.targetDate).toLocaleDateString()}
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}

function StrategySection({ 
    data, 
    onUpdate, 
    isExpanded, 
    onToggle 
}: { 
    data: SOSTACPlan['strategy']; 
    onUpdate: (data: SOSTACPlan['strategy']) => void;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    const [editing, setEditing] = useState(false);
    const [localData, setLocalData] = useState(data);

    return (
        <Card className="overflow-hidden">
            <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={onToggle}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                            <Lightbulb className="h-5 w-5 text-purple-500" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Strategy</CardTitle>
                            <CardDescription>How do we get there?</CardDescription>
                        </div>
                    </div>
                    {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                </div>
            </CardHeader>
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <CardContent className="pt-4 border-t space-y-4">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                                <div className="p-4 bg-muted/30 rounded-lg">
                                    <p className="text-xs font-medium text-muted-foreground mb-2">Target Audience</p>
                                    <p className="text-sm">{data.targetAudience}</p>
                                </div>
                                <div className="p-4 bg-muted/30 rounded-lg">
                                    <p className="text-xs font-medium text-muted-foreground mb-2">Value Proposition</p>
                                    <p className="text-sm">{data.valueProposition}</p>
                                </div>
                                <div className="p-4 bg-muted/30 rounded-lg">
                                    <p className="text-xs font-medium text-muted-foreground mb-2">Positioning</p>
                                    <p className="text-sm">{data.positioning}</p>
                                </div>
                            </div>
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <p className="text-xs font-medium text-muted-foreground mb-2">Key Messages</p>
                                <div className="flex flex-wrap gap-2">
                                    {data.keyMessages.map((msg, i) => (
                                        <Badge key={i} variant="secondary">{msg}</Badge>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}

function TacticsSection({ 
    data, 
    onUpdate, 
    isExpanded, 
    onToggle 
}: { 
    data: Tactic[]; 
    onUpdate: (data: Tactic[]) => void;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    const getStatusColor = (status: Tactic['status']) => {
        switch (status) {
            case 'completed': return 'bg-green-500/10 text-green-600';
            case 'active': return 'bg-blue-500/10 text-blue-600';
            case 'planned': return 'bg-muted text-muted-foreground';
            case 'paused': return 'bg-amber-500/10 text-amber-600';
        }
    };

    const getChannelIcon = (channel: string) => {
        if (channel.includes('Social')) return Users;
        if (channel.includes('Email')) return Zap;
        if (channel.includes('Search')) return Globe;
        return DollarSign;
    };

    return (
        <Card className="overflow-hidden">
            <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={onToggle}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                            <ListTodo className="h-5 w-5 text-amber-500" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Tactics</CardTitle>
                            <CardDescription>How exactly do we get there?</CardDescription>
                        </div>
                    </div>
                    {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                </div>
            </CardHeader>
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <CardContent className="pt-4 border-t">
                            <div className="space-y-3">
                                {data.map((tactic) => {
                                    const ChannelIcon = getChannelIcon(tactic.channel);
                                    const budgetProgress = (tactic.spent / tactic.budget) * 100;
                                    return (
                                        <div key={tactic.id} className="p-4 bg-muted/30 rounded-lg">
                                            <div className="flex items-start justify-between mb-3">
                                                <div className="flex items-center gap-3">
                                                    <div className="h-8 w-8 rounded bg-muted flex items-center justify-center">
                                                        <ChannelIcon className="h-4 w-4 text-muted-foreground" />
                                                    </div>
                                                    <div>
                                                        <p className="font-medium text-sm">{tactic.title}</p>
                                                        <p className="text-xs text-muted-foreground">{tactic.channel}</p>
                                                    </div>
                                                </div>
                                                <Badge className={getStatusColor(tactic.status)}>{tactic.status}</Badge>
                                            </div>
                                            <div className="flex items-center gap-4 text-xs">
                                                <div className="flex items-center gap-1">
                                                    <DollarSign className="h-3 w-3 text-muted-foreground" />
                                                    <span>${tactic.spent.toLocaleString()} / ${tactic.budget.toLocaleString()}</span>
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <Calendar className="h-3 w-3 text-muted-foreground" />
                                                    <span>{new Date(tactic.startDate).toLocaleDateString()} - {new Date(tactic.endDate).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                            <Progress value={budgetProgress} className="h-1.5 mt-2" />
                                        </div>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}

function ActionsSection({ 
    data, 
    onUpdate, 
    isExpanded, 
    onToggle 
}: { 
    data: ActionItem[]; 
    onUpdate: (data: ActionItem[]) => void;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    const getPriorityColor = (priority: ActionItem['priority']) => {
        switch (priority) {
            case 'high': return 'bg-red-500/10 text-red-600';
            case 'medium': return 'bg-amber-500/10 text-amber-600';
            case 'low': return 'bg-green-500/10 text-green-600';
        }
    };

    const getStatusIcon = (status: ActionItem['status']) => {
        switch (status) {
            case 'completed': return <CheckCircle2 className="h-4 w-4 text-green-500" />;
            case 'in_progress': return <Clock className="h-4 w-4 text-blue-500" />;
            case 'blocked': return <AlertCircle className="h-4 w-4 text-red-500" />;
            default: return <Clock className="h-4 w-4 text-muted-foreground" />;
        }
    };

    return (
        <Card className="overflow-hidden">
            <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={onToggle}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                            <PlayCircle className="h-5 w-5 text-cyan-500" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Action</CardTitle>
                            <CardDescription>What is our plan?</CardDescription>
                        </div>
                    </div>
                    {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                </div>
            </CardHeader>
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <CardContent className="pt-4 border-t">
                            <div className="space-y-2">
                                {data.map((action) => (
                                    <div key={action.id} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                                        <div className="flex items-center gap-3">
                                            {getStatusIcon(action.status)}
                                            <div>
                                                <p className="text-sm font-medium">{action.title}</p>
                                                <p className="text-xs text-muted-foreground">{action.owner} • Due {new Date(action.dueDate).toLocaleDateString()}</p>
                                            </div>
                                        </div>
                                        <Badge className={getPriorityColor(action.priority)}>{action.priority}</Badge>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}

function ControlSection({ 
    data, 
    onUpdate, 
    isExpanded, 
    onToggle 
}: { 
    data: SOSTACPlan['control']; 
    onUpdate: (data: SOSTACPlan['control']) => void;
    isExpanded: boolean;
    onToggle: () => void;
}) {
    return (
        <Card className="overflow-hidden">
            <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={onToggle}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-pink-500/10 flex items-center justify-center">
                            <BarChart3 className="h-5 w-5 text-pink-500" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Control</CardTitle>
                            <CardDescription>Did we get there?</CardDescription>
                        </div>
                    </div>
                    {isExpanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
                </div>
            </CardHeader>
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <CardContent className="pt-4 border-t space-y-4">
                            <div className="flex items-center gap-2">
                                <Clock className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm">Review Frequency: </span>
                                <Badge variant="secondary">{data.reviewFrequency}</Badge>
                            </div>
                            <div>
                                <p className="text-xs font-medium text-muted-foreground mb-2">Reporting Tools</p>
                                <div className="flex flex-wrap gap-2">
                                    {data.reportingTools.map((tool, i) => (
                                        <Badge key={i} variant="outline">{tool}</Badge>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <p className="text-xs font-medium text-muted-foreground mb-2">Success Criteria</p>
                                <ul className="text-sm space-y-1">
                                    {data.successCriteria.map((criteria, i) => (
                                        <li key={i} className="flex items-center gap-2">
                                            <CheckCircle2 className="h-3 w-3 text-green-500" />
                                            {criteria}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </CardContent>
                    </motion.div>
                )}
            </AnimatePresence>
        </Card>
    );
}

// Main SOSTAC Panel Component
export function SOSTACPanel({ 
    initialData = DEFAULT_SOSTAC,
    onSave 
}: { 
    initialData?: SOSTACPlan;
    onSave?: (plan: SOSTACPlan) => void;
}) {
    const [plan, setPlan] = useState<SOSTACPlan>(initialData);
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['situation', 'objectives']));

    const toggleSection = useCallback((section: string) => {
        setExpandedSections(prev => {
            const next = new Set(prev);
            if (next.has(section)) {
                next.delete(section);
            } else {
                next.add(section);
            }
            return next;
        });
    }, []);

    const updateSection = useCallback(<K extends keyof SOSTACPlan>(section: K, data: SOSTACPlan[K]) => {
        setPlan(prev => ({ ...prev, [section]: data }));
        onSave?.({ ...plan, [section]: data });
    }, [plan, onSave]);

    // Calculate overall progress
    const overallProgress = useMemo(() => {
        const objectives = plan.objectives;
        if (objectives.length === 0) return 0;
        const totalKpis = objectives.reduce((sum, obj) => sum + obj.kpis.length, 0);
        if (totalKpis === 0) return 0;
        const avgProgress = objectives.reduce((sum, obj) => {
            const objProgress = obj.kpis.reduce((kpiSum, kpi) => kpiSum + (kpi.current / kpi.target) * 100, 0) / obj.kpis.length;
            return sum + objProgress;
        }, 0) / objectives.length;
        return Math.min(avgProgress, 100);
    }, [plan.objectives]);

    return (
        <div className="space-y-4">
            {/* Overview Header */}
            <div className="bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-green-500/10 rounded-xl p-6 border">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h3 className="text-xl font-semibold">SOSTAC Marketing Plan</h3>
                        <p className="text-sm text-muted-foreground">Strategic planning framework for your brand</p>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-muted-foreground">Overall Progress</p>
                        <p className="text-2xl font-bold">{overallProgress.toFixed(1)}%</p>
                    </div>
                </div>
                <Progress value={overallProgress} className="h-2" />
            </div>

            {/* SOSTAC Sections */}
            <div className="grid gap-4">
                <SituationSection
                    data={plan.situation}
                    onUpdate={(data) => updateSection('situation', data)}
                    isExpanded={expandedSections.has('situation')}
                    onToggle={() => toggleSection('situation')}
                />
                <ObjectivesSection
                    data={plan.objectives}
                    onUpdate={(data) => updateSection('objectives', data)}
                    isExpanded={expandedSections.has('objectives')}
                    onToggle={() => toggleSection('objectives')}
                />
                <StrategySection
                    data={plan.strategy}
                    onUpdate={(data) => updateSection('strategy', data)}
                    isExpanded={expandedSections.has('strategy')}
                    onToggle={() => toggleSection('strategy')}
                />
                <TacticsSection
                    data={plan.tactics}
                    onUpdate={(data) => updateSection('tactics', data)}
                    isExpanded={expandedSections.has('tactics')}
                    onToggle={() => toggleSection('tactics')}
                />
                <ActionsSection
                    data={plan.actions}
                    onUpdate={(data) => updateSection('actions', data)}
                    isExpanded={expandedSections.has('actions')}
                    onToggle={() => toggleSection('actions')}
                />
                <ControlSection
                    data={plan.control}
                    onUpdate={(data) => updateSection('control', data)}
                    isExpanded={expandedSections.has('control')}
                    onToggle={() => toggleSection('control')}
                />
            </div>
        </div>
    );
}

export default SOSTACPanel;
