import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface Order {
  id: string;
  orderNumber: string;
  status: OrderStatus;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  shipping: number;
  discount: number;
  total: number;
  shippingAddress: Address;
  billingAddress: Address;
  paymentMethod: PaymentMethod;
  trackingNumber?: string;
  trackingUrl?: string;
  estimatedDelivery?: string;
  createdAt: string;
  updatedAt: string;
  history: OrderHistoryItem[];
}

export type OrderStatus =
  | 'pending'
  | 'confirmed'
  | 'processing'
  | 'shipped'
  | 'out_for_delivery'
  | 'delivered'
  | 'cancelled'
  | 'returned'
  | 'refunded';

export interface OrderItem {
  id: string;
  productId: string;
  name: string;
  brand: string;
  image: string;
  price: number;
  salePrice?: number;
  quantity: number;
  size: string;
  color: string;
  status: OrderStatus;
}

export interface Address {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  address1: string;
  address2?: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
}

export interface PaymentMethod {
  type: 'card' | 'paypal' | 'applepay' | 'googlepay';
  last4?: string;
  brand?: string;
}

export interface OrderHistoryItem {
  status: OrderStatus;
  timestamp: string;
  description: string;
  location?: string;
}

export interface OrderState {
  orders: Order[];
  currentOrder: Order | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setOrders: (orders: Order[]) => void;
  addOrder: (order: Order) => void;
  updateOrder: (id: string, updates: Partial<Order>) => void;
  setCurrentOrder: (order: Order | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  getOrderById: (id: string) => Order | undefined;
  getOrdersByStatus: (status: OrderStatus) => Order[];
  getActiveOrders: () => Order[];
}

export const useOrderStore = create<OrderState>()(
  persist(
    (set, get) => ({
      orders: [],
      currentOrder: null,
      isLoading: false,
      error: null,
      
      setOrders: (orders) => set({ orders }),
      
      addOrder: (order) =>
        set({ orders: [order, ...get().orders] }),
        
      updateOrder: (id, updates) =>
        set({
          orders: get().orders.map((order) =>
            order.id === id
              ? { ...order, ...updates, updatedAt: new Date().toISOString() }
              : order
          ),
        }),
        
      setCurrentOrder: (order) => set({ currentOrder: order }),
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      setError: (error) => set({ error }),
      
      getOrderById: (id) => get().orders.find((order) => order.id === id),
      
      getOrdersByStatus: (status) =>
        get().orders.filter((order) => order.status === status),
        
      getActiveOrders: () =>
        get().orders.filter((order) =>
          !['delivered', 'cancelled', 'returned', 'refunded'].includes(order.status)
        ),
    }),
    {
      name: 'confit-orders',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
