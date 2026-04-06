import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    LayoutDashboard, Package, BarChart3, Megaphone, Settings, Plus, Search, Filter, Upload, MoreHorizontal,
    TrendingUp, DollarSign, Users, ShoppingBag, AlertCircle, CheckCircle2, X, RotateCcw, User, Bell, CreditCard,
    Globe, Mail, Building2, Truck, RefreshCw, Download, Eye, Edit, Trash2, UserPlus, Shield, Clock, MapPin,
    Calendar, ChevronDown, ChevronRight, ExternalLink, Copy, FileText, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Textarea } from "@/components/ui/textarea";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { MOCK_ORDERS, MOCK_TEAM_MEMBERS, MOCK_ACTIVITY_LOGS, MOCK_CUSTOMER_DEMOGRAPHICS, MOCK_TRAFFIC_SOURCES, getOrderStatusColor, getPaymentStatusColor, getRoleColor, formatCurrency, formatDateTime, getRelativeTime } from '@/services/brandMockData';
import { useAuth } from '@/context/AuthContext';
import type { Order, OrderStatus, TeamMember, TeamRole, Brand } from '@/types/brandTypes';
import { apiUrl } from '@/lib/api';
import { createTransition } from '@/motion';
import { OwnerNotificationsPanel } from '@/components/notifications/OwnerNotificationsPanel';
import { SOSTACPanel } from '@/components/analytics/SOSTACPanel';
import { SoldProductsTable } from '@/components/dashboard/SoldProductsTable';

// Mock Products Data
const MOCK_PRODUCTS = [
    { id: '1', name: 'Premium Active Tee', sku: 'ACT-001', price: 45.00, stock: 124, status: 'In Stock', category: 'Tops', sales: 1200 },
    { id: '2', name: 'Flex Yoga Leggings', sku: 'LEG-002', price: 85.00, stock: 45, status: 'Low Stock', category: 'Bottoms', sales: 850 },
    { id: '3', name: 'Performance Hoodie', sku: 'HOD-003', price: 110.00, stock: 0, status: 'Out of Stock', category: 'Outerwear', sales: 600 },
    { id: '4', name: 'Runner Shorts', sku: 'SHT-004', price: 55.00, stock: 200, status: 'In Stock', category: 'Bottoms', sales: 1500 },
    { id: '5', name: 'Impact Sports Bra', sku: 'BRA-005', price: 40.00, stock: 85, status: 'In Stock', category: 'Tops', sales: 980 },
    { id: '6', name: 'Recovery Slides', sku: 'SLD-006', price: 35.00, stock: 15, status: 'Low Stock', category: 'Footwear', sales: 400 },
];

const SALES_DATA = [
    { name: 'Mon', revenue: 4000, orders: 24 }, { name: 'Tue', revenue: 3000, orders: 18 },
    { name: 'Wed', revenue: 2000, orders: 12 }, { name: 'Thu', revenue: 2780, orders: 20 },
    { name: 'Fri', revenue: 1890, orders: 15 }, { name: 'Sat', revenue: 2390, orders: 19 },
    { name: 'Sun', revenue: 3490, orders: 28 },
];

const CAMPAIGNS = [
    { id: 1, name: 'Summer Sale Boost', status: 'Active', budget: '$500', spent: '$240', clicks: 1200 },
    { id: 2, name: 'New Arrivals Promo', status: 'Scheduled', budget: '$1000', spent: '$0', clicks: 0 },
    { id: 3, name: 'Yoga Collection', status: 'Completed', budget: '$300', spent: '$300', clicks: 850 },
];

const MOCK_BRAND = {
    id: 'brand-1',
    name: 'CONFIT Active Wear',
    website: 'https://confit-active.com',
    description: 'Premium athletic wear designed for performance and style. We create sustainable, comfortable clothing for active lifestyles.',
    email: 'support@confit-active.com',
    phone: '+1 (555) 123-4567',
    logo: 'https://images.unsplash.com/photo-1441986300917-64674e8c6e58?w=200',
    settings: {
        notifications: {
            orderAlerts: true,
            lowStockAlerts: true,
            reviewAlerts: false
        },
        payoutMethod: 'bank_transfer',
        minimumPayout: 100
    }
};

const DEFAULT_BRAND_ID = 'brand-1';

const ANALYTICS_STYLED_ITEMS = [
    { name: 'Premium Active Tee', count: 1240, purchaseRate: '12%' },
    { name: 'Flex Yoga Leggings', count: 980, purchaseRate: '15%' },
    { name: 'Runner Shorts', count: 850, purchaseRate: '8%' },
    { name: 'Impact Sports Bra', count: 600, purchaseRate: '18%' },
];

// Helper Components
function StatCard({ title, value, change, icon: Icon, positive = true }: { title: string; value: string; change: string; icon: React.ElementType; positive?: boolean }) {
    return (
        <div className="bg-card border border-border rounded-xl p-6">
            <div className="flex justify-between items-start mb-4">
                <div><h3 className="text-sm font-medium text-muted-foreground">{title}</h3><p className="text-2xl font-bold mt-1">{value}</p></div>
                <div className="h-10 w-10 bg-muted rounded-full flex items-center justify-center"><Icon className="h-5 w-5 text-muted-foreground" /></div>
            </div>
            <p className={cn("text-xs flex items-center gap-1", positive ? "text-green-600" : "text-red-500")}>
                {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}{change}
            </p>
        </div>
    );
}

function FunnelStep({ label, value, percent, color }: { label: string; value: string; percent: string; color: string }) {
    return (
        <div className="relative"><div className="flex justify-between text-sm mb-1"><span className="font-medium">{label}</span><span className="text-muted-foreground">{value} ({percent})</span></div>
            <div className="w-full bg-muted rounded-full h-3 overflow-hidden"><motion.div initial={{ width: 0 }} animate={{ width: percent }} transition={createTransition({ duration: 1 })} className={cn("h-full rounded-full", color)} /></div>
        </div>
    );
}

// Tab Components
function OverviewTab() {
    const [analytics, setAnalytics] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        const token = localStorage.getItem('confit_token');
        const fetchOverview = async () => {
            // Show mock data immediately
            setAnalytics({
                revenue: 125000,
                costs: 75000,
                profit: 50000,
                monthly_data: SALES_DATA,
                top_skus: ANALYTICS_STYLED_ITEMS.slice(0, 5),
            });
            setIsLoading(false);

            try {
                let brandId = DEFAULT_BRAND_ID;
                const brandsRes = await fetch(apiUrl('/api/brands/'), { headers: token ? { Authorization: `Bearer ${token}` } : {} });
                if (brandsRes.ok) {
                    const brands = await brandsRes.json();
                    if (Array.isArray(brands) && brands.length > 0 && brands[0].id) {
                        brandId = brands[0].id;
                    }
                }
                const res = await fetch(apiUrl(`/api/brands/${brandId}/analytics`), {
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                if (cancelled) return;
                if (res.ok) {
                    const data = await res.json();
                    setAnalytics(data);
                } else {
                    setError('Failed to load analytics');
                }
            } catch (e) {
                if (!cancelled) setError('Failed to load overview');
            } finally {
                if (!cancelled) setIsLoading(false);
            }
        };
        fetchOverview();
        return () => { cancelled = true; };
    }, []);

    // Data is shown immediately from mock, no loading screen needed
    if (!analytics) {
        return (
            <div className="p-8 flex flex-col items-center justify-center min-h-[200px]">
                <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-sm text-muted-foreground">{error || 'No data available'}</p>
                <p className="text-xs text-muted-foreground mt-2">Ensure you are signed in and have brand access.</p>
            </div>
        );
    }

    const monthlyData = analytics.monthly_data || { labels: [], revenue: [], costs: [] };
    const chartData = Array.isArray(monthlyData.labels)
        ? monthlyData.labels.map((label: string, i: number) => ({
            name: label,
            revenue: monthlyData.revenue?.[i] ?? 0,
            costs: monthlyData.costs?.[i] ?? 0,
        }))
        : [];

    return (
        <div className="space-y-6">
            {error && (
                <div className="rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
                    {error} — showing preview analytics.
                </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Total Revenue" value={formatCurrency(analytics.total_revenue ?? 0)} change="+20.1% from last month" icon={DollarSign} positive />
                <StatCard title="Total Costs" value={formatCurrency(analytics.total_costs ?? 0)} change="-1.2% from last month" icon={CreditCard} positive={false} />
                <StatCard title="Net Profit" value={formatCurrency(analytics.net_profit ?? 0)} change={`${analytics.profit_margin ?? 0}% Margin`} icon={TrendingUp} positive={!!analytics.is_profitable} />
                <StatCard title="Conversion Rate" value="3.2%" change="+1.1% this week" icon={TrendingUp} positive />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-7 gap-6">
                <div className="lg:col-span-4 bg-card border border-border rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-2">Revenue Overview</h3>
                    <p className="text-sm text-muted-foreground mb-6">Monthly financial performance</p>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData}>
                                <defs><linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} /><stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} /></linearGradient></defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                                <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
                                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                                <Area type="monotone" dataKey="revenue" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" />
                                <Area type="monotone" dataKey="costs" stroke="#ef4444" strokeWidth={2} fillOpacity={0} fill="transparent" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
                <div className="lg:col-span-3 bg-card border border-border rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-2">Top Performing SKUs</h3>
                    <p className="text-sm text-muted-foreground mb-4">Highest revenue products</p>
                    <div className="space-y-4">
                        {MOCK_PRODUCTS.slice(0, 4).map((product, i) => (
                            <div key={product.id} className="flex items-center justify-between p-3 bg-muted/40 rounded-lg">
                                <div className="flex items-center gap-3">
                                    <div className="h-10 w-10 rounded bg-muted flex items-center justify-center font-bold text-muted-foreground">{product.sku.slice(0, 2)}</div>
                                    <div><p className="font-medium text-sm">{product.name}</p><p className="text-xs text-muted-foreground">{product.sku}</p></div>
                                </div>
                                <div className="text-right"><p className="font-medium text-sm">${product.price.toFixed(2)}</p><p className="text-xs text-green-500">+{product.sales} sold</p></div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <OwnerNotificationsPanel className="lg:col-span-2" />
                <div className="bg-card border border-border rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-2">Pickup ops</h3>
                    <p className="text-sm text-muted-foreground">
                        Pickup scheduling alerts appear here instantly for owners.
                    </p>
                </div>
            </div>
        </div>
    );
}

function ProductsTab() {
    const [searchTerm, setSearchTerm] = useState('');
    const [products, setProducts] = useState<any[]>(MOCK_PRODUCTS);
    const [isLoading, setIsLoading] = useState(false);
    const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

    useEffect(() => {
        // Show mock data immediately, then try to fetch from API
        const fetchBrandProducts = async () => {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);

                const res = await fetch(apiUrl('/api/products'), { signal: controller.signal });
                clearTimeout(timeoutId);

                if (res.ok) {
                    const data = await res.json();
                    if (Array.isArray(data)) {
                        setProducts(data);
                    } else if (data.products && Array.isArray(data.products)) {
                        setProducts(data.products);
                    }
                }
            } catch (e) {
                if (e instanceof Error && e.name !== 'AbortError') {
                    console.warn("Failed to fetch products, using mock data", e);
                }
                // Keep MOCK_PRODUCTS already set
            }
        };
        fetchBrandProducts();
    }, []);

    const filteredProducts = products.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase()) || (p.sku && p.sku.toLowerCase().includes(searchTerm.toLowerCase())));

    const handleStockUpdate = async (id: string, newStock: number) => {
        // Optimistic UI update
        const originalProducts = [...products];
        setProducts(products.map(p => p.id === id ? { ...p, stock: newStock, status: newStock === 0 ? 'Out of Stock' : newStock < 20 ? 'Low Stock' : 'In Stock' } : p));

        try {
            await fetch(apiUrl(`/api/products/${id}`), {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stockQuantity: newStock })
            });
            toast.success("Stock Updated", { description: "Inventory count has been synced." });
        } catch (error) {
            console.error("Failed to update stock", error);
            setProducts(originalProducts); // Revert
            toast.error("Failed to update stock");
        }
    };

    const handleDeleteProduct = async (id: string) => {
        if (!confirm("Are you sure you want to delete this product?")) return;

        const originalProducts = [...products];
        setProducts(products.filter(p => p.id !== id));

        try {
            const res = await fetch(apiUrl(`/api/products/${id}`), { method: 'DELETE' });
            if (!res.ok) throw new Error("Failed to delete");
            toast.success("Product Deleted");
        } catch (error) {
            console.error("Failed to delete product", error);
            setProducts(originalProducts);
            toast.error("Failed to delete product");
        }
    };

    const [newProduct, setNewProduct] = useState({ name: '', sku: '', price: '', stock: '', category: 'tops', description: '' });

    const handleAddProduct = async () => {
        try {
            const payload = {
                name: newProduct.name,
                sku: newProduct.sku, // Note: SKU isn't in backend model yet but let's send it
                price: parseFloat(newProduct.price),
                stockQuantity: parseInt(newProduct.stock),
                category: newProduct.category,
                description: newProduct.description,
                brandId: "brand-confit-essentials", // Hardcoded for demo
                images: ["https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3"], // Placeholder
                gender: "unisex"
            };

            const res = await fetch(apiUrl('/api/products/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const created = await res.json();
                setProducts([...products, created]);
                toast.success("Product Added");
                setIsAddDialogOpen(false);
                setNewProduct({ name: '', sku: '', price: '', stock: '', category: 'tops', description: '' }); // Reset
            } else {
                throw new Error("Failed to create");
            }
        } catch (error) {
            console.error("Failed to add product", error);
            toast.error("Failed to add product");
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between gap-4">
                <div className="flex items-center gap-2 w-full sm:w-auto">
                    <div className="relative flex-1 sm:w-64"><Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" /><Input placeholder="Search products..." className="pl-9" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} /></div>
                    <Button variant="outline" size="icon"><Filter className="h-4 w-4" /></Button>
                </div>
                <div className="flex gap-2">
                    <Dialog><DialogTrigger asChild><Button variant="outline"><Upload className="h-4 w-4 mr-2" />Bulk Upload</Button></DialogTrigger>
                        <DialogContent><DialogHeader><DialogTitle>Upload Collection</DialogTitle><DialogDescription>Upload a CSV file to update inventory.</DialogDescription></DialogHeader>
                            <div className="h-40 border-2 border-dashed border-muted-foreground/25 rounded-xl flex flex-col items-center justify-center text-muted-foreground hover:bg-muted/50 cursor-pointer"><Upload className="h-8 w-8 mb-2" /><p className="text-sm">Drag & drop CSV here</p></div>
                            <DialogFooter><Button onClick={() => toast.success("Upload Started")}>Upload File</Button></DialogFooter></DialogContent></Dialog>
                    <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}><DialogTrigger asChild><Button variant="hero"><Plus className="h-4 w-4 mr-2" />Add Product</Button></DialogTrigger>
                        <DialogContent className="max-w-2xl"><DialogHeader><DialogTitle>Add New Product</DialogTitle></DialogHeader>
                            <div className="grid grid-cols-2 gap-4 py-4">
                                <div className="space-y-2"><label className="text-sm font-medium">Product Name</label><Input placeholder="e.g. Premium Hoodie" value={newProduct.name} onChange={e => setNewProduct({ ...newProduct, name: e.target.value })} /></div>
                                <div className="space-y-2"><label className="text-sm font-medium">SKU</label><Input placeholder="e.g. HOD-007" value={newProduct.sku} onChange={e => setNewProduct({ ...newProduct, sku: e.target.value })} /></div>
                                <div className="space-y-2"><label className="text-sm font-medium">Price</label><Input type="number" placeholder="0.00" value={newProduct.price} onChange={e => setNewProduct({ ...newProduct, price: e.target.value })} /></div>
                                <div className="space-y-2"><label className="text-sm font-medium">Stock</label><Input type="number" placeholder="0" value={newProduct.stock} onChange={e => setNewProduct({ ...newProduct, stock: e.target.value })} /></div>
                                <div className="space-y-2"><label className="text-sm font-medium">Category</label>
                                    <Select value={newProduct.category} onValueChange={v => setNewProduct({ ...newProduct, category: v })}><SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger><SelectContent><SelectItem value="tops">Tops</SelectItem><SelectItem value="bottoms">Bottoms</SelectItem><SelectItem value="outerwear">Outerwear</SelectItem><SelectItem value="footwear">Footwear</SelectItem></SelectContent></Select></div>
                                <div className="col-span-2 space-y-2"><label className="text-sm font-medium">Description</label><Textarea placeholder="Product description..." value={newProduct.description} onChange={e => setNewProduct({ ...newProduct, description: e.target.value })} /></div>
                            </div>
                            <DialogFooter><Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>Cancel</Button><Button onClick={handleAddProduct}>Add Product</Button></DialogFooter></DialogContent></Dialog>
                </div>
            </div>
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <Table><TableHeader><TableRow><TableHead>Product Info</TableHead><TableHead>Category</TableHead><TableHead>Price</TableHead><TableHead>Stock</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                    <TableBody>{filteredProducts.map((product) => (
                        <TableRow key={product.id}><TableCell><div><p className="font-medium">{product.name}</p><p className="text-xs text-muted-foreground">SKU: {product.sku}</p></div></TableCell>
                            <TableCell>{product.category}</TableCell><TableCell>${product.price.toFixed(2)}</TableCell>
                            <TableCell><div className="flex items-center gap-2"><span>{product.stock}</span>
                                <Dialog><DialogTrigger asChild><button title="Edit inventory" aria-label="Edit inventory" className="h-6 w-6 rounded hover:bg-muted flex items-center justify-center"><Edit className="h-3 w-3" /></button></DialogTrigger>
                                    <DialogContent><DialogHeader><DialogTitle>Update Inventory</DialogTitle></DialogHeader><div className="py-4"><label className="text-sm font-medium">Stock Count</label><Input type="number" defaultValue={product.stock} onChange={(e) => e.target.value && handleStockUpdate(product.id, parseInt(e.target.value))} /></div></DialogContent></Dialog></div></TableCell>
                            <TableCell><Badge variant={product.status === 'In Stock' ? 'default' : product.status === 'Low Stock' ? 'secondary' : 'destructive'} className={product.status === 'In Stock' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : ''}>{product.status}</Badge></TableCell>
                            <TableCell className="text-right">
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                        <DropdownMenuItem onClick={() => handleStockUpdate(product.id, product.stock)}>Update Stock</DropdownMenuItem>
                                        <DropdownMenuItem className="text-destructive" onClick={() => handleDeleteProduct(product.id)}>Delete Product</DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </TableCell></TableRow>
                    ))}</TableBody></Table>
            </div>
        </div>
    );
}

function OrdersTab() {
    const [orders, setOrders] = useState<Order[]>(MOCK_ORDERS);
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [categoryFilter, setCategoryFilter] = useState<string>('all');
    const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');
    const [deliveryFilter, setDeliveryFilter] = useState<string>('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

    // Filter orders by date range
    const filterByDateRange = useCallback((order: Order) => {
        if (dateRange === 'all') return true;
        const orderDate = new Date(order.createdAt);
        const now = new Date();
        const daysAgo = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
        const cutoff = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000);
        return orderDate >= cutoff;
    }, [dateRange]);

    // Filter orders by category (based on items)
    const filterByCategory = useCallback((order: Order) => {
        if (categoryFilter === 'all') return true;
        return order.items.some(item => 
            (item as any).category?.toLowerCase() === categoryFilter.toLowerCase()
        );
    }, [categoryFilter]);

    // Filter by delivery method
    const filterByDelivery = useCallback((order: Order) => {
        if (deliveryFilter === 'all') return true;
        return (order as any).delivery_method === deliveryFilter;
    }, [deliveryFilter]);

    const filteredOrders = orders.filter(o => {
        const matchesStatus = statusFilter === 'all' || o.status === statusFilter;
        const matchesSearch = o.orderNumber.toLowerCase().includes(searchTerm.toLowerCase()) || o.customer.name.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesDate = filterByDateRange(o);
        const matchesCategory = filterByCategory(o);
        const matchesDelivery = filterByDelivery(o);
        return matchesStatus && matchesSearch && matchesDate && matchesCategory && matchesDelivery;
    });

    // Calculate filtered totals
    const filteredTotals = useMemo(() => ({
        revenue: filteredOrders.reduce((sum, o) => sum + o.total, 0),
        orders: filteredOrders.length,
        avgOrder: filteredOrders.length > 0 
            ? filteredOrders.reduce((sum, o) => sum + o.total, 0) / filteredOrders.length 
            : 0,
    }), [filteredOrders]);

    const updateOrderStatus = (orderId: string, newStatus: OrderStatus) => {
        setOrders(orders.map(o => o.id === orderId ? { ...o, status: newStatus, updatedAt: new Date() } : o));
        toast.success("Order Updated", { description: `Status changed to ${newStatus}` });
    };

    const exportToCSV = useCallback(() => {
        const headers = [
            'Order Number',
            'Order ID',
            'Customer Name',
            'Customer Email',
            'Items',
            'Subtotal',
            'Shipping',
            'Tax',
            'Total',
            'Status',
            'Payment Status',
            'Delivery Method',
            'Created At',
            'Shipping Street',
            'Shipping City',
            'Shipping State',
            'Shipping Postal Code',
        ];

        const rows = filteredOrders.map(order => [
            order.orderNumber,
            order.id,
            order.customer.name,
            order.customer.email,
            order.items.map(i => `${i.productName} (${i.size}/${i.color} x${i.quantity})`).join('; '),
            order.subtotal.toFixed(2),
            order.shipping.toFixed(2),
            order.tax.toFixed(2),
            order.total.toFixed(2),
            order.status,
            (order as any).paymentStatus || 'paid',
            (order as any).delivery_method || 'shipping',
            new Date(order.createdAt).toISOString(),
            order.shippingAddress.street,
            order.shippingAddress.city,
            order.shippingAddress.state,
            order.shippingAddress.postalCode,
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')),
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `orders-export-${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success("Export Complete", { description: `${filteredOrders.length} orders exported to CSV` });
    }, [filteredOrders]);

    return (
        <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-card border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">Total Revenue</p>
                    <p className="text-2xl font-bold text-green-600">{formatCurrency(filteredTotals.revenue)}</p>
                </div>
                <div className="bg-card border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">Orders</p>
                    <p className="text-2xl font-bold">{filteredTotals.orders}</p>
                </div>
                <div className="bg-card border border-border rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">Avg. Order Value</p>
                    <p className="text-2xl font-bold">{formatCurrency(filteredTotals.avgOrder)}</p>
                </div>
            </div>

            <div className="flex flex-col sm:flex-row justify-between gap-4">
                <div className="flex flex-wrap items-center gap-2">
                    <div className="relative flex-1 sm:w-64"><Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" /><Input placeholder="Search orders..." className="pl-9" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} /></div>
                    <Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-[130px]"><SelectValue placeholder="Status" /></SelectTrigger><SelectContent><SelectItem value="all">All Status</SelectItem><SelectItem value="pending">Pending</SelectItem><SelectItem value="processing">Processing</SelectItem><SelectItem value="shipped">Shipped</SelectItem><SelectItem value="delivered">Delivered</SelectItem><SelectItem value="cancelled">Cancelled</SelectItem></SelectContent></Select>
                    <Select value={categoryFilter} onValueChange={setCategoryFilter}><SelectTrigger className="w-[130px]"><SelectValue placeholder="Category" /></SelectTrigger><SelectContent><SelectItem value="all">All Categories</SelectItem><SelectItem value="tops">Tops</SelectItem><SelectItem value="bottoms">Bottoms</SelectItem><SelectItem value="dresses">Dresses</SelectItem><SelectItem value="outerwear">Outerwear</SelectItem><SelectItem value="footwear">Footwear</SelectItem><SelectItem value="accessories">Accessories</SelectItem></SelectContent></Select>
                    <Select value={dateRange} onValueChange={(v) => setDateRange(v as any)}><SelectTrigger className="w-[110px]"><SelectValue placeholder="Period" /></SelectTrigger><SelectContent><SelectItem value="7d">Last 7 days</SelectItem><SelectItem value="30d">Last 30 days</SelectItem><SelectItem value="90d">Last 90 days</SelectItem><SelectItem value="all">All time</SelectItem></SelectContent></Select>
                    <Select value={deliveryFilter} onValueChange={setDeliveryFilter}><SelectTrigger className="w-[120px]"><SelectValue placeholder="Delivery" /></SelectTrigger><SelectContent><SelectItem value="all">All Methods</SelectItem><SelectItem value="shipping">Shipping</SelectItem><SelectItem value="pickup">Pickup</SelectItem></SelectContent></Select>
                </div>
                <Button variant="outline" onClick={exportToCSV}><Download className="h-4 w-4 mr-2" />Export CSV</Button>
            </div>
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <Table><TableHeader><TableRow><TableHead>Order</TableHead><TableHead>Customer</TableHead><TableHead>Items</TableHead><TableHead>Total</TableHead><TableHead>Status</TableHead><TableHead>Date</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                    <TableBody>{filteredOrders.map((order) => (
                        <TableRow key={order.id}><TableCell><p className="font-medium">{order.orderNumber}</p><p className="text-xs text-muted-foreground">{order.id}</p></TableCell>
                            <TableCell><div className="flex items-center gap-2"><Avatar className="h-8 w-8"><AvatarImage src={order.customer.avatar} /><AvatarFallback>{order.customer.name.split(' ').map(n => n[0]).join('')}</AvatarFallback></Avatar><div><p className="text-sm font-medium">{order.customer.name}</p><p className="text-xs text-muted-foreground">{order.customer.email}</p></div></div></TableCell>
                            <TableCell>{order.items.length} items</TableCell><TableCell className="font-medium">{formatCurrency(order.total)}</TableCell>
                            <TableCell><Badge className={getOrderStatusColor(order.status)}>{order.status}</Badge></TableCell>
                            <TableCell className="text-sm text-muted-foreground">{formatDateTime(order.createdAt)}</TableCell>
                            <TableCell className="text-right"><div className="flex items-center justify-end gap-1">
                                <Dialog><DialogTrigger asChild><Button variant="ghost" size="icon" onClick={() => setSelectedOrder(order)}><Eye className="h-4 w-4" /></Button></DialogTrigger>
                                    <DialogContent className="max-w-2xl"><DialogHeader><DialogTitle>Order {order.orderNumber}</DialogTitle><DialogDescription>Placed on {formatDateTime(order.createdAt)}</DialogDescription></DialogHeader>
                                        <div className="space-y-6 py-4">
                                            <div className="grid grid-cols-2 gap-4">
                                                <div><h4 className="font-medium mb-2">Customer</h4><p className="text-sm">{order.customer.name}</p><p className="text-sm text-muted-foreground">{order.customer.email}</p></div>
                                                <div><h4 className="font-medium mb-2">Shipping Address</h4><p className="text-sm">{order.shippingAddress.street}</p><p className="text-sm text-muted-foreground">{order.shippingAddress.city}, {order.shippingAddress.state} {order.shippingAddress.postalCode}</p></div>
                                            </div>
                                            <div><h4 className="font-medium mb-2">Items</h4>
                                                <div className="space-y-2">{order.items.map((item) => (<div key={item.id} className="flex items-center gap-3 p-2 bg-muted/40 rounded-lg"><img src={item.productImage} alt={item.productName} className="w-12 h-12 object-cover rounded" /><div className="flex-1"><p className="text-sm font-medium">{item.productName}</p><p className="text-xs text-muted-foreground">{item.size} / {item.color} × {item.quantity}</p></div><p className="font-medium">{formatCurrency(item.totalPrice)}</p></div>))}</div></div>
                                            <div className="border-t pt-4"><div className="flex justify-between mb-2"><span className="text-muted-foreground">Subtotal</span><span>{formatCurrency(order.subtotal)}</span></div><div className="flex justify-between mb-2"><span className="text-muted-foreground">Shipping</span><span>{formatCurrency(order.shipping)}</span></div><div className="flex justify-between mb-2"><span className="text-muted-foreground">Tax</span><span>{formatCurrency(order.tax)}</span></div><div className="flex justify-between font-bold text-lg"><span>Total</span><span>{formatCurrency(order.total)}</span></div></div>
                                        </div>
                                        <DialogFooter><Select value={order.status} onValueChange={(v) => updateOrderStatus(order.id, v as OrderStatus)}><SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="pending">Pending</SelectItem><SelectItem value="confirmed">Confirmed</SelectItem><SelectItem value="processing">Processing</SelectItem><SelectItem value="shipped">Shipped</SelectItem><SelectItem value="delivered">Delivered</SelectItem></SelectContent></Select></DialogFooter></DialogContent></Dialog>
                                <Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button></div></TableCell></TableRow>
                    ))}</TableBody></Table>
            </div>
        </div>
    );
}


function AnalyticsTab() {
    const [analytics, setAnalytics] = useState<any>(null);
    const [advice, setAdvice] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
    const [refreshing, setRefreshing] = useState(false);

    // Generate comprehensive mock data
    const generateMockData = useCallback(() => {
        const now = new Date();
        const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
        const dailyData = [];
        
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            const dayOfWeek = date.getDay();
            const weekendMultiplier = (dayOfWeek === 0 || dayOfWeek === 6) ? 1.3 : 1;
            const baseSales = 50 + Math.random() * 30;
            const sales = Math.floor(baseSales * weekendMultiplier);
            const revenue = sales * (80 + Math.random() * 120);
            const users = Math.floor(sales * (2.5 + Math.random()));
            
            dailyData.push({
                name: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                revenue: Math.floor(revenue),
                orders: sales,
                users: Math.floor(users),
                costs: Math.floor(revenue * 0.4 + Math.random() * 500)
            });
        }

        return {
            total_revenue: 284750,
            total_costs: 142000,
            net_profit: 142750,
            is_profitable: true,
            profit_margin: 50.1,
            total_orders: 3420,
            total_users: 15420,
            conversion_rate: 7.5,
            avg_order_value: 83.2,
            monthly_data: dailyData,
            category_data: [
                { category: 'Tops', sales: 1250, percentage: 36.5, revenue: 100000 },
                { category: 'Bottoms', sales: 890, percentage: 26.0, revenue: 71200 },
                { category: 'Dresses', sales: 680, percentage: 19.9, revenue: 54400 },
                { category: 'Outerwear', sales: 420, percentage: 12.3, revenue: 33600 },
                { category: 'Accessories', sales: 180, percentage: 5.3, revenue: 14400 }
            ],
            gender_data: [
                { gender: 'Women', count: 8900, percentage: 57.7 },
                { gender: 'Men', count: 6520, percentage: 42.3 }
            ],
            top_products: [
                { name: 'Classic White T-Shirt', sales: 245, revenue: 19600, trend: 'up' },
                { name: 'Slim Fit Jeans', sales: 189, revenue: 20790, trend: 'up' },
                { name: 'Summer Dress', sales: 167, revenue: 23380, trend: 'down' },
                { name: 'Leather Jacket', sales: 143, revenue: 28600, trend: 'up' },
                { name: 'Casual Sneakers', sales: 128, revenue: 15360, trend: 'up' }
            ]
        };
    }, [timeRange]);

    useEffect(() => {
        const fetchAnalytics = async () => {
            try {
                const token = localStorage.getItem('confit_token');
                // Show mock data immediately
                setAnalytics(generateMockData());
                setAdvice([
                    { type: 'success', title: 'Revenue Growth', content: 'Your revenue increased by 12.5% compared to last month. Keep up the great work!' },
                    { type: 'info', title: 'Inventory Alert', content: 'Consider restocking "Flex Yoga Leggings" - only 45 units left.' },
                    { type: 'warning', title: 'Conversion Opportunity', content: 'Your cart abandonment rate is 68%. Consider adding exit-intent popups.' }
                ]);
                setIsLoading(false);

                // Try to fetch real data from backend
                let brandId = DEFAULT_BRAND_ID;
                try {
                    const brandsRes = await fetch(apiUrl('/api/brands/'), { 
                        headers: token ? { Authorization: `Bearer ${token}` } : {} 
                    });
                    if (brandsRes.ok) {
                        const brands = await brandsRes.json();
                        if (Array.isArray(brands) && brands.length > 0 && brands[0].id) {
                            brandId = brands[0].id;
                        }
                    }
                } catch (e) {
                    console.log('Using mock brand data');
                }

                // Fetch Analytics
                try {
                    const resAn = await fetch(apiUrl(`/api/brands/${brandId}/analytics`), { 
                        headers: token ? { Authorization: `Bearer ${token}` } : {} 
                    });
                    if (resAn.ok) {
                        const data = await resAn.json();
                        setAnalytics(prev => ({ ...prev, ...data }));
                    }
                } catch (e) {
                    console.log('Using mock analytics data');
                }

                // Fetch AI Advice
                try {
                    const resAdv = await fetch(apiUrl(`/api/brands/${brandId}/advice`), { 
                        headers: token ? { Authorization: `Bearer ${token}` } : {} 
                    });
                    if (resAdv.ok) {
                        const data = await resAdv.json();
                        if (Array.isArray(data) && data.length > 0) {
                            setAdvice(data);
                        }
                    }
                } catch (e) {
                    console.log('Using mock advice data');
                }
            } catch (e) {
                console.error("Failed to fetch brand data", e);
            } finally {
                setIsLoading(false);
            }
        };
        fetchAnalytics();
    }, [generateMockData]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        await new Promise(resolve => setTimeout(resolve, 1000));
        setAnalytics(generateMockData());
        setRefreshing(false);
    }, [generateMockData]);

    // Colors for charts
    const CHART_COLORS = ['#8b5cf6', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];

    // Animation variants
    const cardVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } }
    };

    // Data is shown immediately from mock, no loading screen needed
    if (!analytics) return <div className="p-8 text-center">Failed to load data.</div>;

    return (
        <div className="space-y-6">
            {/* Header with Time Range Selector */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Analytics Dashboard</h2>
                <div className="flex items-center gap-3">
                    <div className="flex gap-1 p-1 bg-muted rounded-lg">
                        {(['7d', '30d', '90d'] as const).map((range) => (
                            <Button
                                key={range}
                                variant={timeRange === range ? 'default' : 'ghost'}
                                size="sm"
                                onClick={() => setTimeRange(range)}
                                className="h-8"
                            >
                                {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : '90 Days'}
                            </Button>
                        ))}
                    </div>
                    <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
                        <motion.div
                            animate={refreshing ? { rotate: 360 } : { rotate: 0 }}
                            transition={createTransition({ duration: 1, repeat: refreshing ? Infinity : 0, ease: "linear" })}
                        >
                            <RefreshCw className="h-4 w-4" />
                        </motion.div>
                    </Button>
                </div>
            </div>

            {/* KPI Cards with Animations */}
            <motion.div 
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
            >
                {[
                    { title: "Total Revenue", value: formatCurrency(analytics.total_revenue), change: "+12.5%", icon: DollarSign, positive: true },
                    { title: "Net Profit", value: formatCurrency(analytics.net_profit), change: `${analytics.profit_margin}% Margin`, icon: TrendingUp, positive: analytics.net_profit > 0 },
                    { title: "Total Orders", value: analytics.total_orders?.toLocaleString() || "3,420", change: "+15.3%", icon: ShoppingBag, positive: true },
                    { title: "Total Users", value: analytics.total_users?.toLocaleString() || "15,420", change: "+8.2%", icon: Users, positive: true },
                    { title: "Conversion Rate", value: `${analytics.conversion_rate || 7.5}%`, change: "+0.8%", icon: BarChart3, positive: true },
                    { title: "Avg Order Value", value: formatCurrency(analytics.avg_order_value || 83.2), change: "+3.4%", icon: Package, positive: true },
                    { title: "Total Costs", value: formatCurrency(analytics.total_costs), change: "Operational", icon: CreditCard, positive: false },
                    { title: "Profit Status", value: analytics.is_profitable ? "Profitable" : "Loss", change: analytics.is_profitable ? "Healthy" : "Attention", icon: TrendingUp, positive: analytics.is_profitable }
                ].map((stat, index) => (
                    <motion.div
                        key={stat.title}
                        variants={cardVariants}
                        transition={createTransition({ delay: index * 0.05 })}
                    >
                        <Card className="hover:shadow-lg transition-shadow duration-300">
                            <CardContent className="p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <stat.icon className="h-4 w-4 text-muted-foreground" />
                                    <Badge variant={stat.positive ? 'default' : 'secondary'} className="text-xs">
                                        {stat.positive ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
                                        {stat.change}
                                    </Badge>
                                </div>
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    transition={createTransition({ duration: 0.3, delay: index * 0.05 })}
                                >
                                    <div className="text-xl font-bold">{stat.value}</div>
                                    <div className="text-xs text-muted-foreground">{stat.title}</div>
                                </motion.div>
                            </CardContent>
                        </Card>
                    </motion.div>
                ))}
            </motion.div>

            {/* Charts Row 1 */}
            <motion.div 
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                transition={createTransition({ delay: 0.2 })}
                className="grid grid-cols-1 lg:grid-cols-2 gap-6"
            >
                {/* Revenue & Orders Trend */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <TrendingUp className="h-5 w-5" />
                            Revenue & Orders Trend
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <AreaChart data={analytics.monthly_data}>
                                <defs>
                                    <linearGradient id="colorRevenue2" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1}/>
                                    </linearGradient>
                                    <linearGradient id="colorOrders2" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                                <YAxis yAxisId="left" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => `$${v/1000}k`} />
                                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                                <Area yAxisId="left" type="monotone" dataKey="revenue" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue2)" animationDuration={1500} />
                                <Area yAxisId="right" type="monotone" dataKey="orders" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorOrders2)" animationDuration={1500} animationBegin={200} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Sales by Category */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <Package className="h-5 w-5" />
                            Sales by Category
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={analytics.category_data}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ category, percentage }) => `${category} ${percentage.toFixed(1)}%`}
                                    outerRadius={80}
                                    dataKey="sales"
                                    animationDuration={1500}
                                >
                                    {analytics.category_data.map((_: any, index: number) => (
                                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                            </PieChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>
            </motion.div>

            {/* Charts Row 2 */}
            <motion.div 
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                transition={createTransition({ delay: 0.3 })}
                className="grid grid-cols-1 lg:grid-cols-2 gap-6"
            >
                {/* Customer Demographics */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <Users className="h-5 w-5" />
                            Customer Demographics
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={analytics.gender_data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                <XAxis dataKey="gender" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                                <YAxis tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                                <Bar dataKey="count" fill="#8b5cf6" radius={[8, 8, 0, 0]} animationDuration={1500} animationBegin={400} />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Top Performing Products */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <TrendingUp className="h-5 w-5" />
                            Top Performing Products
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {analytics.top_products.map((product: any, index: number) => (
                                <motion.div
                                    key={product.name}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={createTransition({ delay: 0.4 + index * 0.1 })}
                                    className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition-colors"
                                >
                                    <div className="flex-1">
                                        <div className="font-medium text-sm">{product.name}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {product.sales} sold • {formatCurrency(product.revenue)}
                                        </div>
                                    </div>
                                    <Badge variant={product.trend === 'up' ? 'default' : 'secondary'} className="text-xs">
                                        {product.trend === 'up' ? <ArrowUpRight className="h-3 w-3 mr-1" /> : <ArrowDownRight className="h-3 w-3 mr-1" />}
                                        {product.trend === 'up' ? '+' : '-'}{Math.floor(Math.random() * 20 + 5)}%
                                    </Badge>
                                </motion.div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </motion.div>

            {/* AI Business Advisor */}
            <motion.div 
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                transition={createTransition({ delay: 0.4 })}
            >
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <Megaphone className="h-5 w-5 text-accent" /> AI Business Advisor
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {advice.map((item, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={createTransition({ delay: 0.5 + i * 0.1 })}
                                    className={cn("p-4 rounded-lg border",
                                        item.type === 'critical' ? "bg-red-50 border-red-200 dark:bg-red-900/10" :
                                            item.type === 'warning' ? "bg-yellow-50 border-yellow-200 dark:bg-yellow-900/10" :
                                                item.type === 'success' ? "bg-green-50 border-green-200 dark:bg-green-900/10" :
                                                    "bg-blue-50 border-blue-200 dark:bg-blue-900/10"
                                    )}
                                >
                                    <h4 className={cn("font-semibold mb-1 text-sm",
                                        item.type === 'critical' ? "text-red-700 dark:text-red-400" :
                                            item.type === 'warning' ? "text-yellow-700 dark:text-yellow-400" :
                                                item.type === 'success' ? "text-green-700 dark:text-green-400" :
                                                    "text-blue-700 dark:text-blue-400"
                                    )}>{item.title}</h4>
                                    <p className="text-xs text-muted-foreground">{item.content}</p>
                                </motion.div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </motion.div>
        </div>
    );
}

function CampaignsTab() {
    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center"><h2 className="text-xl font-semibold">Sponsored Placements</h2>
                <Dialog><DialogTrigger asChild><Button variant="hero"><Megaphone className="h-4 w-4 mr-2" />Create Campaign</Button></DialogTrigger>
                    <DialogContent><DialogHeader><DialogTitle>Boost a Product</DialogTitle><DialogDescription>Select a product to promote.</DialogDescription></DialogHeader>
                        <div className="space-y-4 py-4"><div className="space-y-2"><label htmlFor="product-select" className="text-sm font-medium">Select Product</label><select id="product-select" className="w-full p-2 border rounded-md bg-background">{MOCK_PRODUCTS.map(p => <option key={p.id}>{p.name}</option>)}</select></div><div className="space-y-2"><label className="text-sm font-medium">Daily Budget</label><Input type="number" placeholder="$50.00" /></div></div>
                        <DialogFooter><Button onClick={() => toast.success("Campaign Created")}>Launch Campaign</Button></DialogFooter></DialogContent></Dialog></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">{CAMPAIGNS.map((campaign) => (
                <div key={campaign.id} className="bg-card border border-border rounded-xl p-6 space-y-4">
                    <div className="flex justify-between items-start"><div><h3 className="font-semibold">{campaign.name}</h3><Badge variant="outline" className={campaign.status === 'Active' ? 'text-green-600 border-green-200 bg-green-50' : ''}>{campaign.status}</Badge></div><div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center"><TrendingUp className="h-4 w-4" /></div></div>
                    <div className="grid grid-cols-2 gap-4 text-sm"><div><p className="text-muted-foreground">Budget</p><p className="font-medium">{campaign.budget}</p></div><div><p className="text-muted-foreground">Spent</p><p className="font-medium">{campaign.spent}</p></div><div><p className="text-muted-foreground">Clicks</p><p className="font-medium">{campaign.clicks}</p></div></div>
                    <div className="w-full bg-muted rounded-full h-2 overflow-hidden"><div className="bg-accent h-full progress-bar-45" /></div></div>))}</div>
        </div>
    );
}

function TeamTab() {
    const [members, setMembers] = useState<TeamMember[]>(MOCK_TEAM_MEMBERS);
    const [isInviteOpen, setIsInviteOpen] = useState(false);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center"><h2 className="text-xl font-semibold">Team Members</h2><Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}><DialogTrigger asChild><Button variant="hero"><UserPlus className="h-4 w-4 mr-2" />Invite Member</Button></DialogTrigger>
                <DialogContent><DialogHeader><DialogTitle>Invite Team Member</DialogTitle></DialogHeader>
                    <div className="space-y-4 py-4"><div className="space-y-2"><label className="text-sm font-medium">Email Address</label><Input type="email" placeholder="colleague@company.com" /></div><div className="space-y-2"><label className="text-sm font-medium">Role</label><Select defaultValue="staff"><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="admin">Admin</SelectItem><SelectItem value="manager">Manager</SelectItem><SelectItem value="staff">Staff</SelectItem><SelectItem value="viewer">Viewer</SelectItem></SelectContent></Select></div></div>
                    <DialogFooter><Button onClick={() => { toast.success("Invitation Sent"); setIsInviteOpen(false); }}>Send Invite</Button></DialogFooter></DialogContent></Dialog></div>
            <div className="grid gap-4">{members.map((member) => (
                <div key={member.id} className="bg-card border border-border rounded-xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4"><Avatar className="h-12 w-12"><AvatarImage src={member.avatar} /><AvatarFallback>{member.name.split(' ').map(n => n[0]).join('')}</AvatarFallback></Avatar><div><p className="font-medium">{member.name}</p><p className="text-sm text-muted-foreground">{member.email}</p></div></div>
                    <div className="flex items-center gap-4"><Badge className={getRoleColor(member.role)}>{member.role}</Badge>{member.lastActive && <span className="text-xs text-muted-foreground">{getRelativeTime(member.lastActive)}</span>}<Button variant="ghost" size="icon"><MoreHorizontal className="h-4 w-4" /></Button></div></div>))}</div>
            <div className="bg-card border border-border rounded-xl p-6"><h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
                <div className="space-y-4">{MOCK_ACTIVITY_LOGS.slice(0, 5).map((log) => (
                    <div key={log.id} className="flex items-start gap-3"><Avatar className="h-8 w-8"><AvatarImage src={log.userAvatar} /><AvatarFallback>{log.userName.split(' ').map(n => n[0]).join('')}</AvatarFallback></Avatar>
                        <div className="flex-1"><p className="text-sm"><span className="font-medium">{log.userName}</span> {log.action} {log.resourceName && <span className="font-medium">{log.resourceName}</span>}</p>{log.details && <p className="text-xs text-muted-foreground">{log.details}</p>}<p className="text-xs text-muted-foreground mt-1">{getRelativeTime(log.createdAt)}</p></div></div>))}</div></div>
        </div>
    );
}

function SettingsTab() {
    const [brand, setBrand] = useState(MOCK_BRAND);

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-semibold">Brand Settings</h2>
            <div className="grid gap-6">
                <div className="bg-card border border-border rounded-xl p-6"><h3 className="font-semibold mb-4 flex items-center gap-2"><Building2 className="h-4 w-4" />Brand Profile</h3>
                    <div className="grid md:grid-cols-2 gap-4"><div className="space-y-2"><label className="text-sm font-medium">Brand Name</label><Input defaultValue={brand.name} /></div><div className="space-y-2"><label className="text-sm font-medium">Website</label><Input defaultValue={brand.website} /></div><div className="col-span-2 space-y-2"><label className="text-sm font-medium">Description</label><Textarea defaultValue={brand.description} /></div></div></div>
                <div className="bg-card border border-border rounded-xl p-6"><h3 className="font-semibold mb-4 flex items-center gap-2"><Mail className="h-4 w-4" />Contact Information</h3>
                    <div className="grid md:grid-cols-2 gap-4"><div className="space-y-2"><label className="text-sm font-medium">Email</label><Input defaultValue={brand.email} /></div><div className="space-y-2"><label className="text-sm font-medium">Phone</label><Input defaultValue={brand.phone} /></div></div></div>
                <div className="bg-card border border-border rounded-xl p-6"><h3 className="font-semibold mb-4 flex items-center gap-2"><Bell className="h-4 w-4" />Notifications</h3>
                    <div className="space-y-4">{[{ label: 'Order Alerts', key: 'orderAlerts' }, { label: 'Low Stock Alerts', key: 'lowStockAlerts' }, { label: 'Review Alerts', key: 'reviewAlerts' }].map((item) => (<div key={item.key} className="flex items-center justify-between"><span className="text-sm">{item.label}</span><Switch defaultChecked={(brand.settings.notifications as Record<string, boolean>)[item.key]} /></div>))}</div></div>
                <div className="bg-card border border-border rounded-xl p-6"><h3 className="font-semibold mb-4 flex items-center gap-2"><CreditCard className="h-4 w-4" />Payment Settings</h3>
                    <div className="grid md:grid-cols-2 gap-4"><div className="space-y-2"><label className="text-sm font-medium">Payout Method</label><Select defaultValue={brand.settings.payoutMethod}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="bank_transfer">Bank Transfer</SelectItem><SelectItem value="paypal">PayPal</SelectItem><SelectItem value="stripe">Stripe</SelectItem></SelectContent></Select></div><div className="space-y-2"><label className="text-sm font-medium">Minimum Payout</label><Input type="number" defaultValue={brand.settings.minimumPayout} /></div></div></div>
                <Button onClick={() => toast.success("Settings Saved")} className="w-full">Save Changes</Button>
            </div>
        </div>
    );
}

// Main Component
export default function BrandDashboard() {
    return (
        <MainLayout>
            <div className="flex min-h-screen bg-muted/20">
                <main className="flex-1 p-4 lg:p-8 overflow-y-auto">
                    <Tabs defaultValue="overview" className="flex flex-col lg:flex-row w-full gap-8">
                        <TabsList className="hidden lg:flex flex-col w-64 h-auto bg-card border border-border p-4 gap-1 shrink-0 rounded-xl items-stretch self-start sticky top-24">
                            <div className="mb-4 px-2"><h2 className="text-lg font-bold font-display">Brand Portal</h2><p className="text-xs text-muted-foreground">Admin Workspace</p></div>
                            {[{ id: 'overview', label: 'Overview', icon: LayoutDashboard }, { id: 'products', label: 'Products', icon: Package }, { id: 'orders', label: 'Orders', icon: Truck }, { id: 'sold', label: 'Sold Products', icon: DollarSign }, { id: 'analytics', label: 'Analytics', icon: BarChart3 }, { id: 'sostac', label: 'SOSTAC', icon: Target }, { id: 'campaigns', label: 'Campaigns', icon: Megaphone }, { id: 'team', label: 'Team', icon: Users }, { id: 'settings', label: 'Settings', icon: Settings }].map((item) => (
                                <TabsTrigger key={item.id} value={item.id} className="justify-start gap-3"><item.icon className="h-4 w-4" />{item.label}</TabsTrigger>
                            ))}
                        </TabsList>
                        <TabsList className="lg:hidden w-full overflow-x-auto justify-start mb-6"><TabsTrigger value="overview">Overview</TabsTrigger><TabsTrigger value="products">Products</TabsTrigger><TabsTrigger value="orders">Orders</TabsTrigger><TabsTrigger value="sold">Sold</TabsTrigger><TabsTrigger value="analytics">Analytics</TabsTrigger><TabsTrigger value="sostac">SOSTAC</TabsTrigger><TabsTrigger value="campaigns">Campaigns</TabsTrigger><TabsTrigger value="team">Team</TabsTrigger><TabsTrigger value="settings">Settings</TabsTrigger></TabsList>
                        <div className="flex-1 min-w-0 space-y-6">
                            <TabsContent value="overview" className="mt-0"><div className="flex items-center justify-between mb-6"><h1 className="text-3xl font-display font-semibold">Dashboard Overview</h1><Button>Export Report</Button></div><OverviewTab /></TabsContent>
                            <TabsContent value="products" className="mt-0"><div className="flex items-center justify-between mb-6"><h1 className="text-3xl font-display font-semibold">Inventory Management</h1></div><ProductsTab /></TabsContent>
                            <TabsContent value="orders" className="mt-0"><div className="flex items-center justify-between mb-6"><h1 className="text-3xl font-display font-semibold">Order Management</h1></div><OrdersTab /></TabsContent>
                            <TabsContent value="sold" className="mt-0"><div className="flex items-center justify-between mb-6"><h1 className="text-3xl font-display font-semibold">Sold Products</h1></div><SoldProductsTable /></TabsContent>
                            <TabsContent value="analytics" className="mt-0"><AnalyticsTab /></TabsContent>
                            <TabsContent value="sostac" className="mt-0"><div className="flex items-center justify-between mb-6"><h1 className="text-3xl font-display font-semibold">Marketing Plan (SOSTAC)</h1></div><SOSTACPanel /></TabsContent>
                            <TabsContent value="campaigns" className="mt-0"><CampaignsTab /></TabsContent>
                            <TabsContent value="team" className="mt-0"><TeamTab /></TabsContent>
                            <TabsContent value="settings" className="mt-0"><SettingsTab /></TabsContent>
                        </div>
                    </Tabs>
                </main>
            </div>
        </MainLayout>
    );
}
