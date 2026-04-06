/**
 * CONFIT CARE - Beneficiary Shopping ViewModel
 * =============================================
 * ViewModel for beneficiary shopping experience with budget tracking.
 */

import { useState, useCallback, useEffect } from 'react';
import { 
  careService, 
  SessionContext
} from '../services/care.service';

interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
  size: string;
  color: string;
  image_url: string;
}

interface Product {
  id: string;
  name: string;
  brand: string;
  price: number;
  original_price?: number;
  image_url: string;
  category: string;
  sizes: string[];
  colors: string[];
  in_stock: boolean;
}

interface Filters {
  category?: string;
  size?: string;
  brand?: string;
  price_range?: [number, number];
}

interface UseBeneficiaryShoppingViewModel {
  // State
  context: SessionContext | null;
  products: Product[];
  cart: CartItem[];
  loading: boolean;
  error: string | null;
  budgetRemaining: number;
  showPrices: boolean;
  filters: Filters;
  sortBy: string;
  viewMode: 'grid' | 'list';
  
  // Actions
  fetchContext: () => Promise<void>;
  fetchProducts: () => Promise<void>;
  addToCart: (product: Product, size?: string, color?: string) => void;
  removeFromCart: (itemId: string) => void;
  updateQuantity: (itemId: string, quantity: number) => void;
  applyFilters: (filters: Filters) => void;
  setSortBy: (sort: string) => void;
  setViewMode: (mode: 'grid' | 'list') => void;
  checkout: () => Promise<void>;
  logout: () => void;
}

export const useBeneficiaryShoppingViewModel = (
  sessionToken: string | null
): UseBeneficiaryShoppingViewModel => {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [sortBy, setSortBy] = useState('recommended');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Derived state
  const budgetRemaining = context?.budget_remaining ?? context?.voucher?.budget_remaining ?? 0;
  const showPrices = true; // Could be configurable based on campaign settings

  const fetchContext = useCallback(async () => {
    if (!sessionToken) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const contextData = await careService.getSessionContext(sessionToken);
      setContext(contextData);
      
      // Load cart from session if exists
      if (contextData.session) {
        const savedCart = localStorage.getItem(`care_cart_${sessionToken}`);
        if (savedCart) {
          setCart(JSON.parse(savedCart));
        }
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to load session';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [sessionToken]);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch products with campaign filters
      const response = await fetch('/api/products?limit=100');
      const data = await response.json();
      
      let filteredProducts = data.products || data || [];
      
      // Apply campaign restrictions
      if (context?.allowed_categories && context.allowed_categories.length > 0) {
        filteredProducts = filteredProducts.filter((p: Product) => 
          context.allowed_categories!.includes(p.category)
        );
      }
      
      if (context?.excluded_brands && context.excluded_brands.length > 0) {
        filteredProducts = filteredProducts.filter((p: Product) => 
          !context.excluded_brands!.includes(p.brand)
        );
      }
      
      setProducts(filteredProducts);
    } catch (err: any) {
      console.error('Error fetching products:', err);
      // Set mock products for development
      setProducts(getMockProducts());
    } finally {
      setLoading(false);
    }
  }, [context]);

  const addToCart = useCallback((product: Product, size?: string, color?: string) => {
    const itemId = `${product.id}-${size || 'default'}-${color || 'default'}`;
    
    setCart(prev => {
      const existing = prev.find(item => item.id === itemId);
      
      if (existing) {
        return prev.map(item =>
          item.id === itemId
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      
      const newItem: CartItem = {
        id: itemId,
        name: product.name,
        price: product.price,
        quantity: 1,
        size: size || product.sizes[0] || 'One Size',
        color: color || product.colors[0] || 'Default',
        image_url: product.image_url,
      };
      
      const newCart = [...prev, newItem];
      
      // Save to localStorage
      if (sessionToken) {
        localStorage.setItem(`care_cart_${sessionToken}`, JSON.stringify(newCart));
      }
      
      return newCart;
    });
  }, [sessionToken]);

  const removeFromCart = useCallback((itemId: string) => {
    setCart(prev => {
      const newCart = prev.filter(item => item.id !== itemId);
      
      if (sessionToken) {
        localStorage.setItem(`care_cart_${sessionToken}`, JSON.stringify(newCart));
      }
      
      return newCart;
    });
  }, [sessionToken]);

  const updateQuantity = useCallback((itemId: string, quantity: number) => {
    if (quantity < 1) {
      removeFromCart(itemId);
      return;
    }
    
    setCart(prev => {
      const newCart = prev.map(item =>
        item.id === itemId ? { ...item, quantity } : item
      );
      
      if (sessionToken) {
        localStorage.setItem(`care_cart_${sessionToken}`, JSON.stringify(newCart));
      }
      
      return newCart;
    });
  }, [sessionToken, removeFromCart]);

  const applyFilters = useCallback((newFilters: Filters) => {
    setFilters(newFilters);
  }, []);

  const checkout = useCallback(async () => {
    if (!sessionToken || cart.length === 0) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Calculate total
      const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
      
      // Validate budget
      if (total > budgetRemaining) {
        throw new Error('Cart total exceeds remaining budget');
      }
      
      // Create order
      const orderData = {
        items: cart.map(item => ({
          product_id: item.id.split('-')[0],
          quantity: item.quantity,
          size: item.size,
          color: item.color,
          price: item.price,
        })),
        delivery_method: 'shipping',
        shipping_address: null, // Will be collected at checkout
      };
      
      const order = await careService.createCareOrder(sessionToken, orderData);
      
      // Clear cart
      setCart([]);
      localStorage.removeItem(`care_cart_${sessionToken}`);
      
      // Navigate to confirmation
      window.location.href = `/care/order-confirmation?order_id=${order.order_id}`;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to place order';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [sessionToken, cart, budgetRemaining]);

  const logout = useCallback(() => {
    // Clear session data
    if (sessionToken) {
      localStorage.removeItem(`care_cart_${sessionToken}`);
    }
    
    // Navigate to entry
    window.location.href = '/care/entry';
  }, [sessionToken]);

  return {
    context,
    products,
    cart,
    loading,
    error,
    budgetRemaining,
    showPrices,
    filters,
    sortBy,
    viewMode,
    fetchContext,
    fetchProducts,
    addToCart,
    removeFromCart,
    updateQuantity,
    applyFilters,
    setSortBy,
    setViewMode,
    checkout,
    logout,
  };
};

// Mock products for development
function getMockProducts(): Product[] {
  return [
    {
      id: '1',
      name: 'Classic Cotton T-Shirt',
      brand: 'CONFIT Basics',
      price: 299,
      original_price: 399,
      image_url: 'https://images.unsplash.com/photo-1521572163441-5a607c634b10?w=400',
      category: 'tops',
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['White', 'Black', 'Navy'],
      in_stock: true,
    },
    {
      id: '2',
      name: 'Slim Fit Chinos',
      brand: 'CONFIT Essentials',
      price: 599,
      image_url: 'https://images.unsplash.com/photo-1473966968600-fef80458e4ec?w=400',
      category: 'bottoms',
      sizes: ['28', '30', '32', '34', '36'],
      colors: ['Beige', 'Navy', 'Olive'],
      in_stock: true,
    },
    {
      id: '3',
      name: 'Casual Sneakers',
      brand: 'CONFIT Footwear',
      price: 899,
      original_price: 1199,
      image_url: 'https://images.unsplash.com/photo-1460353584144-d90ab595a7df?w=400',
      category: 'footwear',
      sizes: ['38', '39', '40', '41', '42', '43', '44'],
      colors: ['White', 'Black'],
      in_stock: true,
    },
    {
      id: '4',
      name: 'Wool Blend Sweater',
      brand: 'CONFIT Knitwear',
      price: 799,
      image_url: 'https://images.unsplash.com/photo-1434389677669-e08b4deb3101?w=400',
      category: 'tops',
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['Grey', 'Navy', 'Burgundy'],
      in_stock: true,
    },
    {
      id: '5',
      name: 'Leather Belt',
      brand: 'CONFIT Accessories',
      price: 349,
      image_url: 'https://images.unsplash.com/photo-1553062407-98eebda072b3?w=400',
      category: 'accessories',
      sizes: ['S', 'M', 'L'],
      colors: ['Brown', 'Black'],
      in_stock: true,
    },
    {
      id: '6',
      name: 'Floral Summer Dress',
      brand: 'CONFIT Women',
      price: 999,
      original_price: 1299,
      image_url: 'https://images.unsplash.com/photo-1572804013309-59a40a1e4acc?w=400',
      category: 'dresses',
      sizes: ['XS', 'S', 'M', 'L'],
      colors: ['Blue Floral', 'Pink Floral'],
      in_stock: true,
    },
    {
      id: '7',
      name: 'Denim Jacket',
      brand: 'CONFIT Outerwear',
      price: 1199,
      image_url: 'https://images.unsplash.com/photo-1576995870887-6d61348202c8?w=400',
      category: 'outerwear',
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['Light Blue', 'Dark Blue'],
      in_stock: true,
    },
    {
      id: '8',
      name: 'Canvas Tote Bag',
      brand: 'CONFIT Bags',
      price: 449,
      image_url: 'https://images.unsplash.com/photo-1544816155-5df959178353?w=400',
      category: 'accessories',
      sizes: ['One Size'],
      colors: ['Natural', 'Black', 'Navy'],
      in_stock: true,
    },
  ];
}

export default useBeneficiaryShoppingViewModel;
