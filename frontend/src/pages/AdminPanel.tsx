import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Users,
  ShoppingBag,
  DollarSign,
  Package,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Settings,
  Bell,
  Search,
  Filter,
  Download,
  MoreHorizontal,
  Eye,
  Ban,
  CheckCircle,
  Clock,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { PageTransition, StaggerContainer, StaggerItem, transitionHero } from '@/motion';
import { DashboardStatsSkeleton, TableSkeleton } from '@/components/loading';
import { useQuery } from '@tanstack/react-query';

// Mock data for admin dashboard
const mockStats = {
  totalUsers: 12847,
  activeUsers: 3421,
  totalOrders: 8923,
  totalRevenue: 1247832,
  totalProducts: 4521,
  totalBrands: 89,
  pendingApprovals: 23,
  reportedIssues: 7,
};

const mockUsers = [
  { id: '1', name: 'Emma Wilson', email: 'emma@example.com', role: 'user', status: 'active', orders: 12, spent: 2847, joined: '2024-01-15' },
  { id: '2', name: 'James Chen', email: 'james@example.com', role: 'brand', status: 'active', orders: 0, spent: 0, joined: '2023-11-20' },
  { id: '3', name: 'Sophie Martin', email: 'sophie@example.com', role: 'user', status: 'suspended', orders: 8, spent: 1523, joined: '2024-02-10' },
  { id: '4', name: 'Oliver Brown', email: 'oliver@example.com', role: 'admin', status: 'active', orders: 0, spent: 0, joined: '2023-06-01' },
  { id: '5', name: 'Isabella Davis', email: 'isabella@example.com', role: 'user', status: 'pending', orders: 3, spent: 892, joined: '2024-03-05' },
];

const mockOrders = [
  { id: 'ORD-001', customer: 'Emma Wilson', brand: 'Gucci', total: 2450, status: 'delivered', date: '2024-03-10', items: 3 },
  { id: 'ORD-002', customer: 'James Chen', brand: 'Prada', total: 1890, status: 'shipped', date: '2024-03-12', items: 2 },
  { id: 'ORD-003', customer: 'Sophie Martin', brand: 'Versace', total: 3200, status: 'processing', date: '2024-03-14', items: 4 },
  { id: 'ORD-004', customer: 'Oliver Brown', brand: 'Dior', total: 980, status: 'pending', date: '2024-03-15', items: 1 },
  { id: 'ORD-005', customer: 'Isabella Davis', brand: 'Chanel', total: 4500, status: 'cancelled', date: '2024-03-16', items: 2 },
];

const mockReports = [
  { id: '1', type: 'product', reason: 'Counterfeit suspicion', status: 'pending', reportedBy: 'user_123', date: '2024-03-14' },
  { id: '2', type: 'user', reason: 'Suspicious activity', status: 'reviewed', reportedBy: 'system', date: '2024-03-13' },
  { id: '3', type: 'brand', reason: 'Policy violation', status: 'pending', reportedBy: 'admin_456', date: '2024-03-12' },
];

const mockRevenueData = [
  { month: 'Jan', revenue: 98000, orders: 234 },
  { month: 'Feb', revenue: 125000, orders: 312 },
  { month: 'Mar', revenue: 142000, orders: 356 },
  { month: 'Apr', revenue: 118000, orders: 289 },
  { month: 'May', revenue: 156000, orders: 398 },
  { month: 'Jun', revenue: 189000, orders: 445 },
];

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [userFilter, setUserFilter] = useState('all');
  const [orderFilter, setOrderFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return mockStats;
    },
  });

  const StatCard = ({ title, value, change, icon: Icon, trend }: {
    title: string;
    value: string | number;
    change?: number;
    icon: typeof Users;
    trend?: 'up' | 'down';
  }) => (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {change !== undefined && (
          <div className={`flex items-center text-xs ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
            {trend === 'up' ? <TrendingUp className="mr-1 h-3 w-3" /> : <TrendingDown className="mr-1 h-3 w-3" />}
            {change}% from last month
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <PageTransition>
      <div className="min-h-screen bg-background">
        {/* Header */}
        <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container flex h-16 items-center justify-between px-4">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-bold">Admin Panel</h1>
              <Badge variant="secondary">CONFIT</Badge>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-64 pl-9"
                />
              </div>
              <Button variant="ghost" size="icon">
                <Bell className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon">
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="container px-4 py-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-6">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="users">Users</TabsTrigger>
              <TabsTrigger value="orders">Orders</TabsTrigger>
              <TabsTrigger value="products">Products</TabsTrigger>
              <TabsTrigger value="reports">Reports</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview">
              <StaggerContainer className="space-y-6">
                {/* Stats Grid */}
                <StaggerItem>
                  {statsLoading ? (
                    <DashboardStatsSkeleton />
                  ) : (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      <StatCard
                        title="Total Users"
                        value={stats?.totalUsers.toLocaleString() || 0}
                        change={12.5}
                        icon={Users}
                        trend="up"
                      />
                      <StatCard
                        title="Total Revenue"
                        value={`$${(stats?.totalRevenue || 0).toLocaleString()}`}
                        change={8.2}
                        icon={DollarSign}
                        trend="up"
                      />
                      <StatCard
                        title="Total Orders"
                        value={stats?.totalOrders.toLocaleString() || 0}
                        change={-2.4}
                        icon={ShoppingBag}
                        trend="down"
                      />
                      <StatCard
                        title="Active Users"
                        value={stats?.activeUsers.toLocaleString() || 0}
                        change={15.3}
                        icon={TrendingUp}
                        trend="up"
                      />
                    </div>
                  )}
                </StaggerItem>

                {/* Charts Row */}
                <StaggerItem>
                  <div className="grid gap-6 lg:grid-cols-2">
                    {/* Revenue Chart */}
                    <Card>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle>Revenue Overview</CardTitle>
                          <Button variant="ghost" size="sm">
                            <Download className="mr-2 h-4 w-4" />
                            Export
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="h-64">
                          {/* Simple bar chart visualization */}
                          <div className="flex h-full items-end gap-2">
                            {mockRevenueData.map((data) => (
                              <div key={data.month} className="flex flex-1 flex-col items-center gap-2">
                                <motion.div
                                  className="w-full rounded-t bg-primary transition-all hover:bg-primary/80"
                                  initial={{ height: '0%' }}
                                  animate={{ height: `${(data.revenue / 200000) * 100}%` }}
                                  transition={transitionHero}
                                />
                                <span className="text-xs text-muted-foreground">{data.month}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Quick Stats */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Quick Stats</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Package className="h-4 w-4 text-muted-foreground" />
                            <span>Total Products</span>
                          </div>
                          <span className="font-semibold">{stats?.totalProducts.toLocaleString()}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Users className="h-4 w-4 text-muted-foreground" />
                            <span>Total Brands</span>
                          </div>
                          <span className="font-semibold">{stats?.totalBrands}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-amber-500" />
                            <span>Pending Approvals</span>
                          </div>
                          <Badge variant="secondary">{stats?.pendingApprovals}</Badge>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-red-500" />
                            <span>Reported Issues</span>
                          </div>
                          <Badge variant="destructive">{stats?.reportedIssues}</Badge>
                        </div>

                        {/* Conversion Rate */}
                        <div className="space-y-2 pt-4">
                          <div className="flex justify-between text-sm">
                            <span>Conversion Rate</span>
                            <span className="font-semibold">3.2%</span>
                          </div>
                          <Progress value={32} />
                        </div>

                        {/* Customer Satisfaction */}
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Customer Satisfaction</span>
                            <span className="font-semibold">94%</span>
                          </div>
                          <Progress value={94} />
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </StaggerItem>

                {/* Recent Activity */}
                <StaggerItem>
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle>Recent Orders</CardTitle>
                        <Button variant="ghost" size="sm" onClick={() => setActiveTab('orders')}>
                          View All
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Order ID</TableHead>
                            <TableHead>Customer</TableHead>
                            <TableHead>Brand</TableHead>
                            <TableHead>Total</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Date</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {mockOrders.slice(0, 5).map((order) => (
                            <TableRow key={order.id}>
                              <TableCell className="font-medium">{order.id}</TableCell>
                              <TableCell>{order.customer}</TableCell>
                              <TableCell>{order.brand}</TableCell>
                              <TableCell>${order.total.toLocaleString()}</TableCell>
                              <TableCell>
                                <Badge
                                  variant={
                                    order.status === 'delivered'
                                      ? 'default'
                                      : order.status === 'shipped'
                                      ? 'secondary'
                                      : order.status === 'cancelled'
                                      ? 'destructive'
                                      : 'outline'
                                  }
                                >
                                  {order.status}
                                </Badge>
                              </TableCell>
                              <TableCell>{order.date}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </StaggerItem>
              </StaggerContainer>
            </TabsContent>

            {/* Users Tab */}
            <TabsContent value="users">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>User Management</CardTitle>
                    <div className="flex items-center gap-2">
                      <Select value={userFilter} onValueChange={setUserFilter}>
                        <SelectTrigger className="w-32">
                          <SelectValue placeholder="Filter" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Users</SelectItem>
                          <SelectItem value="active">Active</SelectItem>
                          <SelectItem value="suspended">Suspended</SelectItem>
                          <SelectItem value="pending">Pending</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button variant="outline" size="sm">
                        <Filter className="mr-2 h-4 w-4" />
                        Filter
                      </Button>
                      <Button variant="outline" size="sm">
                        <Download className="mr-2 h-4 w-4" />
                        Export
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>User</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Orders</TableHead>
                        <TableHead>Total Spent</TableHead>
                        <TableHead>Joined</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mockUsers.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Avatar className="h-8 w-8">
                                <AvatarImage src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user.email}`} />
                                <AvatarFallback>{user.name.charAt(0)}</AvatarFallback>
                              </Avatar>
                              <span className="font-medium">{user.name}</span>
                            </div>
                          </TableCell>
                          <TableCell>{user.email}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="capitalize">
                              {user.role}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                user.status === 'active'
                                  ? 'default'
                                  : user.status === 'suspended'
                                  ? 'destructive'
                                  : 'secondary'
                              }
                            >
                              {user.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{user.orders}</TableCell>
                          <TableCell>${user.spent.toLocaleString()}</TableCell>
                          <TableCell>{user.joined}</TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem>
                                  <Eye className="mr-2 h-4 w-4" />
                                  View Details
                                </DropdownMenuItem>
                                <DropdownMenuItem>
                                  <Ban className="mr-2 h-4 w-4" />
                                  Suspend User
                                </DropdownMenuItem>
                                <DropdownMenuItem>
                                  <CheckCircle className="mr-2 h-4 w-4" />
                                  Activate User
                                </DropdownMenuItem>
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

            {/* Orders Tab */}
            <TabsContent value="orders">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Order Management</CardTitle>
                    <div className="flex items-center gap-2">
                      <Select value={orderFilter} onValueChange={setOrderFilter}>
                        <SelectTrigger className="w-32">
                          <SelectValue placeholder="Status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Status</SelectItem>
                          <SelectItem value="pending">Pending</SelectItem>
                          <SelectItem value="processing">Processing</SelectItem>
                          <SelectItem value="shipped">Shipped</SelectItem>
                          <SelectItem value="delivered">Delivered</SelectItem>
                          <SelectItem value="cancelled">Cancelled</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button variant="outline" size="sm">
                        <Download className="mr-2 h-4 w-4" />
                        Export
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Order ID</TableHead>
                        <TableHead>Customer</TableHead>
                        <TableHead>Brand</TableHead>
                        <TableHead>Items</TableHead>
                        <TableHead>Total</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mockOrders.map((order) => (
                        <TableRow key={order.id}>
                          <TableCell className="font-medium">{order.id}</TableCell>
                          <TableCell>{order.customer}</TableCell>
                          <TableCell>{order.brand}</TableCell>
                          <TableCell>{order.items}</TableCell>
                          <TableCell>${order.total.toLocaleString()}</TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                order.status === 'delivered'
                                  ? 'default'
                                  : order.status === 'shipped'
                                  ? 'secondary'
                                  : order.status === 'cancelled'
                                  ? 'destructive'
                                  : 'outline'
                              }
                            >
                              {order.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{order.date}</TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm">
                              <Eye className="mr-2 h-4 w-4" />
                              View
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Products Tab */}
            <TabsContent value="products">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Product Management</CardTitle>
                    <Button variant="outline" size="sm">
                      <Download className="mr-2 h-4 w-4" />
                      Export
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex h-64 items-center justify-center text-muted-foreground">
                    <div className="text-center">
                      <Package className="mx-auto h-12 w-12 mb-4" />
                      <p>Product management coming soon</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Reports Tab */}
            <TabsContent value="reports">
              <Card>
                <CardHeader>
                  <CardTitle>Reported Issues</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead>Reason</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Reported By</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mockReports.map((report) => (
                        <TableRow key={report.id}>
                          <TableCell className="capitalize">{report.type}</TableCell>
                          <TableCell>{report.reason}</TableCell>
                          <TableCell>
                            <Badge variant={report.status === 'pending' ? 'destructive' : 'secondary'}>
                              {report.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{report.reportedBy}</TableCell>
                          <TableCell>{report.date}</TableCell>
                          <TableCell className="text-right">
                            <Button variant="outline" size="sm">
                              Review
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </PageTransition>
  );
}
