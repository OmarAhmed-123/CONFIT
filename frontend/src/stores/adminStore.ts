import { create } from 'zustand';

export interface AdminStats {
  totalUsers: number;
  activeUsers: number;
  totalOrders: number;
  totalRevenue: number;
  totalProducts: number;
  totalBrands: number;
  pendingApprovals: number;
  reportedIssues: number;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'brand' | 'admin';
  status: 'active' | 'suspended' | 'pending';
  createdAt: string;
  lastLogin: string;
  orderCount: number;
  totalSpent: number;
}

export interface AdminOrder {
  id: string;
  orderNumber: string;
  customerName: string;
  customerEmail: string;
  brandName: string;
  total: number;
  status: string;
  createdAt: string;
  items: number;
}

export interface AdminProduct {
  id: string;
  name: string;
  brandName: string;
  price: number;
  stock: number;
  status: 'active' | 'draft' | 'archived' | 'flagged';
  views: number;
  sales: number;
  createdAt: string;
}

export interface AdminReport {
  id: string;
  type: 'product' | 'user' | 'brand' | 'review';
  reportedId: string;
  reason: string;
  description: string;
  reportedBy: string;
  status: 'pending' | 'reviewed' | 'resolved' | 'dismissed';
  createdAt: string;
}

export interface AdminState {
  stats: AdminStats | null;
  users: AdminUser[];
  orders: AdminOrder[];
  products: AdminProduct[];
  reports: AdminReport[];
  isLoading: boolean;
  error: string | null;
  filters: {
    users: AdminUserFilter;
    orders: AdminOrderFilter;
    products: AdminProductFilter;
  };
}

export interface AdminUserFilter {
  role?: string;
  status?: string;
  search?: string;
}

export interface AdminOrderFilter {
  status?: string;
  dateRange?: [string, string];
  brandId?: string;
}

export interface AdminProductFilter {
  status?: string;
  brandId?: string;
  category?: string;
}

export const useAdminStore = create<AdminState>((set, get) => ({
  stats: null,
  users: [],
  orders: [],
  products: [],
  reports: [],
  isLoading: false,
  error: null,
  filters: {
    users: {},
    orders: {},
    products: {},
  },
  
  // Actions would be implemented here
  // For brevity, I'm showing the state structure
  // Full implementation would include:
  // - fetchStats, fetchUsers, fetchOrders, fetchProducts, fetchReports
  // - updateUserStatus, updateProductStatus, resolveReport
  // - setFilters, clearFilters
}));

// Extended actions
export const adminActions = {
  fetchStats: async () => {
    // Implementation would call API
  },
  fetchUsers: async (filter?: AdminUserFilter) => {
    // Implementation would call API
  },
  suspendUser: async (userId: string) => {
    // Implementation would call API
  },
  fetchReports: async () => {
    // Implementation would call API
  },
  resolveReport: async (reportId: string, action: string) => {
    // Implementation would call API
  },
};
