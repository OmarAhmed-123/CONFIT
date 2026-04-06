/**
 * Brand Dashboard Page
 * Dashboard for brand partners to manage products, orders, and analytics
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    LayoutDashboard, Package, BarChart3, Megaphone, Settings, Plus, Search,
    TrendingUp, DollarSign, Users, ShoppingBag, AlertCircle, CheckCircle2,
    Store, Eye, Edit, Trash2, Globe, Mail, Building2
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
import { useAuth } from '@/context/AuthContext';
import { AppRole, useRBAC } from '@/hooks/useRBAC';
import { cn } from '@/lib/utils';

// Mock data
const MOCK_PRODUCTS = [
    { id: '1', name: 'Premium Active Tee', sku: 'ACT-001', price: 45.00, stock: 124, status: 'In Stock', sales: 1200 },
    { id: '2', name: 'Flex Yoga Leggings', sku: 'LEG-002', price: 85.00, stock: 45, status: 'Low Stock', sales: 850 },
    { id: '3', name: 'Performance Hoodie', sku: 'HOD-003', price: 110.00, stock: 0, status: 'Out of Stock', sales: 600 },
    { id: '4', name: 'Runner Shorts', sku: 'SHT-004', price: 55.00, stock: 200, status: 'In Stock', sales: 1500 },
];

const MOCK_ORDERS = [
    { id: 'ORD-001', customer: 'John Doe', items: 3, total: '$245.00', status: 'completed', date: '2024-04-10' },
    { id: 'ORD-002', customer: 'Jane Smith', items: 2, total: '$89.50', status: 'processing', date: '2024-04-12' },
    { id: 'ORD-003', customer: 'Mike Johnson', items: 1, total: '$156.00', status: 'pending', date: '2024-04-14' },
];

const STATS = [
    { label: 'Total Sales', value: '$12,450', icon: DollarSign, trend: '+12%', color: 'text-green-500' },
    { label: 'Orders', value: '156', icon: ShoppingBag, trend: '+8%', color: 'text-blue-500' },
    { label: 'Products', value: '24', icon: Package, trend: '+2', color: 'text-purple-500' },
    { label: 'Views', value: '3,456', icon: Eye, trend: '+15%', color: 'text-amber-500' },
];

export default function BrandDashboardPage() {
    const router = useRouter();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const rbac = useRBAC();
    const [activeTab, setActiveTab] = useState('overview');
    const canAccessDashboard = rbac.hasAnyRole([AppRole.ADMIN, AppRole.BRAND_MANAGER]);

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login?redirect=/brand-dashboard');
            return;
        }

        if (!authLoading && isAuthenticated && !canAccessDashboard) {
            router.replace('/?error=unauthorized');
        }
    }, [authLoading, canAccessDashboard, isAuthenticated, router]);

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin h-8 w-8 border-4 border-amber-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (!isAuthenticated || !canAccessDashboard) {
        return null;
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'In Stock': return 'bg-green-500/10 text-green-600';
            case 'Low Stock': return 'bg-yellow-500/10 text-yellow-600';
            case 'Out of Stock': return 'bg-red-500/10 text-red-600';
            case 'completed': return 'bg-green-500/10 text-green-600';
            case 'processing': return 'bg-blue-500/10 text-blue-600';
            case 'pending': return 'bg-yellow-500/10 text-yellow-600';
            default: return 'bg-gray-500/10 text-gray-600';
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
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                            <Store className="h-6 w-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-display font-semibold">Brand Dashboard</h1>
                            <p className="text-muted-foreground">Welcome back, {user?.name || 'Brand Partner'}!</p>
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
                            <TabsTrigger value="products">Products</TabsTrigger>
                            <TabsTrigger value="orders">Orders</TabsTrigger>
                            <TabsTrigger value="analytics">Analytics</TabsTrigger>
                            <TabsTrigger value="settings">Settings</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Recent Products */}
                                <Card>
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="flex items-center gap-2">
                                                <Package className="h-5 w-5 text-amber-500" />
                                                Top Products
                                            </CardTitle>
                                            <Button size="sm" onClick={() => setActiveTab('products')}>
                                                View All
                                            </Button>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            {MOCK_PRODUCTS.slice(0, 3).map((product) => (
                                                <div key={product.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                                                    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
                                                        <Package className="h-5 w-5 text-amber-500" />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="font-medium truncate">{product.name}</div>
                                                        <div className="text-sm text-muted-foreground">${product.price} · {product.stock} in stock</div>
                                                    </div>
                                                    <Badge className={getStatusColor(product.status)}>{product.status}</Badge>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* Recent Orders */}
                                <Card>
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="flex items-center gap-2">
                                                <ShoppingBag className="h-5 w-5 text-green-500" />
                                                Recent Orders
                                            </CardTitle>
                                            <Button size="sm" onClick={() => setActiveTab('orders')}>
                                                View All
                                            </Button>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            {MOCK_ORDERS.map((order) => (
                                                <div key={order.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                                                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                                                        <ShoppingBag className="h-5 w-5 text-green-500" />
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
                                    </CardContent>
                                </Card>
                            </div>

                            {/* Quick Actions */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Quick Actions</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <Plus className="h-5 w-5 text-amber-500" />
                                            <span>Add Product</span>
                                        </Button>
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <BarChart3 className="h-5 w-5 text-blue-500" />
                                            <span>View Analytics</span>
                                        </Button>
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <Megaphone className="h-5 w-5 text-purple-500" />
                                            <span>Promotions</span>
                                        </Button>
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <Settings className="h-5 w-5 text-gray-500" />
                                            <span>Settings</span>
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="products">
                            <Card>
                                <CardHeader>
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                        <CardTitle>Product Management</CardTitle>
                                        <Button>
                                            <Plus className="h-4 w-4 mr-2" />
                                            Add Product
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Product</TableHead>
                                                <TableHead>SKU</TableHead>
                                                <TableHead>Price</TableHead>
                                                <TableHead>Stock</TableHead>
                                                <TableHead>Status</TableHead>
                                                <TableHead>Sales</TableHead>
                                                <TableHead className="text-right">Actions</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {MOCK_PRODUCTS.map((product) => (
                                                <TableRow key={product.id}>
                                                    <TableCell className="font-medium">{product.name}</TableCell>
                                                    <TableCell>{product.sku}</TableCell>
                                                    <TableCell>${product.price}</TableCell>
                                                    <TableCell>{product.stock}</TableCell>
                                                    <TableCell>
                                                        <Badge className={getStatusColor(product.status)}>{product.status}</Badge>
                                                    </TableCell>
                                                    <TableCell>{product.sales}</TableCell>
                                                    <TableCell className="text-right">
                                                        <div className="flex items-center justify-end gap-2">
                                                            <Button variant="ghost" size="sm">
                                                                <Eye className="h-4 w-4" />
                                                            </Button>
                                                            <Button variant="ghost" size="sm">
                                                                <Edit className="h-4 w-4" />
                                                            </Button>
                                                        </div>
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
                                                <TableHead>Items</TableHead>
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
                                                    <TableCell>{order.items}</TableCell>
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

                        <TabsContent value="analytics">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Analytics & Insights</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-center py-12">
                                        <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                        <h3 className="font-medium mb-2">Analytics Dashboard</h3>
                                        <p className="text-sm text-muted-foreground">View detailed sales and performance analytics</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="settings">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Brand Settings</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-center py-12">
                                        <Settings className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                        <h3 className="font-medium mb-2">Brand Settings</h3>
                                        <p className="text-sm text-muted-foreground">Manage your brand profile and preferences</p>
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
