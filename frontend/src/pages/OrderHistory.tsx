import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Package,
    ChevronRight,
    Truck,
    CheckCircle,
    Clock,
    XCircle,
    Eye,
    RotateCcw,
    MapPin,
    Search,
    Filter,
    ShoppingBag,
    FileText,
    ArrowRight
} from 'lucide-react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

// Types
interface OrderItem {
    id: string;
    productId: string;
    productName: string;
    productImage: string;
    brand: string;
    size: string;
    color: string;
    price: number;
    quantity: number;
}

interface Order {
    id: string;
    orderNumber: string;
    placedAt: string;
    status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
    items: OrderItem[];
    subtotal: number;
    shipping: number;
    tax: number;
    total: number;
    trackingNumber?: string;
    estimatedDelivery?: string;
    shippingAddress: {
        firstName: string;
        lastName: string;
        address: string;
        city: string;
        state: string;
        zipCode: string;
        country: string;
        phone: string;
    };
    paymentMethod: string;
}

// Mock Data
const MOCK_ORDERS: Order[] = [
    {
        id: 'ord-123',
        orderNumber: 'CONF-89231',
        placedAt: '2024-02-14T10:30:00Z',
        status: 'processing',
        items: [
            { id: 'item-1', productId: 'p1', productName: 'Oxford Button-Down', brand: 'Ralph Lauren', size: 'L', color: 'White', price: 95.00, quantity: 1, productImage: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&q=80&w=200' },
            { id: 'item-2', productId: 'p2', productName: 'Slim Fit Chinos', brand: 'Tommy Hilfiger', size: '32', color: 'Navy', price: 89.50, quantity: 1, productImage: 'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?auto=format&fit=crop&q=80&w=200' }
        ],
        subtotal: 184.50, shipping: 10.00, tax: 15.50, total: 210.00,
        estimatedDelivery: '2024-02-18',
        shippingAddress: {
            firstName: "Alex", lastName: "Johnson", address: "123 Fashion Ave", city: "New York", state: "NY", zipCode: "10001", country: "USA", phone: "+1 (555) 012-3456"
        },
        paymentMethod: "Visa ending in 4242"
    },
    {
        id: 'ord-122',
        orderNumber: 'CONF-77120',
        placedAt: '2024-01-20T14:15:00Z',
        status: 'delivered',
        items: [
            { id: 'item-3', productId: 'p3', productName: 'Silk Scarf', brand: 'Gucci', size: 'One Size', color: 'Floral', price: 350.00, quantity: 1, productImage: 'https://images.unsplash.com/photo-1584030373081-f37b785de72d?auto=format&fit=crop&q=80&w=200' }
        ],
        subtotal: 350.00, shipping: 0.00, tax: 28.00, total: 378.00,
        trackingNumber: '1Z999AA10123456784',
        estimatedDelivery: '2024-01-25',
        shippingAddress: {
            firstName: "Alex", lastName: "Johnson", address: "123 Fashion Ave", city: "New York", state: "NY", zipCode: "10001", country: "USA", phone: "+1 (555) 012-3456"
        },
        paymentMethod: "Apple Pay"
    }
];

export default function OrderHistory() {
    const [orders, setOrders] = useState<Order[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

    useEffect(() => {
        const fetchOrders = async () => {
            try {
                // In a real app, fetch from API
                // const res = await fetch(`${apiUrl}/api/orders`);
                // const data = await res.json();

                // Simulating network delay
                setTimeout(() => {
                    setOrders(MOCK_ORDERS);
                    setIsLoading(false);
                }, 800);
            } catch (error) {
                console.error("Failed to fetch orders", error);
                setOrders(MOCK_ORDERS);
                setIsLoading(false);
            }
        };
        fetchOrders();
    }, []);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'pending': return 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800';
            case 'processing': return 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800';
            case 'shipped': return 'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800';
            case 'delivered': return 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800';
            case 'cancelled': return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
            default: return 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'pending': return <Clock className="h-3.5 w-3.5" />;
            case 'processing': return <Package className="h-3.5 w-3.5" />;
            case 'shipped': return <Truck className="h-3.5 w-3.5" />;
            case 'delivered': return <CheckCircle className="h-3.5 w-3.5" />;
            case 'cancelled': return <XCircle className="h-3.5 w-3.5" />;
            default: return <Clock className="h-3.5 w-3.5" />;
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const filteredOrders = orders.filter(order =>
        order.orderNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
        order.items.some(item => item.productName.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    if (loading) {
        return (
            <MainLayout>
                <div className="min-h-[70vh] flex items-center justify-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent"></div>
                </div>
            </MainLayout>
        );
    }

    return (
        <MainLayout>
            <div className="container py-8 max-w-5xl">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-3xl font-display font-semibold mb-2">Order History</h1>
                        <p className="text-muted-foreground">Manage your orders and track shipments.</p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" asChild>
                            <Link href="/discover">Continue Shopping</Link>
                        </Button>
                    </div>
                </div>

                {/* Search and Filter */}
                <div className="flex gap-4 mb-6">
                    <div className="relative flex-1 max-w-sm">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search orders..."
                            className="pl-10"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <Button variant="outline"><Filter className="h-4 w-4 mr-2" /> Filter</Button>
                </div>

                {orders.length === 0 ? (
                    <div className="text-center py-16 bg-muted/30 rounded-2xl border border-dashed">
                        <ShoppingBag className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium mb-2">No orders yet</h3>
                        <p className="text-muted-foreground mb-6">When you place an order, it will appear here.</p>
                        <Button asChild variant="hero">
                            <Link href="/discover">Start Shopping <ArrowRight className="h-4 w-4 ml-2" /></Link>
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {filteredOrders.length === 0 ? (
                            <div className="text-center py-12 text-muted-foreground">No orders found matching "{searchTerm}"</div>
                        ) : (
                            filteredOrders.map((order, index) => (
                                <motion.div
                                    key={order.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={createTransition({ delay: index * 0.1 })}
                                    className="bg-card border border-border rounded-xl overflow-hidden hover:shadow-md transition-shadow group"
                                >
                                    {/* Order Header */}
                                    <div className="bg-muted/30 p-4 md:p-6 border-b border-border flex flex-wrap gap-6 items-center justify-between">
                                        <div className="flex flex-wrap gap-x-8 gap-y-4 text-sm">
                                            <div>
                                                <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1">Order Placed</p>
                                                <p className="font-medium">{formatDate(order.placedAt)}</p>
                                            </div>
                                            <div>
                                                <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1">Total</p>
                                                <p className="font-medium">${order.total.toFixed(2)}</p>
                                            </div>
                                            <div>
                                                <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1">Ship To</p>
                                                <div className="group relative">
                                                    <p className="font-medium text-accent hover:underline cursor-pointer flex items-center gap-1">
                                                        {order.shippingAddress.firstName} {order.shippingAddress.lastName} <ChevronRight className="h-3 w-3" />
                                                    </p>
                                                </div>
                                            </div>
                                            <div>
                                                <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1">Order #</p>
                                                <p className="font-medium font-mono">{order.orderNumber}</p>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-3 w-full md:w-auto">
                                            <Button variant="outline" size="sm" className="flex-1 md:flex-none" onClick={() => setSelectedOrder(order)}>
                                                View Order Details
                                            </Button>
                                            <Button variant="ghost" size="sm" className="flex-1 md:flex-none">
                                                Invoice
                                            </Button>
                                        </div>
                                    </div>

                                    {/* Order Body */}
                                    <div className="p-4 md:p-6">
                                        <div className="flex flex-col md:flex-row gap-6">
                                            {/* Status and Items */}
                                            <div className="flex-1 space-y-6">
                                                <div className="flex items-center gap-3">
                                                    <h3 className={cn("text-lg font-medium flex items-center gap-2",
                                                        order.status === 'delivered' ? "text-green-600 dark:text-green-400" :
                                                            order.status === 'processing' ? "text-blue-600 dark:text-blue-400" : ""
                                                    )}>
                                                        {order.status === 'delivered' ? 'Delivered' :
                                                            order.status === 'shipped' ? 'Shipped' :
                                                                order.status === 'processing' ? 'Processing' :
                                                                    order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                                                        {order.estimatedDelivery && order.status !== 'delivered' &&
                                                            <span className="text-sm font-normal text-muted-foreground ml-2">
                                                                Arriving {formatDate(order.estimatedDelivery)}
                                                            </span>
                                                        }
                                                    </h3>
                                                </div>

                                                <div className="space-y-4">
                                                    {order.items.map(item => (
                                                        <div key={item.id} className="flex gap-4 group/item">
                                                            <div className="relative h-24 w-20 flex-shrink-0 overflow-hidden rounded-md border border-border bg-muted">
                                                                <img
                                                                    src={item.productImage}
                                                                    alt={item.productName}
                                                                    className="h-full w-full object-cover object-center transition-transform group-hover/item:scale-105"
                                                                />
                                                            </div>
                                                            <div className="flex flex-1 flex-col justify-between py-1">
                                                                <div>
                                                                    <div className="flex justify-between items-start">
                                                                        <h4 className="font-medium hover:text-accent cursor-pointer transition-colors max-w-[200px] sm:max-w-none truncate">{item.productName}</h4>
                                                                        <p className="font-semibold text-sm">${item.price.toFixed(2)}</p>
                                                                    </div>
                                                                    <p className="text-sm text-muted-foreground mt-1">{item.brand} • {item.color} • {item.size}</p>
                                                                    <p className="text-sm text-muted-foreground">Qty: {item.quantity}</p>
                                                                </div>
                                                                <div className="flex gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                                    <Button variant="secondary" size="sm" className="h-7 text-xs">Buy again</Button>
                                                                    {order.status === 'delivered' && (
                                                                        <Button variant="outline" size="sm" className="h-7 text-xs">Write a review</Button>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            {/* Quick Actions */}
                                            <div className="flex flex-col gap-3 justify-center md:border-l md:pl-8 md:w-64">
                                                {order.status === 'shipped' && (
                                                    <Button variant="hero" className="w-full">
                                                        <Truck className="h-4 w-4 mr-2" /> Track Package
                                                    </Button>
                                                )}
                                                {order.status === 'delivered' && (
                                                    <Button variant="outline" className="w-full">
                                                        <RotateCcw className="h-4 w-4 mr-2" /> Return Items
                                                    </Button>
                                                )}
                                                <Button variant="outline" className="w-full">
                                                    Write a Product Review
                                                </Button>
                                                <Button variant="ghost" className="w-full text-xs text-muted-foreground h-auto py-2">
                                                    Archive Order
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ))
                        )}
                    </div>
                )}
            </div>

            {/* Order Details Modal */}
            <AnimatePresence>
                {selectedOrder && (
                    <Dialog open={!!selectedOrder} onOpenChange={(open) => !open && setSelectedOrder(null)}>
                        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                            <DialogHeader>
                                <DialogTitle className="text-xl font-display">Order Details</DialogTitle>
                                <DialogDescription>
                                    Order #{selectedOrder.orderNumber} placed on {new Date(selectedOrder.placedAt).toLocaleString()}
                                </DialogDescription>
                            </DialogHeader>

                            <div className="space-y-8 mt-4">
                                {/* Tracking Status */}
                                <div className="space-y-4">
                                    <h3 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground">Order Status</h3>
                                    <div className="relative">
                                        <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-muted">
                                            <div style={{
                                                width:
                                                    selectedOrder.status === 'pending' ? '25%' :
                                                        selectedOrder.status === 'processing' ? '50%' :
                                                            selectedOrder.status === 'shipped' ? '75%' :
                                                                selectedOrder.status === 'delivered' ? '100%' : '0%'
                                            }} className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-accent transition-all duration-500"></div>
                                        </div>
                                        <div className="flex justify-between text-xs font-medium text-muted-foreground">
                                            <span className={selectedOrder.status !== 'cancelled' ? 'text-foreground' : ''}>Ordered</span>
                                            <span className={['processing', 'shipped', 'delivered'].includes(selectedOrder.status) ? 'text-foreground' : ''}>Processing</span>
                                            <span className={['shipped', 'delivered'].includes(selectedOrder.status) ? 'text-foreground' : ''}>Shipped</span>
                                            <span className={selectedOrder.status === 'delivered' ? 'text-foreground' : ''}>Delivered</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Items */}
                                <div>
                                    <h3 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground mb-4">Items Ordered</h3>
                                    <div className="space-y-4">
                                        {selectedOrder.items.map(item => (
                                            <div key={item.id} className="flex gap-4 pb-4 border-b last:border-0 last:pb-0">
                                                <img src={item.productImage} alt={item.productName} className="w-16 h-16 object-cover rounded border" />
                                                <div className="flex-1">
                                                    <div className="flex justify-between">
                                                        <h4 className="font-medium text-sm">{item.productName}</h4>
                                                        <span className="font-semibold text-sm">${item.price.toFixed(2)}</span>
                                                    </div>
                                                    <p className="text-xs text-muted-foreground mt-1">{item.brand} • {item.size} • {item.color}</p>
                                                    <p className="text-xs text-muted-foreground mt-1">Qty: {item.quantity}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Info Grid */}
                                <div className="grid md:grid-cols-2 gap-8">
                                    <div>
                                        <h3 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground mb-3">Shipping Address</h3>
                                        <div className="text-sm space-y-1">
                                            <p className="font-medium">{selectedOrder.shippingAddress.firstName} {selectedOrder.shippingAddress.lastName}</p>
                                            <p>{selectedOrder.shippingAddress.address}</p>
                                            <p>{selectedOrder.shippingAddress.city}, {selectedOrder.shippingAddress.state} {selectedOrder.shippingAddress.zipCode}</p>
                                            <p>{selectedOrder.shippingAddress.country}</p>
                                            <p className="text-muted-foreground mt-2">{selectedOrder.shippingAddress.phone}</p>
                                        </div>
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-sm uppercase tracking-wide text-muted-foreground mb-3">Payment Summary</h3>
                                        <div className="text-sm space-y-2">
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Payment Method</span>
                                                <span className="font-medium">{selectedOrder.paymentMethod}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Subtotal</span>
                                                <span>${selectedOrder.subtotal.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Shipping</span>
                                                <span>${selectedOrder.shipping.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Tax</span>
                                                <span>${selectedOrder.tax.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between font-bold text-base border-t pt-2 mt-2">
                                                <span>Grand Total</span>
                                                <span>${selectedOrder.total.toFixed(2)}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <DialogFooter>
                                <Button variant="outline" onClick={() => setSelectedOrder(null)}>Close</Button>
                                <Button variant="hero">Reorder All Items</Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                )}
            </AnimatePresence>
        </MainLayout>
    );
}
