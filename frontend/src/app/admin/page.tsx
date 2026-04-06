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
    CheckCircle, Clock, ChevronDown, Package, Store, Palette
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

// Mock admin data
const MOCK_USERS = [
    { id: '1', name: 'John Doe', email: 'john@example.com', role: 'user', status: 'active', joined: '2024-01-15', orders: 12 },
    { id: '2', name: 'Jane Smith', email: 'jane@example.com', role: 'brand_manager', status: 'active', joined: '2024-02-20', orders: 0 },
    { id: '3', name: 'Mike Johnson', email: 'mike@example.com', role: 'stylist', status: 'pending', joined: '2024-03-10', orders: 0 },
    { id: '4', name: 'Sarah Wilson', email: 'sarah@example.com', role: 'user', status: 'suspended', joined: '2024-01-05', orders: 8 },
];

const MOCK_ORDERS = [
    { id: 'ORD-001', customer: 'John Doe', total: '$245.00', status: 'completed', date: '2024-04-10' },
    { id: 'ORD-002', customer: 'Jane Smith', total: '$89.50', status: 'processing', date: '2024-04-12' },
    { id: 'ORD-003', customer: 'Mike Johnson', total: '$156.00', status: 'pending', date: '2024-04-14' },
];

const STATS = [
    { label: 'Total Users', value: '1,234', icon: Users, trend: '+12%', color: 'text-blue-500' },
    { label: 'Total Orders', value: '5,678', icon: ShoppingBag, trend: '+8%', color: 'text-green-500' },
    { label: 'Revenue', value: '$45,230', icon: DollarSign, trend: '+15%', color: 'text-purple-500' },
    { label: 'Active Brands', value: '89', icon: Store, trend: '+5%', color: 'text-amber-500' },
];

export default function AdminDashboardPage() {
    const router = useRouter();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const rbac = useRBAC();
    const [activeTab, setActiveTab] = useState('overview');
    const [userFilter, setUserFilter] = useState('all');
    const canAccessDashboard = rbac.hasRole(AppRole.ADMIN);

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login?redirect=/admin');
            return;
        }

        if (!authLoading && isAuthenticated && !canAccessDashboard) {
            router.replace('/?error=unauthorized');
        }
    }, [authLoading, canAccessDashboard, isAuthenticated, router]);

    if (authLoading) {
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
                                            {MOCK_USERS.slice(0, 4).map((u) => (
                                                <div key={u.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-medium">
                                                        {u.name.split(' ').map(n => n[0]).join('')}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="font-medium truncate">{u.name}</div>
                                                        <div className="text-sm text-muted-foreground truncate">{u.email}</div>
                                                    </div>
                                                    <Badge className={getRoleColor(u.role)}>{u.role}</Badge>
                                                </div>
                                            ))}
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
                                            {MOCK_ORDERS.map((order) => (
                                                <div key={order.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                                                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                                                        <Package className="h-5 w-5 text-green-500" />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="font-medium">{order.id}</div>
                                                        <div className="text-sm text-muted-foreground">{order.customer}</div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="font-medium">{order.total}</div>
                                                        <Badge className={getStatusColor(order.status)}>{order.status}</Badge>
                                                    </div>
                                                </div>
                                            ))}
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
                                            {MOCK_USERS.map((u) => (
                                                <TableRow key={u.id}>
                                                    <TableCell>
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
                                                                {u.name.split(' ').map(n => n[0]).join('')}
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
                                            ))}
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
                                            {MOCK_ORDERS.map((order) => (
                                                <TableRow key={order.id}>
                                                    <TableCell className="font-medium">{order.id}</TableCell>
                                                    <TableCell>{order.customer}</TableCell>
                                                    <TableCell>{order.total}</TableCell>
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
                                            ))}
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
