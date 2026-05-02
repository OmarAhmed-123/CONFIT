/**
 * Admin Dashboard Page
 * Administrative dashboard for platform management
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    Shield, Users, ShoppingBag, DollarSign, TrendingUp, AlertTriangle,
    Settings, BarChart3, Bell, Search, Filter, Download, Eye, Ban,
    CheckCircle, Clock, ChevronDown, Package, Store, Palette, Activity, Loader2
} from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/context/AuthContext';
import { AppRole, useRBAC } from '@/hooks/useRBAC';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { toast } from 'sonner';

// Types
interface AdminStats {
    total_users: number;
    total_orders: number;
    total_revenue: number;
    active_brands: number;
    user_growth_percent: number;
    order_growth_percent: number;
    revenue_growth_percent: number;
    brand_growth_percent: number;
}

interface AdminUser {
    id: string;
    name: string;
    email: string;
    role: string;
    status: 'active' | 'pending' | 'suspended';
    joined: string;
    orders: number;
}

interface AdminOrder {
    id: string;
    customer: string;
    total: number;
    status: string;
    date: string;
}

const INITIAL_STATS: AdminStats = {
    total_users: 0,
    total_orders: 0,
    total_revenue: 0,
    active_brands: 0,
    user_growth_percent: 0,
    order_growth_percent: 0,
    revenue_growth_percent: 0,
    brand_growth_percent: 0,
};

function toNumber(value: unknown): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
}

function normalizeAdminStats(payload: unknown): AdminStats {
    const source = (payload && typeof payload === 'object' && 'data' in payload)
        ? (payload as { data?: unknown }).data
        : payload;
    const data = source && typeof source === 'object' ? source as Record<string, unknown> : {};

    return {
        total_users: toNumber(data.total_users),
        total_orders: toNumber(data.total_orders),
        total_revenue: toNumber(data.total_revenue ?? data.total_revenue_egp),
        active_brands: toNumber(data.active_brands),
        user_growth_percent: toNumber(data.user_growth_percent),
        order_growth_percent: toNumber(data.order_growth_percent),
        revenue_growth_percent: toNumber(data.revenue_growth_percent),
        brand_growth_percent: toNumber(data.brand_growth_percent),
    };
}

function normalizeAdminUser(raw: any): AdminUser {
    return {
        id: String(raw?.id || ''),
        name: String(raw?.name || raw?.email || 'User'),
        email: String(raw?.email || ''),
        role: String(raw?.role || 'user'),
        status: ['active', 'pending', 'suspended'].includes(String(raw?.status))
            ? raw.status
            : 'active',
        joined: String(raw?.joined || raw?.created_at || ''),
        orders: toNumber(raw?.orders),
    };
}

function normalizeAdminOrder(raw: any): AdminOrder {
    return {
        id: String(raw?.id || raw?.order_number || ''),
        customer: String(raw?.customer || raw?.customer_name || 'Customer'),
        total: toNumber(raw?.total),
        status: String(raw?.status || 'processing'),
        date: String(raw?.date || raw?.placed_at || raw?.created_at || ''),
    };
}

export default function AdminDashboardPage() {
    const router = useRouter();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const rbac = useRBAC();
    const [hasMounted, setHasMounted] = useState(false);
    const [activeTab, setActiveTab] = useState('overview');
    const [userFilter, setUserFilter] = useState('all');
    const canAccessDashboard = rbac.hasRole(AppRole.ADMIN);

    // Real data states
    const [stats, setStats] = useState<AdminStats>(INITIAL_STATS);
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [orders, setOrders] = useState<AdminOrder[]>([]);
    const [isLoadingStats, setIsLoadingStats] = useState(true);
    const [isLoadingUsers, setIsLoadingUsers] = useState(true);
    const [isLoadingOrders, setIsLoadingOrders] = useState(true);

    useEffect(() => {
        setHasMounted(true);
    }, []);

    // Fetch admin data
    useEffect(() => {
        if (!authLoading && isAuthenticated && canAccessDashboard) {
            fetchAdminStats();
            fetchAdminUsers();
            fetchAdminOrders();
        }
    }, [authLoading, isAuthenticated, canAccessDashboard]);

    const fetchAdminStats = async () => {
        try {
            setIsLoadingStats(true);
            // Use analytics admin endpoint
            const data = await api.get<unknown>(API_ENDPOINTS.ANALYTICS.ADMIN_OVERVIEW);
            setStats(normalizeAdminStats(data));
        } catch (error) {
            console.error('Failed to fetch admin stats:', error);
            toast.error('Failed to load dashboard statistics');
            setStats(INITIAL_STATS);
        } finally {
            setIsLoadingStats(false);
        }
    };

    const fetchAdminUsers = async () => {
        try {
            setIsLoadingUsers(true);
            const data = await api.get<{ users?: unknown[] }>('/api/admin/users');
            setUsers(Array.isArray(data.users) ? data.users.map(normalizeAdminUser) : []);
        } catch (error) {
            console.error('Failed to fetch users:', error);
            // Graceful fallback - don't block UI
            setUsers([]);
        } finally {
            setIsLoadingUsers(false);
        }
    };

    const fetchAdminOrders = async () => {
        try {
            setIsLoadingOrders(true);
            const data = await api.get<{ orders?: unknown[] }>('/api/admin/orders');
            setOrders(Array.isArray(data.orders) ? data.orders.map(normalizeAdminOrder) : []);
        } catch (error) {
            console.error('Failed to fetch orders:', error);
            setOrders([]);
        } finally {
            setIsLoadingOrders(false);
        }
    };

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login?redirect=/admin');
            return;
        }

        if (!authLoading && isAuthenticated && !canAccessDashboard) {
            router.replace('/?error=unauthorized');
        }
    }, [authLoading, canAccessDashboard, isAuthenticated, router]);

    // Stats configuration
    const safeStats = normalizeAdminStats(stats);
    const STATS = [
        { label: 'Total Users', value: safeStats.total_users.toLocaleString(), icon: Users, trend: `+${safeStats.user_growth_percent}%`, color: 'text-blue-500' },
        { label: 'Total Orders', value: safeStats.total_orders.toLocaleString(), icon: ShoppingBag, trend: `+${safeStats.order_growth_percent}%`, color: 'text-green-500' },
        { label: 'Revenue', value: `$${safeStats.total_revenue.toLocaleString()}`, icon: DollarSign, trend: `+${safeStats.revenue_growth_percent}%`, color: 'text-purple-500' },
        { label: 'Active Brands', value: safeStats.active_brands.toString(), icon: Store, trend: `+${safeStats.brand_growth_percent}%`, color: 'text-amber-500' },
    ];

    if (!hasMounted || authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin h-8 w-8 border-4 border-red-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (!isAuthenticated || !canAccessDashboard) {
        return null;
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active': return 'bg-green-500/10 text-green-600';
            case 'pending': return 'bg-yellow-500/10 text-yellow-600';
            case 'suspended': return 'bg-red-500/10 text-red-600';
            case 'completed': return 'bg-green-500/10 text-green-600';
            case 'processing': return 'bg-blue-500/10 text-blue-600';
            default: return 'bg-gray-500/10 text-gray-600';
        }
    };

    const getRoleColor = (role: string) => {
        switch (role) {
            case 'admin': return 'bg-red-500/10 text-red-600';
            case 'brand_manager': return 'bg-amber-500/10 text-amber-600';
            case 'stylist': return 'bg-pink-500/10 text-pink-600';
            default: return 'bg-blue-500/10 text-blue-600';
        }
    };

    return (
        <MainLayout>
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <div className="flex items-center gap-4 mb-2">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
                            <Shield className="h-6 w-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-display font-semibold">Admin Dashboard</h1>
                            <p className="text-muted-foreground">Platform management and oversight</p>
                        </div>
                    </div>
                </motion.div>

                {/* Stats Grid */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
                >
                    {STATS.map((stat, i) => {
                        const Icon = stat.icon;
                        return (
                            <Card key={i} className="hover:shadow-lg transition-shadow">
                                <CardContent className="p-6">
                                    <div className="flex items-center justify-between mb-2">
                                        <Icon className={cn('h-5 w-5', stat.color)} />
                                        <span className="text-xs text-green-600 font-medium">{stat.trend}</span>
                                    </div>
                                    <div className="text-2xl font-bold">{stat.value}</div>
                                    <div className="text-sm text-muted-foreground">{stat.label}</div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </motion.div>

                {/* Main Content */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="mb-6">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="users">Users</TabsTrigger>
                            <TabsTrigger value="orders">Orders</TabsTrigger>
                            <TabsTrigger value="brands">Brands</TabsTrigger>
                            <TabsTrigger value="settings">Settings</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Recent Users */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <Users className="h-5 w-5 text-blue-500" />
                                            Recent Users
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            {isLoadingUsers ? (
                                                <div className="flex items-center justify-center py-8">
                                                    <Loader2 className="h-6 w-6 animate-spin" />
                                                </div>
                                            ) : users.length === 0 ? (
                                                <p className="text-center text-muted-foreground py-8">No users found</p>
                                            ) : (
                                                users.slice(0, 4).map((u) => (
                                                    <div key={u.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-medium">
                                                            {u.name?.split(' ').map((n: string) => n[0]).join('') || 'U'}
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="font-medium truncate">{u.name}</div>
                                                            <div className="text-sm text-muted-foreground truncate">{u.email}</div>
                                                        </div>
                                                        <Badge className={getRoleColor(u.role)}>{u.role}</Badge>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                        <Button variant="outline" className="w-full mt-4" onClick={() => setActiveTab('users')}>
                                            View All Users
                                        </Button>
                                    </CardContent>
                                </Card>

                                {/* Recent Orders */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <ShoppingBag className="h-5 w-5 text-green-500" />
                                            Recent Orders
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            {isLoadingOrders ? (
                                                <div className="flex items-center justify-center py-8">
                                                    <Loader2 className="h-6 w-6 animate-spin" />
                                                </div>
                                            ) : orders.length === 0 ? (
                                                <p className="text-center text-muted-foreground py-8">No orders found</p>
                                            ) : (
                                                orders.slice(0, 4).map((order) => (
                                                    <div key={order.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                                                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                                                            <Package className="h-5 w-5 text-green-500" />
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="font-medium">{order.id}</div>
                                                            <div className="text-sm text-muted-foreground">{order.customer}</div>
                                                        </div>
                                                        <div className="text-right">
                                                            <div className="font-medium">${order.total?.toFixed(2)}</div>
                                                            <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
                                                        </div>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                        <Button variant="outline" className="w-full mt-4" onClick={() => setActiveTab('orders')}>
                                            View All Orders
                                        </Button>
                                    </CardContent>
                                </Card>
                            </div>

                            {/* Alerts */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                                        System Alerts
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-3 p-3 bg-amber-500/10 rounded-lg">
                                            <AlertTriangle className="h-5 w-5 text-amber-500" />
                                            <div className="flex-1">
                                                <div className="font-medium">3 pending user verifications</div>
                                                <div className="text-sm text-muted-foreground">Review and approve new accounts</div>
                                            </div>
                                            <Button size="sm" variant="outline">Review</Button>
                                        </div>
                                        <div className="flex items-center gap-3 p-3 bg-blue-500/10 rounded-lg">
                                            <Store className="h-5 w-5 text-blue-500" />
                                            <div className="flex-1">
                                                <div className="font-medium">2 new brand applications</div>
                                                <div className="text-sm text-muted-foreground">Pending approval for brand partnerships</div>
                                            </div>
                                            <Button size="sm" variant="outline">Review</Button>
                                        </div>
                                        <div className="flex items-center gap-3 p-3 bg-emerald-500/10 rounded-lg">
                                            <Activity className="h-5 w-5 text-emerald-500" />
                                            <div className="flex-1">
                                                <div className="font-medium">System Monitoring</div>
                                                <div className="text-sm text-muted-foreground">Live observability & health dashboards</div>
                                            </div>
                                            <Button size="sm" variant="outline" onClick={() => router.push('/monitoring')}>Open</Button>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="users">
                            <Card>
                                <CardHeader>
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                        <CardTitle>User Management</CardTitle>
                                        <div className="flex items-center gap-2">
                                            <div className="relative">
                                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                                <Input placeholder="Search users..." className="pl-9 w-[200px]" />
                                            </div>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="outline" size="sm">
                                                        <Filter className="h-4 w-4 mr-2" />
                                                        Filter
                                                        <ChevronDown className="h-4 w-4 ml-2" />
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent>
                                                    <DropdownMenuItem>All Users</DropdownMenuItem>
                                                    <DropdownMenuItem>Active</DropdownMenuItem>
                                                    <DropdownMenuItem>Pending</DropdownMenuItem>
                                                    <DropdownMenuItem>Suspended</DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>User</TableHead>
                                                <TableHead>Role</TableHead>
                                                <TableHead>Status</TableHead>
                                                <TableHead>Joined</TableHead>
                                                <TableHead>Orders</TableHead>
                                                <TableHead className="text-right">Actions</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {isLoadingUsers ? (
                                                <TableRow>
                                                    <TableCell colSpan={6} className="text-center py-8">
                                                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                                                    </TableCell>
                                                </TableRow>
                                            ) : users.length === 0 ? (
                                                <TableRow>
                                                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                                        No users found
                                                    </TableCell>
                                                </TableRow>
                                            ) : (
                                                users.map((u) => (
                                                    <TableRow key={u.id}>
                                                        <TableCell>
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
                                                                    {u.name?.split(' ').map((n: string) => n[0]).join('') || 'U'}
                                                                </div>
                                                                <div>
                                                                    <div className="font-medium">{u.name}</div>
                                                                    <div className="text-sm text-muted-foreground">{u.email}</div>
                                                                </div>
                                                            </div>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Badge className={getRoleColor(u.role)}>{u.role}</Badge>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Badge className={getStatusColor(u.status)}>{u.status}</Badge>
                                                        </TableCell>
                                                        <TableCell>{u.joined}</TableCell>
                                                        <TableCell>{u.orders}</TableCell>
                                                        <TableCell className="text-right">
                                                            <DropdownMenu>
                                                                <DropdownMenuTrigger asChild>
                                                                    <Button variant="ghost" size="sm">
                                                                        <Eye className="h-4 w-4" />
                                                                    </Button>
                                                                </DropdownMenuTrigger>
                                                                <DropdownMenuContent align="end">
                                                                    <DropdownMenuItem>View Profile</DropdownMenuItem>
                                                                    <DropdownMenuItem>Edit User</DropdownMenuItem>
                                                                    <DropdownMenuItem>Change Role</DropdownMenuItem>
                                                                    <DropdownMenuItem className="text-red-600">Suspend</DropdownMenuItem>
                                                                </DropdownMenuContent>
                                                            </DropdownMenu>
                                                        </TableCell>
                                                    </TableRow>
                                                ))
                                            )}
                                        </TableBody>
                                    </Table>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="orders">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Order Management</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Order ID</TableHead>
                                                <TableHead>Customer</TableHead>
                                                <TableHead>Total</TableHead>
                                                <TableHead>Status</TableHead>
                                                <TableHead>Date</TableHead>
                                                <TableHead className="text-right">Actions</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {isLoadingOrders ? (
                                                <TableRow>
                                                    <TableCell colSpan={6} className="text-center py-8">
                                                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                                                    </TableCell>
                                                </TableRow>
                                            ) : orders.length === 0 ? (
                                                <TableRow>
                                                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                                        No orders found
                                                    </TableCell>
                                                </TableRow>
                                            ) : (
                                                orders.map((order) => (
                                                    <TableRow key={order.id}>
                                                        <TableCell className="font-medium">{order.id}</TableCell>
                                                        <TableCell>{order.customer}</TableCell>
                                                        <TableCell>${order.total?.toFixed(2)}</TableCell>
                                                        <TableCell>
                                                            <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
                                                        </TableCell>
                                                        <TableCell>{order.date}</TableCell>
                                                        <TableCell className="text-right">
                                                            <Button variant="ghost" size="sm">
                                                                <Eye className="h-4 w-4" />
                                                            </Button>
                                                        </TableCell>
                                                    </TableRow>
                                                ))
                                            )}
                                        </TableBody>
                                    </Table>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="brands">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Brand Management</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-center py-12">
                                        <Store className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                        <h3 className="font-medium mb-2">Brand Management</h3>
                                        <p className="text-sm text-muted-foreground">Manage brand partnerships and applications</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="settings">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Platform Settings</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-center py-12">
                                        <Settings className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                        <h3 className="font-medium mb-2">Platform Settings</h3>
                                        <p className="text-sm text-muted-foreground">Configure platform-wide settings and preferences</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </motion.div>
            </div>
        </MainLayout>
    );
}
