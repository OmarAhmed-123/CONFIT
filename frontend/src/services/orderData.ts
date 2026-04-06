import type { Product, OutfitSuggestion } from '@/types';

// Order types
export interface Order {
    id: string;
    orderNumber: string;
    date: Date;
    status: 'processing' | 'shipped' | 'delivered' | 'cancelled';
    items: OrderItem[];
    subtotal: number;
    shipping: number;
    tax: number;
    total: number;
    shippingAddress: ShippingAddress;
    paymentMethod: string;
    trackingNumber?: string;
    estimatedDelivery?: Date;
}

export interface OrderItem {
    product: Product;
    quantity: number;
    size: string;
    color: string;
    price: number;
}

export interface ShippingAddress {
    firstName: string;
    lastName: string;
    address: string;
    apartment?: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
    phone: string;
}

// Store types for BOPIS
export interface Store {
    id: string;
    name: string;
    address: string;
    city: string;
    state: string;
    zipCode: string;
    phone: string;
    hours: string;
    lat: number;
    lng: number;
    distance?: number;
    hasStock?: boolean;
    pickupTime?: string;
}

// Promo code types
export interface PromoCode {
    code: string;
    discountType: 'percentage' | 'fixed';
    discountValue: number;
    minOrderValue?: number;
    maxDiscount?: number;
    expirationDate?: Date;
    description: string;
}

// Mock Orders Data
export const mockOrders: Order[] = [
    {
        id: 'order-1',
        orderNumber: 'CFT-2026-001247',
        date: new Date('2026-02-03'),
        status: 'delivered',
        items: [
            {
                product: {
                    id: 'prod-1',
                    name: 'Silk Blend Blazer',
                    brand: 'Everlane',
                    price: 198,
                    originalPrice: 248,
                    images: ['https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=400&h=500&fit=crop'],
                    category: 'outerwear',
                    colors: ['Navy', 'Black'],
                    sizes: ['XS', 'S', 'M', 'L', 'XL'],
                    styleCompatibility: 92,
                    description: 'Premium silk blend blazer',
                    tags: ['formal', 'business'],
                    currency: 'USD',
                    subcategory: 'Blazers',
                    inStock: true,
                },
                quantity: 1,
                size: 'M',
                color: 'Navy',
                price: 198,
            },
        ],
        subtotal: 198,
        shipping: 0,
        tax: 15.84,
        total: 213.84,
        shippingAddress: {
            firstName: 'Sarah',
            lastName: 'Johnson',
            address: '123 Fashion Ave',
            city: 'New York',
            state: 'NY',
            zipCode: '10001',
            country: 'United States',
            phone: '+1 (555) 123-4567',
        },
        paymentMethod: 'Visa ending in 4242',
        trackingNumber: '1Z999AA10123456784',
    },
    {
        id: 'order-2',
        orderNumber: 'CFT-2026-001198',
        date: new Date('2026-01-28'),
        status: 'shipped',
        items: [
            {
                product: {
                    id: 'prod-2',
                    name: 'Cashmere Sweater',
                    brand: 'Theory',
                    price: 325,
                    images: ['https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop'],
                    category: 'tops',
                    colors: ['Beige', 'Gray'],
                    sizes: ['XS', 'S', 'M', 'L'],
                    styleCompatibility: 88,
                    description: 'Luxurious cashmere sweater',
                    tags: ['casual', 'luxury'],
                    currency: 'USD',
                    subcategory: 'Sweaters',
                    inStock: true,
                },
                quantity: 1,
                size: 'S',
                color: 'Beige',
                price: 325,
            },
            {
                product: {
                    id: 'prod-3',
                    name: 'Leather Crossbody Bag',
                    brand: 'Coach',
                    price: 275,
                    images: ['https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&h=500&fit=crop'],
                    category: 'bags',
                    colors: ['Tan', 'Black'],
                    sizes: ['One Size'],
                    styleCompatibility: 94,
                    description: 'Classic leather crossbody',
                    tags: ['everyday', 'classic'],
                    currency: 'USD',
                    subcategory: 'Crossbody',
                    inStock: true,
                },
                quantity: 1,
                size: 'One Size',
                color: 'Tan',
                price: 275,
            },
        ],
        subtotal: 600,
        shipping: 12,
        tax: 48.96,
        total: 660.96,
        shippingAddress: {
            firstName: 'Sarah',
            lastName: 'Johnson',
            address: '123 Fashion Ave',
            city: 'New York',
            state: 'NY',
            zipCode: '10001',
            country: 'United States',
            phone: '+1 (555) 123-4567',
        },
        paymentMethod: 'Visa ending in 4242',
        trackingNumber: '1Z999AA10123456785',
        estimatedDelivery: new Date('2026-02-08'),
    },
    {
        id: 'order-3',
        orderNumber: 'CFT-2026-001156',
        date: new Date('2026-01-15'),
        status: 'delivered',
        items: [
            {
                product: {
                    id: 'prod-4',
                    name: 'High-Rise Trousers',
                    brand: 'Vince',
                    price: 245,
                    images: ['https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop'],
                    category: 'bottoms',
                    colors: ['Black', 'Charcoal'],
                    sizes: ['0', '2', '4', '6', '8', '10'],
                    styleCompatibility: 90,
                    description: 'Tailored high-rise trousers',
                    tags: ['work', 'formal'],
                    currency: 'USD',
                    subcategory: 'Pants',
                    inStock: true,
                },
                quantity: 2,
                size: '4',
                color: 'Black',
                price: 490,
            },
        ],
        subtotal: 490,
        shipping: 0,
        tax: 39.20,
        total: 529.20,
        shippingAddress: {
            firstName: 'Sarah',
            lastName: 'Johnson',
            address: '123 Fashion Ave',
            city: 'New York',
            state: 'NY',
            zipCode: '10001',
            country: 'United States',
            phone: '+1 (555) 123-4567',
        },
        paymentMethod: 'Apple Pay',
    },
];

// Mock Stores Data for BOPIS
export const mockStores: Store[] = [
    {
        id: 'store-1',
        name: 'CONFIT SoHo',
        address: '580 Broadway',
        city: 'New York',
        state: 'NY',
        zipCode: '10012',
        phone: '(212) 555-0123',
        hours: 'Mon-Sat: 10am-9pm, Sun: 11am-7pm',
        lat: 40.7243,
        lng: -73.9975,
        distance: 0.8,
        hasStock: true,
        pickupTime: 'Ready in 2 hours',
    },
    {
        id: 'store-2',
        name: 'CONFIT Fifth Avenue',
        address: '725 Fifth Avenue',
        city: 'New York',
        state: 'NY',
        zipCode: '10022',
        phone: '(212) 555-0456',
        hours: 'Mon-Sat: 10am-8pm, Sun: 12pm-6pm',
        lat: 40.7620,
        lng: -73.9738,
        distance: 2.3,
        hasStock: true,
        pickupTime: 'Ready in 3 hours',
    },
    {
        id: 'store-3',
        name: 'CONFIT Brooklyn',
        address: '160 N 4th Street',
        city: 'Brooklyn',
        state: 'NY',
        zipCode: '11211',
        phone: '(718) 555-0789',
        hours: 'Mon-Sat: 11am-8pm, Sun: 11am-6pm',
        lat: 40.7166,
        lng: -73.9585,
        distance: 3.1,
        hasStock: false,
        pickupTime: 'Out of stock',
    },
    {
        id: 'store-4',
        name: 'CONFIT Upper East Side',
        address: '1045 Madison Avenue',
        city: 'New York',
        state: 'NY',
        zipCode: '10075',
        phone: '(212) 555-0321',
        hours: 'Mon-Sat: 10am-7pm, Sun: 12pm-5pm',
        lat: 40.7749,
        lng: -73.9638,
        distance: 4.2,
        hasStock: true,
        pickupTime: 'Ready tomorrow',
    },
];

// Mock Promo Codes
export const mockPromoCodes: PromoCode[] = [
    {
        code: 'WELCOME20',
        discountType: 'percentage',
        discountValue: 20,
        minOrderValue: 100,
        maxDiscount: 50,
        description: '20% off your first order',
    },
    {
        code: 'STYLE15',
        discountType: 'percentage',
        discountValue: 15,
        description: '15% off sitewide',
    },
    {
        code: 'FREESHIP',
        discountType: 'fixed',
        discountValue: 12,
        minOrderValue: 75,
        description: 'Free standard shipping',
    },
    {
        code: 'SAVE50',
        discountType: 'fixed',
        discountValue: 50,
        minOrderValue: 250,
        description: '$50 off orders $250+',
    },
];

// Helper functions
export function getOrderById(orderId: string): Order | undefined {
    return mockOrders.find(order => order.id === orderId);
}

export function getOrderByNumber(orderNumber: string): Order | undefined {
    return mockOrders.find(order => order.orderNumber === orderNumber);
}

export function getNearbyStores(limit: number = 4): Store[] {
    return mockStores.slice(0, limit);
}

export function getStoreById(storeId: string): Store | undefined {
    return mockStores.find(store => store.id === storeId);
}

export function validatePromoCode(code: string, orderTotal: number): {
    valid: boolean;
    promo?: PromoCode;
    discount?: number;
    message?: string;
} {
    const promo = mockPromoCodes.find(p => p.code.toUpperCase() === code.toUpperCase());

    if (!promo) {
        return { valid: false, message: 'Invalid promo code' };
    }

    if (promo.minOrderValue && orderTotal < promo.minOrderValue) {
        return {
            valid: false,
            message: `Minimum order of $${promo.minOrderValue} required`
        };
    }

    let discount = promo.discountType === 'percentage'
        ? (orderTotal * promo.discountValue) / 100
        : promo.discountValue;

    if (promo.maxDiscount && discount > promo.maxDiscount) {
        discount = promo.maxDiscount;
    }

    return { valid: true, promo, discount };
}

export function getStatusColor(status: Order['status']): string {
    switch (status) {
        case 'processing':
            return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
        case 'shipped':
            return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
        case 'delivered':
            return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
        case 'cancelled':
            return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
        default:
            return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
    }
}
