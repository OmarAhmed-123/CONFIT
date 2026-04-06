import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface OutfitItem {
  id: string;
  wardrobeItemId: string;
  name: string;
  image: string;
  category: string;
  position: { x: number; y: number };
  scale: number;
  rotation: number;
  zIndex: number;
}

export interface SavedOutfit {
  id: string;
  name: string;
  description?: string;
  items: OutfitItem[];
  thumbnail: string;
  occasions: string[];
  seasons: ('spring' | 'summer' | 'fall' | 'winter')[];
  tags: string[];
  isFavorite: boolean;
  createdAt: string;
  updatedAt: string;
  timesWorn: number;
}

export interface OutfitBuilderState {
  canvasItems: OutfitItem[];
  savedOutfits: SavedOutfit[];
  selectedItemId: string | null;
  budgetLimit: number | null;
  currentBudget: number;
  
  // Actions
  addToCanvas: (item: Omit<OutfitItem, 'id' | 'position' | 'scale' | 'rotation' | 'zIndex'>) => void;
  removeFromCanvas: (id: string) => void;
  updateItemPosition: (id: string, position: { x: number; y: number }) => void;
  updateItemTransform: (id: string, transforms: Partial<Pick<OutfitItem, 'scale' | 'rotation' | 'zIndex'>>) => void;
  selectItem: (id: string | null) => void;
  clearCanvas: () => void;
  saveOutfit: (name: string, description?: string, occasions?: string[], seasons?: ('spring' | 'summer' | 'fall' | 'winter')[]) => void;
  updateOutfit: (id: string, updates: Partial<SavedOutfit>) => void;
  deleteOutfit: (id: string) => void;
  loadOutfit: (id: string) => void;
  duplicateOutfit: (id: string) => void;
  setBudgetLimit: (limit: number | null) => void;
  calculateCurrentBudget: () => void;
}

export const useOutfitStore = create<OutfitBuilderState>()(
  persist(
    (set, get) => ({
      canvasItems: [],
      savedOutfits: [],
      selectedItemId: null,
      budgetLimit: null,
      currentBudget: 0,
      
      addToCanvas: (item) => {
        const id = `canvas-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newItem: OutfitItem = {
          ...item,
          id,
          position: { x: 50, y: 50 },
          scale: 1,
          rotation: 0,
          zIndex: get().canvasItems.length,
        };
        set({ canvasItems: [...get().canvasItems, newItem] });
        get().calculateCurrentBudget();
      },
      
      removeFromCanvas: (id) => {
        set({
          canvasItems: get().canvasItems.filter((item) => item.id !== id),
          selectedItemId: get().selectedItemId === id ? null : get().selectedItemId,
        });
        get().calculateCurrentBudget();
      },
      
      updateItemPosition: (id, position) =>
        set({
          canvasItems: get().canvasItems.map((item) =>
            item.id === id ? { ...item, position } : item
          ),
        }),
        
      updateItemTransform: (id, transforms) =>
        set({
          canvasItems: get().canvasItems.map((item) =>
            item.id === id ? { ...item, ...transforms } : item
          ),
        }),
        
      selectItem: (id) => set({ selectedItemId: id }),
      
      clearCanvas: () => set({ canvasItems: [], selectedItemId: null }),
      
      saveOutfit: (name, description, occasions = [], seasons = []) => {
        const { canvasItems } = get();
        const id = `outfit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const now = new Date().toISOString();
        
        const newOutfit: SavedOutfit = {
          id,
          name,
          description,
          items: canvasItems,
          thumbnail: canvasItems[0]?.image || '',
          occasions,
          seasons,
          tags: [],
          isFavorite: false,
          createdAt: now,
          updatedAt: now,
          timesWorn: 0,
        };
        
        set({ savedOutfits: [...get().savedOutfits, newOutfit] });
      },
      
      updateOutfit: (id, updates) =>
        set({
          savedOutfits: get().savedOutfits.map((outfit) =>
            outfit.id === id
              ? { ...outfit, ...updates, updatedAt: new Date().toISOString() }
              : outfit
          ),
        }),
        
      deleteOutfit: (id) =>
        set({ savedOutfits: get().savedOutfits.filter((outfit) => outfit.id !== id) }),
        
      loadOutfit: (id) => {
        const outfit = get().savedOutfits.find((o) => o.id === id);
        if (outfit) {
          set({ canvasItems: outfit.items, selectedItemId: null });
          get().calculateCurrentBudget();
        }
      },
      
      duplicateOutfit: (id) => {
        const outfit = get().savedOutfits.find((o) => o.id === id);
        if (outfit) {
          const newId = `outfit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newOutfit: SavedOutfit = {
            ...outfit,
            id: newId,
            name: `${outfit.name} (Copy)`,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            timesWorn: 0,
          };
          set({ savedOutfits: [...get().savedOutfits, newOutfit] });
        }
      },
      
      setBudgetLimit: (limit) => set({ budgetLimit: limit }),
      
      calculateCurrentBudget: () => {
        // This would integrate with product prices if items are from products
        const total = get().canvasItems.length * 100; // Placeholder
        set({ currentBudget: total });
      },
    }),
    {
      name: 'confit-outfits',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
