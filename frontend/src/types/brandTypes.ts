/**
 * Brand & Admin Management Types
 * 
 * TypeScript interfaces and types for the B2B brand portal features
 * including orders, team management, analytics, and settings.
 */

// ============================================
// Brand & Profile Types
// ============================================

export interface Brand {
    id: string;
    name: string;
    slug: string;
    description: string;
    logo: string;
    banner?: string;
    website?: string;
    email: string;
    phone?: string;
    address: BrandAddress;
    socialLinks: SocialLinks;
    settings: BrandSettings;
    verified: boolean;
    createdAt: Date;
    updatedAt: Date;
}

export interface BrandAddress {
    street: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
}

export interface SocialLinks {
    instagram?: string;
    facebook?: string;
    twitter?: string;
    tiktok?: string;
    pinterest?: string;
}

export interface BrandSettings {
    currency: string;
    timezone: string;
    language: string;
    notifications: NotificationSettings;
    payoutMethod: PayoutMethod;
    minimumPayout: number;
    autoFulfillment: boolean;
}

export interface NotificationSettings {
    orderAlerts: boolean;
    lowStockAlerts: boolean;
    reviewAlerts: boolean;
    marketingUpdates: boolean;
    emailDigest: 'daily' | 'weekly' | 'never';
}

export type PayoutMethod = 'bank_transfer' | 'paypal' | 'stripe';

// ============================================
// Order Types
// ============================================

export interface Order {
    id: string;
    orderNumber: string;
    brandId: string;
    customerId: string;
    customer: OrderCustomer;
    items: OrderItem[];
    status: OrderStatus;
    paymentStatus: PaymentStatus;
    subtotal: number;
    tax: number;
    shipping: number;
    discount: number;
    total: number;
    currency: string;
    shippingAddress: ShippingAddress;
    billingAddress?: ShippingAddress;
    shippingMethod: ShippingMethod;
    trackingNumber?: string;
    notes?: string;
    createdAt: Date;
    updatedAt: Date;
    fulfilledAt?: Date;
    deliveredAt?: Date;
}

export interface OrderCustomer {
    id: string;
    name: string;
    email: string;
    phone?: string;
    avatar?: string;
    totalOrders: number;
    totalSpent: number;
}

export interface OrderItem {
    id: string;
    productId: string;
    productName: string;
    productImage: string;
    sku: string;
    quantity: number;
    unitPrice: number;
    totalPrice: number;
    size?: string;
    color?: string;
    variant?: string;
}

export type OrderStatus =
    | 'pending'
    | 'confirmed'
    | 'processing'
    | 'shipped'
    | 'delivered'
    | 'cancelled'
    | 'refunded';

export type PaymentStatus =
    | 'pending'
    | 'paid'
    | 'failed'
    | 'refunded'
    | 'partially_refunded';

export interface ShippingAddress {
    name: string;
    street: string;
    apartment?: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
    phone?: string;
}

export interface ShippingMethod {
    id: string;
    name: string;
    carrier: string;
    estimatedDays: number;
    price: number;
}

// ============================================
// Team & Permission Types
// ============================================

export interface TeamMember {
    id: string;
    userId: string;
    brandId: string;
    name: string;
    email: string;
    avatar?: string;
    role: TeamRole;
    permissions: Permission[];
    status: 'active' | 'invited' | 'deactivated';
    lastActive?: Date;
    invitedAt: Date;
    joinedAt?: Date;
}

export type TeamRole = 'owner' | 'admin' | 'manager' | 'staff' | 'viewer';

export interface Permission {
    resource: PermissionResource;
    actions: PermissionAction[];
}

export type PermissionResource =
    | 'products'
    | 'orders'
    | 'analytics'
    | 'campaigns'
    | 'settings'
    | 'team';

export type PermissionAction = 'view' | 'create' | 'edit' | 'delete' | 'manage';

export const ROLE_PERMISSIONS: Record<TeamRole, Permission[]> = {
    owner: [
        { resource: 'products', actions: ['view', 'create', 'edit', 'delete', 'manage'] },
        { resource: 'orders', actions: ['view', 'create', 'edit', 'delete', 'manage'] },
        { resource: 'analytics', actions: ['view', 'manage'] },
        { resource: 'campaigns', actions: ['view', 'create', 'edit', 'delete', 'manage'] },
        { resource: 'settings', actions: ['view', 'edit', 'manage'] },
        { resource: 'team', actions: ['view', 'create', 'edit', 'delete', 'manage'] },
    ],
    admin: [
        { resource: 'products', actions: ['view', 'create', 'edit', 'delete'] },
        { resource: 'orders', actions: ['view', 'create', 'edit', 'delete'] },
        { resource: 'analytics', actions: ['view'] },
        { resource: 'campaigns', actions: ['view', 'create', 'edit', 'delete'] },
        { resource: 'settings', actions: ['view', 'edit'] },
        { resource: 'team', actions: ['view', 'create', 'edit'] },
    ],
    manager: [
        { resource: 'products', actions: ['view', 'create', 'edit'] },
        { resource: 'orders', actions: ['view', 'edit'] },
        { resource: 'analytics', actions: ['view'] },
        { resource: 'campaigns', actions: ['view', 'create', 'edit'] },
        { resource: 'settings', actions: ['view'] },
        { resource: 'team', actions: ['view'] },
    ],
    staff: [
        { resource: 'products', actions: ['view', 'edit'] },
        { resource: 'orders', actions: ['view', 'edit'] },
        { resource: 'analytics', actions: ['view'] },
        { resource: 'campaigns', actions: ['view'] },
        { resource: 'settings', actions: ['view'] },
        { resource: 'team', actions: ['view'] },
    ],
    viewer: [
        { resource: 'products', actions: ['view'] },
        { resource: 'orders', actions: ['view'] },
        { resource: 'analytics', actions: ['view'] },
        { resource: 'campaigns', actions: ['view'] },
        { resource: 'settings', actions: ['view'] },
        { resource: 'team', actions: ['view'] },
    ],
};

// ============================================
// Activity Log Types
// ============================================

export interface ActivityLog {
    id: string;
    brandId: string;
    userId: string;
    userName: string;
    userAvatar?: string;
    action: ActivityAction;
    resource: PermissionResource;
    resourceId?: string;
    resourceName?: string;
    details?: string;
    metadata?: Record<string, unknown>;
    ipAddress?: string;
    userAgent?: string;
    createdAt: Date;
}

export type ActivityAction =
    | 'created'
    | 'updated'
    | 'deleted'
    | 'viewed'
    | 'exported'
    | 'imported'
    | 'published'
    | 'unpublished'
    | 'fulfilled'
    | 'cancelled'
    | 'refunded'
    | 'invited'
    | 'joined'
    | 'left'
    | 'login'
    | 'logout';

// ============================================
// Analytics Types
// ============================================

export interface AnalyticsDateRange {
    start: Date;
    end: Date;
    preset?: 'today' | 'yesterday' | '7days' | '30days' | '90days' | 'year' | 'custom';
}

export interface SalesMetrics {
    totalRevenue: number;
    totalOrders: number;
    averageOrderValue: number;
    conversionRate: number;
    refundRate: number;
    repeatCustomerRate: number;
}

export interface ProductMetrics {
    productId: string;
    productName: string;
    views: number;
    addToCart: number;
    purchases: number;
    revenue: number;
    conversionRate: number;
}

export interface CustomerDemographics {
    ageGroups: { range: string; count: number; percentage: number }[];
    genderDistribution: { gender: string; count: number; percentage: number }[];
    topLocations: { location: string; count: number; percentage: number }[];
}

export interface TrafficSource {
    source: string;
    visitors: number;
    orders: number;
    revenue: number;
    conversionRate: number;
}

// ============================================
// Return & Refund Types
// ============================================

export interface ReturnRequest {
    id: string;
    orderId: string;
    orderNumber: string;
    customerId: string;
    customerName: string;
    items: ReturnItem[];
    reason: ReturnReason;
    status: ReturnStatus;
    refundAmount: number;
    notes?: string;
    createdAt: Date;
    resolvedAt?: Date;
}

export interface ReturnItem {
    orderItemId: string;
    productName: string;
    quantity: number;
    reason: string;
}

export type ReturnReason =
    | 'wrong_size'
    | 'defective'
    | 'not_as_described'
    | 'changed_mind'
    | 'late_delivery'
    | 'other';

export type ReturnStatus =
    | 'requested'
    | 'approved'
    | 'rejected'
    | 'received'
    | 'refunded';

// ============================================
// Product Management Types
// ============================================

export interface ProductVariant {
    id: string;
    sku: string;
    size?: string;
    color?: string;
    material?: string;
    price: number;
    compareAtPrice?: number;
    stock: number;
    image?: string;
    weight?: number;
    barcode?: string;
}

export interface ProductFormData {
    name: string;
    description: string;
    category: string;
    subcategory?: string;
    brand: string;
    basePrice: number;
    compareAtPrice?: number;
    costPrice?: number;
    sku: string;
    barcode?: string;
    images: string[];
    variants: ProductVariant[];
    tags: string[];
    seoTitle?: string;
    seoDescription?: string;
    status: 'draft' | 'active' | 'archived';
    publishAt?: Date;
    weight?: number;
    dimensions?: {
        length: number;
        width: number;
        height: number;
        unit: 'cm' | 'in';
    };
}

// ============================================
// Utility Types
// ============================================

export type SortDirection = 'asc' | 'desc';

export interface PaginationParams {
    page: number;
    limit: number;
    sortBy?: string;
    sortDirection?: SortDirection;
}

export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    limit: number;
    totalPages: number;
}

export interface FilterParams {
    search?: string;
    status?: string[];
    dateRange?: AnalyticsDateRange;
    categories?: string[];
    brands?: string[];
}
