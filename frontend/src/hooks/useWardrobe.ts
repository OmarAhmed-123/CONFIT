/**
 * CONFIT Frontend - MY CLOSET Wardrobe Hooks
 * React hooks for virtual wardrobe functionality
 */

import { useState, useCallback, useEffect } from 'react';

// Types
interface WardrobeItem {
  id: string;
  name: string;
  category: string;
  subcategory?: string;
  colors: string[];
  patterns: string[];
  materials: string[];
  tags: string[];
  image_url?: string;
  is_favorite: boolean;
  times_worn?: number;
  last_worn?: string;
}

interface DuplicateAlert {
  existing_item_id: string;
  existing_item_name: string;
  similarity_score: number;
  message: string;
}

interface OutfitSuggestion {
  outfit_id: string;
  name: string;
  items: Array<{
    id: string;
    name: string;
    category: string;
    image_url?: string;
  }>;
  occasion?: string;
  color_harmony_score: number;
  style_match_score: number;
  tips: string[];
}

interface UseWardrobeOptions {
  onError?: (error: Error) => void;
}

interface UseWardrobeReturn {
  // State
  items: WardrobeItem[];
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;
  totalItems: number;
  quotaRemaining: number;
  outfitSuggestions: OutfitSuggestion[];
  
  // Actions
  addItem: (image: File, name?: string, category?: string) => Promise<WardrobeItem | null>;
  getItem: (itemId: string) => Promise<WardrobeItem | null>;
  listItems: (category?: string, limit?: number, offset?: number) => Promise<void>;
  updateItem: (itemId: string, updates: Partial<WardrobeItem>) => Promise<boolean>;
  deleteItem: (itemId: string) => Promise<boolean>;
  checkDuplicates: (productSku: string, productName?: string) => Promise<DuplicateAlert[]>;
  suggestOutfits: (occasion?: string) => Promise<OutfitSuggestion[]>;
  refreshItems: () => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/ai';

export function useWardrobe(options: UseWardrobeOptions = {}): UseWardrobeReturn {
  const { onError } = options;
  
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalItems, setTotalItems] = useState(0);
  const [quotaRemaining, setQuotaRemaining] = useState(50);
  const [outfitSuggestions, setOutfitSuggestions] = useState<OutfitSuggestion[]>([]);

  const addItem = useCallback(async (
    image: File,
    name?: string,
    category?: string
  ): Promise<WardrobeItem | null> => {
    setIsUploading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('image', image);
      if (name) formData.append('name', name);
      if (category) formData.append('category', category);
      
      const response = await fetch(`${API_BASE}/wardrobe/items`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        if (response.status === 429) {
          throw new Error('Daily upload limit exceeded.');
        }
        
        if (response.status === 403) {
          throw new Error('Wardrobe is full. Upgrade to add more items.');
        }
        
        throw new Error(errorData.detail || 'Failed to add item');
      }
      
      const item: WardrobeItem = await response.json();
      
      // Add to local state
      setItems(prev => [item, ...prev]);
      setTotalItems(prev => prev + 1);
      setQuotaRemaining(prev => Math.max(0, prev - 1));
      
      return item;
      
    } catch (err) {
      const error = err as Error;
      setError(error.message);
      onError?.(error);
      return null;
      
    } finally {
      setIsUploading(false);
    }
  }, [onError]);

  const getItem = useCallback(async (itemId: string): Promise<WardrobeItem | null> => {
    try {
      const response = await fetch(`${API_BASE}/wardrobe/items/${itemId}`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Item not found');
      }
      
      return response.json();
      
    } catch (err) {
      const error = err as Error;
      onError?.(error);
      return null;
    }
  }, [onError]);

  const listItems = useCallback(async (
    category?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<void> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (category) params.append('category', category);
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());
      
      const response = await fetch(`${API_BASE}/wardrobe/items?${params}`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to load wardrobe items');
      }
      
      const data: WardrobeItem[] = await response.json();
      
      if (offset === 0) {
        setItems(data);
      } else {
        setItems(prev => [...prev, ...data]);
      }
      
      setTotalItems(data.length);
      
    } catch (err) {
      const error = err as Error;
      setError(error.message);
      onError?.(error);
      
    } finally {
      setIsLoading(false);
    }
  }, [onError]);

  const updateItem = useCallback(async (
    itemId: string,
    updates: Partial<WardrobeItem>
  ): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/wardrobe/items/${itemId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update item');
      }
      
      const updatedItem: WardrobeItem = await response.json();
      
      // Update local state
      setItems(prev => prev.map(item => 
        item.id === itemId ? updatedItem : item
      ));
      
      return true;
      
    } catch (err) {
      const error = err as Error;
      setError(error.message);
      onError?.(error);
      return false;
    }
  }, [onError]);

  const deleteItem = useCallback(async (itemId: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/wardrobe/items/${itemId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete item');
      }
      
      // Remove from local state
      setItems(prev => prev.filter(item => item.id !== itemId));
      setTotalItems(prev => Math.max(0, prev - 1));
      setQuotaRemaining(prev => prev + 1);
      
      return true;
      
    } catch (err) {
      const error = err as Error;
      setError(error.message);
      onError?.(error);
      return false;
    }
  }, [onError]);

  const checkDuplicates = useCallback(async (
    productSku: string,
    productName?: string
  ): Promise<DuplicateAlert[]> => {
    try {
      const response = await fetch(`${API_BASE}/wardrobe/check-duplicates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({
          product_sku: productSku,
          product_name: productName,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to check duplicates');
      }
      
      const data = await response.json();
      return data.alerts || [];
      
    } catch (err) {
      const error = err as Error;
      onError?.(error);
      return [];
    }
  }, [onError]);

  const suggestOutfits = useCallback(async (
    occasion?: string
  ): Promise<OutfitSuggestion[]> => {
    try {
      const params = occasion ? `?occasion=${occasion}` : '';
      
      const response = await fetch(`${API_BASE}/wardrobe/outfits/suggestions${params}`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to get outfit suggestions');
      }
      
      const data = await response.json();
      const suggestions = data.outfits || [];
      
      setOutfitSuggestions(suggestions);
      return suggestions;
      
    } catch (err) {
      const error = err as Error;
      onError?.(error);
      return [];
    }
  }, [onError]);

  const refreshItems = useCallback(async () => {
    await listItems();
  }, [listItems]);

  // Load items on mount
  useEffect(() => {
    listItems();
  }, [listItems]);

  return {
    items,
    isLoading,
    isUploading,
    error,
    totalItems,
    quotaRemaining,
    outfitSuggestions,
    addItem,
    getItem,
    listItems,
    updateItem,
    deleteItem,
    checkDuplicates,
    suggestOutfits,
    refreshItems,
  };
}

function getAuthToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token') || '';
  }
  return '';
}

export default useWardrobe;
