import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, APIError } from './client';
import { API_ENDPOINTS } from './endpoints';

// Re-export APIError for consumers
export { APIError };

// Generic query hook factory
export function createQueryHook<T>(
  queryKey: unknown[],
  endpoint: string,
  options?: {
    enabled?: boolean;
    staleTime?: number;
    refetchInterval?: number;
    params?: Record<string, string | number | boolean | undefined>;
  }
) {
  return () =>
    useQuery<T, APIError>({
      queryKey,
      queryFn: () => api.get<T>(endpoint, options?.params),
      ...options,
    });
}

// Products
export function useProducts(params?: Record<string, string | number | boolean | undefined>) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.LIST, params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.DETAIL(id)),
    enabled: !!id,
  });
}

export function useFeaturedProducts() {
  return useQuery({
    queryKey: ['products', 'featured'],
    queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.FEATURED),
    staleTime: 10 * 60 * 1000,
  });
}

export function useTrendingProducts() {
  return useQuery({
    queryKey: ['products', 'trending'],
    queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.TRENDING),
    staleTime: 10 * 60 * 1000,
  });
}

export function useProductSearch(query: string) {
  return useQuery({
    queryKey: ['products', 'search', query],
    queryFn: () => api.get(API_ENDPOINTS.PRODUCTS.SEARCH, { query }),
    enabled: query.length > 2,
  });
}

// Brands
export function useBrands(params?: Record<string, string | number | boolean | undefined>) {
  return useQuery({
    queryKey: ['brands', params],
    queryFn: () => api.get(API_ENDPOINTS.BRANDS.LIST, params),
    staleTime: 30 * 60 * 1000,
  });
}

export function useBrand(id: string) {
  return useQuery({
    queryKey: ['brand', id],
    queryFn: () => api.get(API_ENDPOINTS.BRANDS.DETAIL(id)),
    enabled: !!id,
  });
}

export function useBrandDashboard(brandId: string) {
  return useQuery({
    queryKey: ['brand', 'dashboard', brandId],
    queryFn: () => api.get(API_ENDPOINTS.BRANDS.DASHBOARD(brandId)),
    enabled: !!brandId,
  });
}

// Wardrobe
export function useWardrobe(params?: Record<string, string | number | boolean | undefined>) {
  return useQuery({
    queryKey: ['wardrobe', params],
    queryFn: () => api.get(API_ENDPOINTS.WARDROBE.LIST, params),
  });
}

export function useWardrobeSuggestions(params?: { occasion?: string; season?: string; limit?: number }) {
  return useQuery({
    queryKey: ['wardrobe', 'suggestions', params],
    queryFn: () => api.get(API_ENDPOINTS.WARDROBE.SUGGESTIONS, params),
  });
}

// Outfits
export function useOutfits() {
  return useQuery({
    queryKey: ['outfits'],
    queryFn: () => api.get(API_ENDPOINTS.WARDROBE.OUTFITS),
  });
}

export function useOutfit(id: string) {
  return useQuery({
    queryKey: ['outfit', id],
    queryFn: () => api.get(API_ENDPOINTS.WARDROBE.OUTFIT_DETAIL(id)),
    enabled: !!id,
  });
}

// Orders
export function useOrders() {
  return useQuery({
    queryKey: ['orders'],
    queryFn: () => api.get(API_ENDPOINTS.ORDERS.LIST),
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: () => api.get(API_ENDPOINTS.ORDERS.DETAIL(id)),
    enabled: !!id,
  });
}

// Profile
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => api.get(API_ENDPOINTS.PROFILE.GET),
  });
}

// Cart
export function useCart() {
  return useQuery({
    queryKey: ['cart'],
    queryFn: () => api.get(API_ENDPOINTS.CART.GET),
  });
}

// Wishlist
export function useWishlist() {
  return useQuery({
    queryKey: ['wishlist'],
    queryFn: () => api.get(API_ENDPOINTS.WISHLIST.GET),
  });
}

// Mutations
export function useAddToCart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { productId: string; size: string; color: string; quantity: number }) =>
      api.post(API_ENDPOINTS.CART.ADD, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) => api.post(API_ENDPOINTS.ORDERS.CREATE, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

export function useAddWardrobeItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { product_id?: string; name: string; category: string; color: string; image?: File }) =>
      data.image
        ? api.upload(API_ENDPOINTS.WARDROBE.ADD, data.image, 'image', { name: data.name, category: data.category, color: data.color })
        : api.post(API_ENDPOINTS.WARDROBE.ADD, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] });
    },
  });
}

export function useCreateOutfit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; item_ids: string[]; occasion?: string }) =>
      api.post(API_ENDPOINTS.WARDROBE.CREATE_OUTFIT, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outfits'] });
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] });
    },
  });
}

export function useStylistChat() {
  return useMutation({
    mutationFn: (message: string) => api.post(API_ENDPOINTS.STYLIST.CHAT, { message }),
  });
}

export function useVisualSearch() {
  return useMutation({
    mutationFn: (image: File) => api.upload(API_ENDPOINTS.VISUAL_SEARCH.SEARCH, image, 'image'),
  });
}

export function useVirtualTryOn() {
  return useMutation({
    mutationFn: (data: { productId: string; userImage: File }) =>
      api.upload(API_ENDPOINTS.TRY_ON.GENERATE, data.userImage, 'userImage', { productId: data.productId }),
  });
}

export function useFollowBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (brandId: string) => api.post(API_ENDPOINTS.BRANDS.FOLLOW(brandId)),
    onSuccess: (_, brandId) => {
      queryClient.invalidateQueries({ queryKey: ['brand', brandId] });
      queryClient.invalidateQueries({ queryKey: ['brands'] });
    },
  });
}

export function useUnfollowBrand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (brandId: string) => api.delete(API_ENDPOINTS.BRANDS.FOLLOW(brandId)),
    onSuccess: (_, brandId) => {
      queryClient.invalidateQueries({ queryKey: ['brand', brandId] });
      queryClient.invalidateQueries({ queryKey: ['brands'] });
    },
  });
}

export function useToggleWardrobeFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => api.post(API_ENDPOINTS.WARDROBE.FAVORITE(itemId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] });
    },
  });
}
