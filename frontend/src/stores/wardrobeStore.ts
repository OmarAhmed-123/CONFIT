import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface WardrobeItem {
  id: string;
  name: string;
  category: 'tops' | 'bottoms' | 'dresses' | 'outerwear' | 'shoes' | 'accessories' | 'bags';
  subcategory?: string;
  color: string;
  colorFamily: string;
  pattern: 'solid' | 'striped' | 'floral' | 'plaid' | 'geometric' | 'other';
  material: string;
  brand?: string;
  image: string;
  tags: string[];
  occasions: string[];
  seasons: ('spring' | 'summer' | 'fall' | 'winter')[];
  purchaseDate?: string;
  price?: number;
  timesWorn: number;
  lastWorn?: string;
  isFavorite: boolean;
  notes?: string;
}

export interface WardrobeState {
  items: WardrobeItem[];
  selectedItems: string[];
  filter: WardrobeFilter;
  viewMode: 'grid' | 'list';
  
  // Actions
  addItem: (item: Omit<WardrobeItem, 'id' | 'timesWorn'>) => void;
  updateItem: (id: string, updates: Partial<WardrobeItem>) => void;
  removeItem: (id: string) => void;
  toggleFavorite: (id: string) => void;
  incrementTimesWorn: (id: string) => void;
  setSelectedItems: (ids: string[]) => void;
  toggleSelectItem: (id: string) => void;
  clearSelection: () => void;
  setFilter: (filter: Partial<WardrobeFilter>) => void;
  setViewMode: (mode: 'grid' | 'list') => void;
  getFilteredItems: () => WardrobeItem[];
  getItemsByCategory: (category: WardrobeItem['category']) => WardrobeItem[];
}

interface WardrobeFilter {
  category?: WardrobeItem['category'];
  colorFamily?: string;
  seasons?: WardrobeItem['seasons'];
  occasions?: string[];
  isFavorite?: boolean;
  search?: string;
}

export const useWardrobeStore = create<WardrobeState>()(
  persist(
    (set, get) => ({
      items: [],
      selectedItems: [],
      filter: {},
      viewMode: 'grid',
      
      addItem: (item) => {
        const id = `wardrobe-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        set({ items: [...get().items, { ...item, id, timesWorn: 0 }] });
      },
      
      updateItem: (id, updates) =>
        set({
          items: get().items.map((item) =>
            item.id === id ? { ...item, ...updates } : item
          ),
        }),
        
      removeItem: (id) =>
        set({
          items: get().items.filter((item) => item.id !== id),
          selectedItems: get().selectedItems.filter((itemId) => itemId !== id),
        }),
        
      toggleFavorite: (id) =>
        set({
          items: get().items.map((item) =>
            item.id === id ? { ...item, isFavorite: !item.isFavorite } : item
          ),
        }),
        
      incrementTimesWorn: (id) =>
        set({
          items: get().items.map((item) =>
            item.id === id
              ? {
                  ...item,
                  timesWorn: item.timesWorn + 1,
                  lastWorn: new Date().toISOString(),
                }
              : item
          ),
        }),
        
      setSelectedItems: (ids) => set({ selectedItems: ids }),
      
      toggleSelectItem: (id) => {
        const selected = get().selectedItems;
        if (selected.includes(id)) {
          set({ selectedItems: selected.filter((itemId) => itemId !== id) });
        } else {
          set({ selectedItems: [...selected, id] });
        }
      },
      
      clearSelection: () => set({ selectedItems: [] }),
      
      setFilter: (filter) => set({ filter: { ...get().filter, ...filter } }),
      
      setViewMode: (mode) => set({ viewMode: mode }),
      
      getFilteredItems: () => {
        const { items, filter } = get();
        return items.filter((item) => {
          if (filter.category && item.category !== filter.category) return false;
          if (filter.colorFamily && item.colorFamily !== filter.colorFamily) return false;
          if (filter.seasons && !filter.seasons.some((s) => item.seasons.includes(s))) return false;
          if (filter.occasions && !filter.occasions.some((o) => item.occasions.includes(o))) return false;
          if (filter.isFavorite !== undefined && item.isFavorite !== filter.isFavorite) return false;
          if (filter.search) {
            const search = filter.search.toLowerCase();
            return (
              item.name.toLowerCase().includes(search) ||
              item.brand?.toLowerCase().includes(search) ||
              item.tags.some((t) => t.toLowerCase().includes(search))
            );
          }
          return true;
        });
      },
      
      getItemsByCategory: (category) =>
        get().items.filter((item) => item.category === category),
    }),
    {
      name: 'confit-wardrobe',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
