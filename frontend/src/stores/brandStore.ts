import { create } from 'zustand';

export interface Brand {
  id: string;
  name: string;
  slug: string;
  logo: string;
  coverImage: string;
  description: string;
  story: string;
  founded: number;
  headquarters: string;
  website?: string;
  socialLinks: {
    instagram?: string;
    twitter?: string;
    facebook?: string;
    pinterest?: string;
  };
  categories: string[];
  priceRange: 'budget' | 'mid-range' | 'premium' | 'luxury';
  sustainabilityRating: number;
  isVerified: boolean;
  isFeatured: boolean;
  productCount: number;
  followerCount: number;
  rating: number;
}

export interface BrandDashboard {
  brandId: string;
  stats: BrandStats;
  recentOrders: BrandOrder[];
  topProducts: BrandProduct[];
  revenue: RevenueData[];
  analytics: BrandAnalytics;
}

export interface BrandStats {
  totalRevenue: number;
  totalOrders: number;
  totalProducts: number;
  totalCustomers: number;
  averageRating: number;
  returnRate: number;
}

export interface BrandOrder {
  id: string;
  orderNumber: string;
  customerName: string;
  items: { name: string; quantity: number; price: number }[];
  total: number;
  status: string;
  createdAt: string;
}

export interface BrandProduct {
  id: string;
  name: string;
  image: string;
  price: number;
  stock: number;
  sold: number;
  rating: number;
}

export interface RevenueData {
  date: string;
  revenue: number;
  orders: number;
}

export interface BrandAnalytics {
  views: number;
  clicks: number;
  conversions: number;
  conversionRate: number;
  topCategories: { name: string; count: number }[];
  demographics: { age: string; percentage: number }[];
}

export interface BrandState {
  brands: Brand[];
  featuredBrands: Brand[];
  currentBrand: Brand | null;
  dashboard: BrandDashboard | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setBrands: (brands: Brand[]) => void;
  setFeaturedBrands: (brands: Brand[]) => void;
  setCurrentBrand: (brand: Brand | null) => void;
  setDashboard: (dashboard: BrandDashboard | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  getBrandById: (id: string) => Brand | undefined;
  getBrandBySlug: (slug: string) => Brand | undefined;
}

export const useBrandStore = create<BrandState>((set, get) => ({
  brands: [],
  featuredBrands: [],
  currentBrand: null,
  dashboard: null,
  isLoading: false,
  error: null,
  
  setBrands: (brands) => set({ brands }),
  
  setFeaturedBrands: (brands) => set({ featuredBrands: brands }),
  
  setCurrentBrand: (brand) => set({ currentBrand: brand }),
  
  setDashboard: (dashboard) => set({ dashboard }),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
  
  getBrandById: (id) => get().brands.find((brand) => brand.id === id),
  
  getBrandBySlug: (slug) => get().brands.find((brand) => brand.slug === slug),
}));
