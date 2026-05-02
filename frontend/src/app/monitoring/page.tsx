/**
 * System Monitoring Dashboard
 * Live observability page connecting to backend health, metrics, and status endpoints.
 * Admin-only access via RBAC.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    Activity, Server, Database, Globe, Shield, Clock,
    AlertTriangle, CheckCircle, XCircle, RefreshCw,
    HardDrive, Cpu, TrendingUp, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/context/AuthContext';
import { AppRole, useRBAC } from '@/hooks/useRBAC';
import { cn } from '@/lib/utils';
import { fetchHealth, fetchReadiness, fetchDeepHealth } from '@/services/monitoring.service';

interface HealthData {
    status: 'ok' | 'healthy' | 'degraded' | 'unhealthy';
    timestamp: string;
    version?: string;
    service?: string;
    checks?: Record<string, any>;
    external_checks?: Record<string, any>;
}

const STATUS_CONFIG: Record<string, { color: string; icon: any; label: string }> = {
    ok: { color: 'bg-green-500', icon: CheckCircle, label: 'Healthy' },
    healthy: { color: 'bg-green-500', icon: CheckCircle, label: 'Healthy' },
    degraded: { color: 'bg-yellow-500', icon: AlertTriangle, label: 'Degraded' },
    unhealthy: { color: 'bg-red-500', icon: XCircle, label: 'Unhealthy' },
    unknown: { color: 'bg-gray-500', icon: Activity, label: 'Unknown' },
};

const GRAFANA_URL = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3001';

function StatusBadge({ status }: { status: string }) {
    const config = STATUS_CONFIG[status] || STATUS_CONFIG.unknown;
    const Icon = config.icon;
    return (
        <Badge className={cn('gap-1 text-white', config.color)}>
            <Icon className="h-3 w-3" />
            {config.label}
        </Badge>
    );
}

function CheckCard({ name, data }: { name: string; data: any }) {
    const isHealthy = data?.status === 'healthy' || data?.status === 'ok';
    const isNotConfigured = data?.status === 'not_configured';
    return (
        <Card className={cn(
            'border-l-4 transition-all',
            isHealthy ? 'border-l-green-500' : isNotConfigured ? 'border-l-gray-400' : 'border-l-red-500'
        )}>
            <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        {isHealthy ? <CheckCircle className="h-4 w-4 text-green-500" />
                            : isNotConfigured ? <Activity className="h-4 w-4 text-gray-400" />
                                : <XCircle className="h-4 w-4 text-red-500" />}
                        <span className="font-medium capitalize">{name}</span>
                    </div>
                    <StatusBadge status={data?.status || 'unknown'} />
                </div>
                {data?.latency_ms !== undefined && (
                    <p className="text-xs text-muted-foreground">Latency: {data.latency_ms}ms</p>
                )}
                {data?.status_code !== undefined && (
                    <p className="text-xs text-muted-foreground">HTTP {data.status_code}</p>
                )}
                {data?.error && (
                    <p className="text-xs text-red-600 mt-1">{data.error}</p>
                )}
            </CardContent>
        </Card>
    );
}

export default function MonitoringPage() {
    const router = useRouter();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const rbac = useRBAC();
    const canAccess = rbac.hasRole(AppRole.ADMIN);

    const [basicHealth, setBasicHealth] = useState<HealthData | null>(null);
    const [readiness, setReadiness] = useState<HealthData | null>(null);
    const [deepHealth, setDeepHealth] = useState<HealthData | null>(null);
    const [loading, setLoading] = useState(true);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [error, setError] = useState<string | null>(null);

    const loadAll = async () => {
        setLoading(true);
        setError(null);
        try {
            const [b, r, d] = await Promise.allSettled([
                fetchHealth(),
                fetchReadiness(),
                fetchDeepHealth(),
            ]);
            if (b.status === 'fulfilled') setBasicHealth(b.value);
            if (r.status === 'fulfilled') setReadiness(r.value);
            if (d.status === 'fulfilled') setDeepHealth(d.value);
            setLastUpdated(new Date());
        } catch (err) {
            setError('Failed to load health data. Is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login?redirect=/monitoring');
            return;
        }
        if (!authLoading && isAuthenticated && !canAccess) {
            router.replace('/?error=unauthorized');
            return;
        }
        if (!authLoading && isAuthenticated && canAccess) {
            loadAll();
            const interval = setInterval(loadAll, 30000);
            return () => clearInterval(interval);
        }
    }, [authLoading, isAuthenticated, canAccess, router]);

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin h-8 w-8 border-4 border-red-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (!isAuthenticated || !canAccess) {
        return null;
    }

    const overallStatus = deepHealth?.status || readiness?.status || basicHealth?.status || 'unknown';

    return (
        <MainLayout>
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                                <Activity className="h-6 w-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-display font-semibold">System Monitoring</h1>
                                <p className="text-muted-foreground">Live observability dashboard</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <StatusBadge status={overallStatus} />
                            <Button variant="outline" size="sm" onClick={loadAll} disabled={loading}>
                                <RefreshCw className={cn('h-4 w-4 mr-2', loading && 'animate-spin')} />
                                Refresh
                            </Button>
                        </div>
                    </div>
                    {lastUpdated && (
                        <p className="text-xs text-muted-foreground mt-2">
                            Last updated: {lastUpdated.toLocaleTimeString()}
                        </p>
                    )}
                </motion.div>

                {error && (
                    <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-700 flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5" />
                        {error}
                    </div>
                )}

                {/* Top Stats */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
                >
                    <Card>
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-2">
                                <Server className="h-5 w-5 text-blue-500" />
                                {overallStatus === 'healthy' ? (
                                    <ArrowUpRight className="h-4 w-4 text-green-500" />
                                ) : (
                                    <ArrowDownRight className="h-4 w-4 text-red-500" />
                                )}
                            </div>
                            <div className="text-2xl font-bold capitalize">{overallStatus}</div>
                            <div className="text-sm text-muted-foreground">Overall Status</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-2">
                                <Database className="h-5 w-5 text-purple-500" />
                                <StatusBadge status={readiness?.checks?.database?.status || 'unknown'} />
                            </div>
                            <div className="text-2xl font-bold">{readiness?.checks?.database?.status === 'healthy' ? 'Connected' : 'Issue'}</div>
                            <div className="text-sm text-muted-foreground">Database</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-2">
                                <HardDrive className="h-5 w-5 text-amber-500" />
                                <StatusBadge status={readiness?.checks?.redis?.status || 'unknown'} />
                            </div>
                            <div className="text-2xl font-bold">{readiness?.checks?.redis?.status === 'healthy' ? 'Connected' : 'Issue'}</div>
                            <div className="text-sm text-muted-foreground">Redis Cache</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-2">
                                <Globe className="h-5 w-5 text-green-500" />
                                <Shield className="h-4 w-4 text-green-500" />
                            </div>
                            <div className="text-2xl font-bold">{deepHealth?.external_checks ? Object.values(deepHealth.external_checks).filter((c: any) => c.status === 'healthy').length : 0}/{deepHealth?.external_checks ? Object.keys(deepHealth.external_checks).length : 0}</div>
                            <div className="text-sm text-muted-foreground">External Providers</div>
                        </CardContent>
                    </Card>
                </motion.div>

                {/* Health Tabs */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <Tabs defaultValue="readiness">
                        <TabsList className="mb-6">
                            <TabsTrigger value="readiness">Readiness (DB + Redis)</TabsTrigger>
                            <TabsTrigger value="deep">Deep Health (External)</TabsTrigger>
                            <TabsTrigger value="basic">Basic Liveness</TabsTrigger>
                        </TabsList>

                        <TabsContent value="readiness" className="space-y-4">
                            {readiness?.checks ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {Object.entries(readiness.checks).map(([name, data]) => (
                                        <CheckCard key={name} name={name} data={data} />
                                    ))}
                                </div>
                            ) : loading ? (
                                <div className="flex items-center justify-center py-12">
                                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : (
                                <p className="text-muted-foreground">No readiness data available.</p>
                            )}
                        </TabsContent>

                        <TabsContent value="deep" className="space-y-4">
                            {deepHealth?.external_checks ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {Object.entries(deepHealth.external_checks).map(([name, data]) => (
                                        <CheckCard key={name} name={name} data={data} />
                                    ))}
                                </div>
                            ) : loading ? (
                                <div className="flex items-center justify-center py-12">
                                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : (
                                <p className="text-muted-foreground">No deep health data available.</p>
                            )}
                        </TabsContent>

                        <TabsContent value="basic" className="space-y-4">
                            <Card>
                                <CardContent className="p-6">
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <span className="text-muted-foreground">Status:</span>
                                            <span className="ml-2 font-medium capitalize">{basicHealth?.status || 'unknown'}</span>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Service:</span>
                                            <span className="ml-2 font-medium">{basicHealth?.service || 'confit-backend'}</span>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Version:</span>
                                            <span className="ml-2 font-medium">{basicHealth?.version || '1.0.0'}</span>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Timestamp:</span>
                                            <span className="ml-2 font-medium">{basicHealth?.timestamp ? new Date(basicHealth.timestamp).toLocaleString() : 'N/A'}</span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </motion.div>

                {/* Grafana Link */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="mt-8"
                >
                    <Card className="bg-gradient-to-r from-blue-500/5 to-cyan-500/5 border-blue-500/10">
                        <CardContent className="p-6 flex items-center justify-between flex-wrap gap-4">
                            <div className="flex items-center gap-3">
                                <TrendingUp className="h-5 w-5 text-blue-500" />
                                <div>
                                    <h3 className="font-medium">Grafana Dashboards</h3>
                                    <p className="text-sm text-muted-foreground">Detailed metrics, logs, and performance analytics</p>
                                </div>
                            </div>
                            <Button variant="outline" onClick={() => window.open(GRAFANA_URL, '_blank')}>
                                Open Grafana
                                <ArrowUpRight className="h-4 w-4 ml-2" />
                            </Button>
                        </CardContent>
                    </Card>
                </motion.div>
            </div>
        </MainLayout>
    );
}
