import { queryOptions } from '@tanstack/react-query';
import { api } from './client';
import { API_ENDPOINTS } from './endpoints';

// Query options for prefetching and SSR
export const productQueries = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    queryOptions({
      queryKey: ['products', params],
      queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.LIST, params),
      staleTime: 5 * 60 * 1000,
    }),
    
  detail: (id: string) =>
    queryOptions({
      queryKey: ['product', id],
      queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.DETAIL(id)),
      enabled: !!id,
    }),
    
  featured: () =>
    queryOptions({
      queryKey: ['products', 'featured'],
      queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.FEATURED),
      staleTime: 10 * 60 * 1000,
    }),
    
  trending: () =>
    queryOptions({
      queryKey: ['products', 'trending'],
      queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.TRENDING),
      staleTime: 10 * 60 * 1000,
    }),
    
  newArrivals: () =>
    queryOptions({
      queryKey: ['products', 'new-arrivals'],
      queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.NEW_ARRIVALS),
      staleTime: 10 * 60 * 1000,
    }),

  bestsellers: () =>
    queryOptions({
      queryKey: ['products', 'bestsellers'],
      queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.BESTSELLERS),
      staleTime: 10 * 60 * 1000,
    }),

  search: (query: string) =>
    queryOptions({
      queryKey: ['products', 'search', query],
      queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.SEARCH, { query }),
      enabled: query.length > 2,
    }),
};

export const brandQueries = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    queryOptions({
      queryKey: ['brands', params],
      queryFn: () => api.get(API_ENDPOINTS.BRANDS.LIST, params),
      staleTime: 30 * 60 * 1000,
    }),
    
  detail: (id: string) =>
    queryOptions({
      queryKey: ['brand', id],
      queryFn: () => api.get(API_ENDPOINTS.BRANDS.DETAIL(id)),
      enabled: !!id,
    }),

  bySlug: (slug: string) =>
    queryOptions({
      queryKey: ['brand', 'slug', slug],
      queryFn: () => api.get(API_ENDPOINTS.BRANDS.BY_SLUG(slug)),
      enabled: !!slug,
    }),
    
  featured: () =>
    queryOptions({
      queryKey: ['brands', 'featured'],
      queryFn: () => api.get(API_ENDPOINTS.BRANDS.FEATURED),
      staleTime: 30 * 60 * 1000,
    }),

  dashboard: (brandId: string) =>
    queryOptions({
      queryKey: ['brand', 'dashboard', brandId],
      queryFn: () => api.get(API_ENDPOINTS.BRANDS.DASHBOARD(brandId)),
      enabled: !!brandId,
    }),

  analytics: (brandId: string) =>
    queryOptions({
      queryKey: ['brand', 'analytics', brandId],
      queryFn: () => api.get(API_ENDPOINTS.BRANDS.ANALYTICS(brandId)),
      enabled: !!brandId,
    }),
};

export const wardrobeQueries = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    queryOptions({
      queryKey: ['wardrobe', params],
      queryFn: () => api.get(API_ENDPOINTS.WARDROBE.LIST, params),
    }),
    
  suggestions: (params?: { occasion?: string; season?: string; limit?: number }) =>
    queryOptions({
      queryKey: ['wardrobe', 'suggestions', params],
      queryFn: () => api.get(API_ENDPOINTS.WARDROBE.SUGGESTIONS, params),
    }),

  detail: (id: string) =>
    queryOptions({
      queryKey: ['wardrobe', 'item', id],
      queryFn: () => api.get(API_ENDPOINTS.WARDROBE.DETAIL(id)),
      enabled: !!id,
    }),
};

export const outfitQueries = {
  list: () =>
    queryOptions({
      queryKey: ['outfits'],
      queryFn: () => api.get(API_ENDPOINTS.WARDROBE.OUTFITS),
    }),
    
  detail: (id: string) =>
    queryOptions({
      queryKey: ['outfit', id],
      queryFn: () => api.get(API_ENDPOINTS.WARDROBE.OUTFIT_DETAIL(id)),
      enabled: !!id,
    }),
};

export const orderQueries = {
  list: () =>
    queryOptions({
      queryKey: ['orders'],
      queryFn: () => api.get(API_ENDPOINTS.ORDERS.LIST),
    }),
    
  detail: (id: string) =>
    queryOptions({
      queryKey: ['order', id],
      queryFn: () => api.get(API_ENDPOINTS.ORDERS.DETAIL(id)),
      enabled: !!id,
    }),
};

export const profileQueries = {
  get: () =>
    queryOptions({
      queryKey: ['profile'],
      queryFn: () => api.get(API_ENDPOINTS.PROFILE.GET),
    }),
};

export const cartQueries = {
  get: () =>
    queryOptions({
      queryKey: ['cart'],
      queryFn: () => api.get(API_ENDPOINTS.CART.GET),
    }),
};

export const wishlistQueries = {
  get: () =>
    queryOptions({
      queryKey: ['wishlist'],
      queryFn: () => api.get(API_ENDPOINTS.WISHLIST.GET),
    }),
};
