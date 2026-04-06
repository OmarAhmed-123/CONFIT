import { create } from 'zustand';

export interface Product {
  id: string;
  name: string;
  brand: string;
  brandId: string;
  price: number;
  salePrice?: number;
  currency: string;
  images: string[];
  category: string;
  subcategory?: string;
  colors: ProductColor[];
  sizes: ProductSize[];
  description: string;
  details: string[];
  materials: string[];
  fit: string;
  careInstructions: string[];
  stock: number;
  rating: number;
  reviewCount: number;
  tags: string[];
  isNew: boolean;
  isFeatured: boolean;
  isTrending: boolean;
  sustainabilityScore?: number;
  relatedProducts: string[];
}

export interface ProductColor {
  id: string;
  name: string;
  hex: string;
  image?: string;
  stock: number;
}

export interface ProductSize {
  id: string;
  name: string;
  stock: number;
  measurements?: Record<string, number>;
}

export interface ProductFilter {
  category?: string;
  subcategory?: string;
  brand?: string[];
  priceRange?: [number, number];
  sizes?: string[];
  colors?: string[];
  rating?: number;
  isNew?: boolean;
  isSale?: boolean;
  sortBy?: 'newest' | 'price-asc' | 'price-desc' | 'rating' | 'popular';
}

export interface ProductState {
  products: Product[];
  featuredProducts: Product[];
  trendingProducts: Product[];
  newArrivals: Product[];
  searchResults: Product[];
  currentProduct: Product | null;
  filter: ProductFilter;
  isLoading: boolean;
  error: string | null;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    hasMore: boolean;
  };
  
  // Actions
  setProducts: (products: Product[]) => void;
  setFeaturedProducts: (products: Product[]) => void;
  setTrendingProducts: (products: Product[]) => void;
  setNewArrivals: (products: Product[]) => void;
  setSearchResults: (products: Product[]) => void;
  setCurrentProduct: (product: Product | null) => void;
  setFilter: (filter: Partial<ProductFilter>) => void;
  clearFilter: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPagination: (pagination: Partial<ProductState['pagination']>) => void;
  loadMore: () => void;
}

const initialFilter: ProductFilter = {
  sortBy: 'newest',
};

const initialPagination = {
  page: 1,
  pageSize: 20,
  total: 0,
  hasMore: false,
};

export const useProductStore = create<ProductState>((set, get) => ({
  products: [],
  featuredProducts: [],
  trendingProducts: [],
  newArrivals: [],
  searchResults: [],
  currentProduct: null,
  filter: initialFilter,
  isLoading: false,
  error: null,
  pagination: initialPagination,
  
  setProducts: (products) => set({ products }),
  
  setFeaturedProducts: (products) => set({ featuredProducts: products }),
  
  setTrendingProducts: (products) => set({ trendingProducts: products }),
  
  setNewArrivals: (products) => set({ newArrivals: products }),
  
  setSearchResults: (products) => set({ searchResults: products }),
  
  setCurrentProduct: (product) => set({ currentProduct: product }),
  
  setFilter: (filter) => {
    set({ filter: { ...get().filter, ...filter }, pagination: initialPagination });
  },
  
  clearFilter: () => set({ filter: initialFilter, pagination: initialPagination }),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
  
  setPagination: (pagination) =>
    set({ pagination: { ...get().pagination, ...pagination } }),
    
  loadMore: () => {
    const { pagination } = get();
    if (pagination.hasMore) {
      set({ pagination: { ...pagination, page: pagination.page + 1 } });
    }
  },
}));
