/**
 * Brand Mock Data
 * 
 * Sample data for B2B portal features including orders, team members,
 * activity logs, and analytics data.
 */

import type {
    Brand,
    Order,
    OrderStatus,
    PaymentStatus,
    TeamMember,
    TeamRole,
    ActivityLog,
    ReturnRequest,
    CustomerDemographics,
    TrafficSource,
    ProductMetrics,
} from '@/types/brandTypes';

// ============================================
// Brand Profile Data
// ============================================

export const MOCK_BRAND: Brand = {
    id: 'brand-001',
    name: 'CONFIT Athletics',
    slug: 'confit-athletics',
    description: 'Premium athletic wear designed for modern lifestyles. Combining style with performance for the everyday athlete.',
    logo: 'https://images.unsplash.com/photo-1599305445671-ac291c95aaa9?w=200&h=200&fit=crop',
    banner: 'https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=1200&h=400&fit=crop',
    website: 'https://confit.com',
    email: 'business@confit.com',
    phone: '+1 (555) 123-4567',
    address: {
        street: '123 Fashion Avenue',
        city: 'New York',
        state: 'NY',
        postalCode: '10001',
        country: 'United States',
    },
    socialLinks: {
        instagram: '@confit_athletics',
        facebook: 'confitAthletics',
        twitter: '@confit',
        tiktok: '@confit',
    },
    settings: {
        currency: 'USD',
        timezone: 'America/New_York',
        language: 'en',
        notifications: {
            orderAlerts: true,
            lowStockAlerts: true,
            reviewAlerts: true,
            marketingUpdates: false,
            emailDigest: 'daily',
        },
        payoutMethod: 'stripe',
        minimumPayout: 100,
        autoFulfillment: false,
    },
    verified: true,
    createdAt: new Date('2024-01-15'),
    updatedAt: new Date('2025-02-01'),
};

// ============================================
// Orders Data
// ============================================

const orderStatuses: OrderStatus[] = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'];
const paymentStatuses: PaymentStatus[] = ['pending', 'paid', 'failed', 'refunded'];

export const MOCK_ORDERS: Order[] = [
    {
        id: 'ord-001',
        orderNumber: 'ORD-2025-0001',
        brandId: 'brand-001',
        customerId: 'cust-001',
        customer: {
            id: 'cust-001',
            name: 'Sarah Johnson',
            email: 'sarah.j@email.com',
            phone: '+1 (555) 234-5678',
            avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop',
            totalOrders: 5,
            totalSpent: 847.50,
        },
        items: [
            {
                id: 'item-001',
                productId: 'prod-1',
                productName: 'Premium Active Tee',
                productImage: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=100&h=100&fit=crop',
                sku: 'ACT-001-BLK-M',
                quantity: 2,
                unitPrice: 45.00,
                totalPrice: 90.00,
                size: 'M',
                color: 'Black',
            },
            {
                id: 'item-002',
                productId: 'prod-2',
                productName: 'Flex Yoga Leggings',
                productImage: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=100&h=100&fit=crop',
                sku: 'LEG-002-NVY-S',
                quantity: 1,
                unitPrice: 85.00,
                totalPrice: 85.00,
                size: 'S',
                color: 'Navy',
            },
        ],
        status: 'shipped',
        paymentStatus: 'paid',
        subtotal: 175.00,
        tax: 15.75,
        shipping: 8.99,
        discount: 0,
        total: 199.74,
        currency: 'USD',
        shippingAddress: {
            name: 'Sarah Johnson',
            street: '456 Oak Street',
            apartment: 'Apt 12B',
            city: 'Brooklyn',
            state: 'NY',
            postalCode: '11201',
            country: 'United States',
            phone: '+1 (555) 234-5678',
        },
        shippingMethod: {
            id: 'ship-standard',
            name: 'Standard Shipping',
            carrier: 'USPS',
            estimatedDays: 5,
            price: 8.99,
        },
        trackingNumber: '9400111899223456789012',
        createdAt: new Date('2025-02-05T14:30:00Z'),
        updatedAt: new Date('2025-02-06T09:15:00Z'),
        fulfilledAt: new Date('2025-02-06T09:15:00Z'),
    },
    {
        id: 'ord-002',
        orderNumber: 'ORD-2025-0002',
        brandId: 'brand-001',
        customerId: 'cust-002',
        customer: {
            id: 'cust-002',
            name: 'Michael Chen',
            email: 'michael.c@email.com',
            avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop',
            totalOrders: 2,
            totalSpent: 245.00,
        },
        items: [
            {
                id: 'item-003',
                productId: 'prod-3',
                productName: 'Performance Hoodie',
                productImage: 'https://images.unsplash.com/photo-1544923246-77307dd628b8?w=100&h=100&fit=crop',
                sku: 'HOD-003-GRY-L',
                quantity: 1,
                unitPrice: 110.00,
                totalPrice: 110.00,
                size: 'L',
                color: 'Gray',
            },
        ],
        status: 'processing',
        paymentStatus: 'paid',
        subtotal: 110.00,
        tax: 9.90,
        shipping: 0,
        discount: 10.00,
        total: 109.90,
        currency: 'USD',
        shippingAddress: {
            name: 'Michael Chen',
            street: '789 Pine Road',
            city: 'San Francisco',
            state: 'CA',
            postalCode: '94102',
            country: 'United States',
        },
        shippingMethod: {
            id: 'ship-express',
            name: 'Express Shipping',
            carrier: 'FedEx',
            estimatedDays: 2,
            price: 0,
        },
        notes: 'Customer requested gift wrapping',
        createdAt: new Date('2025-02-06T10:45:00Z'),
        updatedAt: new Date('2025-02-06T11:00:00Z'),
    },
    {
        id: 'ord-003',
        orderNumber: 'ORD-2025-0003',
        brandId: 'brand-001',
        customerId: 'cust-003',
        customer: {
            id: 'cust-003',
            name: 'Emily Rodriguez',
            email: 'emily.r@email.com',
            avatar: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop',
            totalOrders: 8,
            totalSpent: 1250.00,
        },
        items: [
            {
                id: 'item-004',
                productId: 'prod-4',
                productName: 'Runner Shorts',
                productImage: 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=100&h=100&fit=crop',
                sku: 'SHT-004-BLU-M',
                quantity: 2,
                unitPrice: 55.00,
                totalPrice: 110.00,
                size: 'M',
                color: 'Blue',
            },
            {
                id: 'item-005',
                productId: 'prod-5',
                productName: 'Impact Sports Bra',
                productImage: 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=100&h=100&fit=crop',
                sku: 'BRA-005-PNK-S',
                quantity: 1,
                unitPrice: 40.00,
                totalPrice: 40.00,
                size: 'S',
                color: 'Pink',
            },
        ],
        status: 'delivered',
        paymentStatus: 'paid',
        subtotal: 150.00,
        tax: 13.50,
        shipping: 8.99,
        discount: 15.00,
        total: 157.49,
        currency: 'USD',
        shippingAddress: {
            name: 'Emily Rodriguez',
            street: '321 Maple Avenue',
            city: 'Austin',
            state: 'TX',
            postalCode: '78701',
            country: 'United States',
        },
        shippingMethod: {
            id: 'ship-standard',
            name: 'Standard Shipping',
            carrier: 'USPS',
            estimatedDays: 5,
            price: 8.99,
        },
        trackingNumber: '9400111899223456789013',
        createdAt: new Date('2025-02-01T08:20:00Z'),
        updatedAt: new Date('2025-02-04T16:30:00Z'),
        fulfilledAt: new Date('2025-02-02T10:00:00Z'),
        deliveredAt: new Date('2025-02-04T16:30:00Z'),
    },
    {
        id: 'ord-004',
        orderNumber: 'ORD-2025-0004',
        brandId: 'brand-001',
        customerId: 'cust-004',
        customer: {
            id: 'cust-004',
            name: 'David Kim',
            email: 'david.k@email.com',
            totalOrders: 1,
            totalSpent: 95.00,
        },
        items: [
            {
                id: 'item-006',
                productId: 'prod-6',
                productName: 'Recovery Slides',
                productImage: 'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=100&h=100&fit=crop',
                sku: 'SLD-006-BLK-10',
                quantity: 1,
                unitPrice: 35.00,
                totalPrice: 35.00,
                size: '10',
                color: 'Black',
            },
        ],
        status: 'pending',
        paymentStatus: 'pending',
        subtotal: 35.00,
        tax: 3.15,
        shipping: 8.99,
        discount: 0,
        total: 47.14,
        currency: 'USD',
        shippingAddress: {
            name: 'David Kim',
            street: '555 Cedar Lane',
            city: 'Seattle',
            state: 'WA',
            postalCode: '98101',
            country: 'United States',
        },
        shippingMethod: {
            id: 'ship-standard',
            name: 'Standard Shipping',
            carrier: 'USPS',
            estimatedDays: 5,
            price: 8.99,
        },
        createdAt: new Date('2025-02-07T06:00:00Z'),
        updatedAt: new Date('2025-02-07T06:00:00Z'),
    },
    {
        id: 'ord-005',
        orderNumber: 'ORD-2025-0005',
        brandId: 'brand-001',
        customerId: 'cust-005',
        customer: {
            id: 'cust-005',
            name: 'Jessica Taylor',
            email: 'jessica.t@email.com',
            avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop',
            totalOrders: 3,
            totalSpent: 420.00,
        },
        items: [
            {
                id: 'item-007',
                productId: 'prod-1',
                productName: 'Premium Active Tee',
                productImage: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=100&h=100&fit=crop',
                sku: 'ACT-001-WHT-S',
                quantity: 3,
                unitPrice: 45.00,
                totalPrice: 135.00,
                size: 'S',
                color: 'White',
            },
        ],
        status: 'cancelled',
        paymentStatus: 'refunded',
        subtotal: 135.00,
        tax: 12.15,
        shipping: 8.99,
        discount: 0,
        total: 156.14,
        currency: 'USD',
        shippingAddress: {
            name: 'Jessica Taylor',
            street: '888 Birch Street',
            city: 'Denver',
            state: 'CO',
            postalCode: '80201',
            country: 'United States',
        },
        shippingMethod: {
            id: 'ship-standard',
            name: 'Standard Shipping',
            carrier: 'USPS',
            estimatedDays: 5,
            price: 8.99,
        },
        notes: 'Customer requested cancellation due to duplicate order',
        createdAt: new Date('2025-02-03T12:00:00Z'),
        updatedAt: new Date('2025-02-03T14:30:00Z'),
    },
];

// ============================================
// Team Members Data
// ============================================

export const MOCK_TEAM_MEMBERS: TeamMember[] = [
    {
        id: 'team-001',
        userId: 'user-001',
        brandId: 'brand-001',
        name: 'Alexandra Williams',
        email: 'alex.w@confit.com',
        avatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=100&h=100&fit=crop',
        role: 'owner',
        permissions: [],
        status: 'active',
        lastActive: new Date('2025-02-07T08:45:00Z'),
        invitedAt: new Date('2024-01-15'),
        joinedAt: new Date('2024-01-15'),
    },
    {
        id: 'team-002',
        userId: 'user-002',
        brandId: 'brand-001',
        name: 'James Martinez',
        email: 'james.m@confit.com',
        avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop',
        role: 'admin',
        permissions: [],
        status: 'active',
        lastActive: new Date('2025-02-07T09:30:00Z'),
        invitedAt: new Date('2024-03-10'),
        joinedAt: new Date('2024-03-11'),
    },
    {
        id: 'team-003',
        userId: 'user-003',
        brandId: 'brand-001',
        name: 'Sophie Anderson',
        email: 'sophie.a@confit.com',
        avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop',
        role: 'manager',
        permissions: [],
        status: 'active',
        lastActive: new Date('2025-02-06T17:00:00Z'),
        invitedAt: new Date('2024-06-01'),
        joinedAt: new Date('2024-06-02'),
    },
    {
        id: 'team-004',
        userId: 'user-004',
        brandId: 'brand-001',
        name: 'Ryan Thompson',
        email: 'ryan.t@confit.com',
        role: 'staff',
        permissions: [],
        status: 'active',
        lastActive: new Date('2025-02-07T07:15:00Z'),
        invitedAt: new Date('2024-09-15'),
        joinedAt: new Date('2024-09-16'),
    },
    {
        id: 'team-005',
        userId: 'user-005',
        brandId: 'brand-001',
        name: 'Olivia Brown',
        email: 'olivia.b@external.com',
        role: 'viewer',
        permissions: [],
        status: 'invited',
        invitedAt: new Date('2025-02-05'),
    },
];

// ============================================
// Activity Logs Data
// ============================================

export const MOCK_ACTIVITY_LOGS: ActivityLog[] = [
    {
        id: 'log-001',
        brandId: 'brand-001',
        userId: 'user-001',
        userName: 'Alexandra Williams',
        userAvatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=100&h=100&fit=crop',
        action: 'created',
        resource: 'products',
        resourceId: 'prod-new-001',
        resourceName: 'Spring Collection Hoodie',
        details: 'Added new product to Spring Collection',
        createdAt: new Date('2025-02-07T09:30:00Z'),
    },
    {
        id: 'log-002',
        brandId: 'brand-001',
        userId: 'user-002',
        userName: 'James Martinez',
        userAvatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop',
        action: 'fulfilled',
        resource: 'orders',
        resourceId: 'ord-001',
        resourceName: 'ORD-2025-0001',
        details: 'Order shipped via USPS',
        createdAt: new Date('2025-02-06T09:15:00Z'),
    },
    {
        id: 'log-003',
        brandId: 'brand-001',
        userId: 'user-003',
        userName: 'Sophie Anderson',
        userAvatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop',
        action: 'updated',
        resource: 'products',
        resourceId: 'prod-2',
        resourceName: 'Flex Yoga Leggings',
        details: 'Updated stock count from 45 to 120',
        createdAt: new Date('2025-02-06T08:00:00Z'),
    },
    {
        id: 'log-004',
        brandId: 'brand-001',
        userId: 'user-001',
        userName: 'Alexandra Williams',
        userAvatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=100&h=100&fit=crop',
        action: 'created',
        resource: 'campaigns',
        resourceId: 'camp-001',
        resourceName: 'Summer Sale Boost',
        details: 'Created new promotional campaign',
        createdAt: new Date('2025-02-05T14:20:00Z'),
    },
    {
        id: 'log-005',
        brandId: 'brand-001',
        userId: 'user-002',
        userName: 'James Martinez',
        userAvatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop',
        action: 'invited',
        resource: 'team',
        resourceId: 'team-005',
        resourceName: 'Olivia Brown',
        details: 'Invited as viewer',
        createdAt: new Date('2025-02-05T10:00:00Z'),
    },
    {
        id: 'log-006',
        brandId: 'brand-001',
        userId: 'user-004',
        userName: 'Ryan Thompson',
        action: 'cancelled',
        resource: 'orders',
        resourceId: 'ord-005',
        resourceName: 'ORD-2025-0005',
        details: 'Customer requested cancellation',
        createdAt: new Date('2025-02-03T14:30:00Z'),
    },
    {
        id: 'log-007',
        brandId: 'brand-001',
        userId: 'user-001',
        userName: 'Alexandra Williams',
        userAvatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=100&h=100&fit=crop',
        action: 'exported',
        resource: 'analytics',
        details: 'Exported monthly sales report',
        createdAt: new Date('2025-02-01T12:00:00Z'),
    },
    {
        id: 'log-008',
        brandId: 'brand-001',
        userId: 'user-003',
        userName: 'Sophie Anderson',
        userAvatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop',
        action: 'imported',
        resource: 'products',
        details: 'Bulk imported 25 products from CSV',
        createdAt: new Date('2025-01-28T09:45:00Z'),
    },
];

// ============================================
// Returns Data
// ============================================

export const MOCK_RETURNS: ReturnRequest[] = [
    {
        id: 'ret-001',
        orderId: 'ord-003',
        orderNumber: 'ORD-2025-0003',
        customerId: 'cust-003',
        customerName: 'Emily Rodriguez',
        items: [
            {
                orderItemId: 'item-004',
                productName: 'Runner Shorts',
                quantity: 1,
                reason: 'Size too large',
            },
        ],
        reason: 'wrong_size',
        status: 'approved',
        refundAmount: 55.00,
        notes: 'Customer will exchange for smaller size',
        createdAt: new Date('2025-02-05T10:00:00Z'),
    },
];

// ============================================
// Analytics Data
// ============================================

export const MOCK_CUSTOMER_DEMOGRAPHICS: CustomerDemographics = {
    ageGroups: [
        { range: '18-24', count: 1250, percentage: 15 },
        { range: '25-34', count: 3500, percentage: 42 },
        { range: '35-44', count: 2100, percentage: 25 },
        { range: '45-54', count: 980, percentage: 12 },
        { range: '55+', count: 500, percentage: 6 },
    ],
    genderDistribution: [
        { gender: 'Female', count: 5200, percentage: 62 },
        { gender: 'Male', count: 2800, percentage: 34 },
        { gender: 'Non-binary', count: 330, percentage: 4 },
    ],
    topLocations: [
        { location: 'California', count: 1850, percentage: 22 },
        { location: 'New York', count: 1420, percentage: 17 },
        { location: 'Texas', count: 980, percentage: 12 },
        { location: 'Florida', count: 750, percentage: 9 },
        { location: 'Illinois', count: 580, percentage: 7 },
    ],
};

export const MOCK_TRAFFIC_SOURCES: TrafficSource[] = [
    { source: 'Organic Search', visitors: 12500, orders: 875, revenue: 78500, conversionRate: 7.0 },
    { source: 'Direct', visitors: 8200, orders: 620, revenue: 55800, conversionRate: 7.6 },
    { source: 'Social Media', visitors: 6800, orders: 408, revenue: 36700, conversionRate: 6.0 },
    { source: 'Paid Ads', visitors: 4500, orders: 360, revenue: 32400, conversionRate: 8.0 },
    { source: 'Email', visitors: 3200, orders: 288, revenue: 25900, conversionRate: 9.0 },
    { source: 'Referral', visitors: 1800, orders: 126, revenue: 11340, conversionRate: 7.0 },
];

export const MOCK_PRODUCT_METRICS: ProductMetrics[] = [
    { productId: 'prod-1', productName: 'Premium Active Tee', views: 8500, addToCart: 1275, purchases: 425, revenue: 19125, conversionRate: 5.0 },
    { productId: 'prod-2', productName: 'Flex Yoga Leggings', views: 7200, addToCart: 1080, purchases: 324, revenue: 27540, conversionRate: 4.5 },
    { productId: 'prod-3', productName: 'Performance Hoodie', views: 5600, addToCart: 840, purchases: 252, revenue: 27720, conversionRate: 4.5 },
    { productId: 'prod-4', productName: 'Runner Shorts', views: 6800, addToCart: 1020, purchases: 374, revenue: 20570, conversionRate: 5.5 },
    { productId: 'prod-5', productName: 'Impact Sports Bra', views: 4200, addToCart: 630, purchases: 210, revenue: 8400, conversionRate: 5.0 },
];

// ============================================
// Helper Functions
// ============================================

export function getOrderStatusColor(status: OrderStatus): string {
    const colors: Record<OrderStatus, string> = {
        pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
        confirmed: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
        processing: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
        shipped: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
        delivered: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
        cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
        refunded: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };
    return colors[status] || colors.pending;
}

export function getPaymentStatusColor(status: PaymentStatus): string {
    const colors: Record<PaymentStatus, string> = {
        pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
        paid: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
        failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
        refunded: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
        partially_refunded: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    };
    return colors[status] || colors.pending;
}

export function getRoleColor(role: TeamRole): string {
    const colors: Record<TeamRole, string> = {
        owner: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
        admin: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
        manager: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
        staff: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
        viewer: 'bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-400',
    };
    return colors[role] || colors.viewer;
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
    }).format(amount);
}

export function formatDate(date: Date, options?: Intl.DateTimeFormatOptions): string {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        ...options,
    }).format(date);
}

export function formatDateTime(date: Date): string {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }).format(date);
}

export function getRelativeTime(date: Date): string {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(date);
}
