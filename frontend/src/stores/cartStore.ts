import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface CartItem {
  id: string;
  productId: string;
  name: string;
  brand: string;
  price: number;
  salePrice?: number;
  image: string;
  size: string;
  color: string;
  quantity: number;
  stock: number;
}

export interface CartState {
  items: CartItem[];
  isOpen: boolean;
  budgetLimit: number | null;
  
  // Computed
  totalItems: () => number;
  subtotal: () => number;
  savings: () => number;
  tax: () => number;
  total: () => number;
  budgetRemaining: () => number | null;
  
  // Actions
  addItem: (item: Omit<CartItem, 'id'>) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;
  toggleCart: () => void;
  setBudgetLimit: (limit: number | null) => void;
  isInCart: (productId: string, size: string, color: string) => boolean;
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      isOpen: false,
      budgetLimit: null,
      
      totalItems: () => get().items.reduce((sum, item) => sum + item.quantity, 0),
      
      subtotal: () =>
        get().items.reduce((sum, item) => {
          const price = item.salePrice ?? item.price;
          return sum + price * item.quantity;
        }, 0),
        
      savings: () =>
        get().items.reduce((sum, item) => {
          if (item.salePrice) {
            return sum + (item.price - item.salePrice) * item.quantity;
          }
          return sum;
        }, 0),
        
      tax: () => get().subtotal() * 0.08, // 8% tax
      
      total: () => get().subtotal() + get().tax(),
      
      budgetRemaining: () => {
        const { budgetLimit } = get();
        if (!budgetLimit) return null;
        return budgetLimit - get().total();
      },
      
      addItem: (item) => {
        if (item.stock !== undefined && item.stock <= 0) return;
        const items = get().items;
        const existingIndex = items.findIndex(
          (i) => i.productId === item.productId && i.size === item.size && i.color === item.color
        );
        
        if (existingIndex > -1) {
          const newItems = [...items];
          newItems[existingIndex].quantity += item.quantity;
          set({ items: newItems });
        } else {
          set({ items: [...items, { ...item, id: generateId() }] });
        }
      },
      
      removeItem: (id) =>
        set({ items: get().items.filter((item) => item.id !== id) }),
        
      updateQuantity: (id, quantity) =>
        set((state) => ({
          items:
            quantity <= 0
              ? state.items.filter((item) => item.id !== id)
              : state.items.map((item) =>
                  item.id === id ? { ...item, quantity: Math.min(quantity, item.stock || 999) } : item
                ),
        })),
        
      clearCart: () => set({ items: [] }),
      
      toggleCart: () => set({ isOpen: !get().isOpen }),
      
      setBudgetLimit: (limit) => set({ budgetLimit: limit }),
      
      isInCart: (productId, size, color) =>
        get().items.some((i) => i.productId === productId && i.size === size && i.color === color),
    }),
    {
      name: 'confit-cart',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        items: state.items,
        budgetLimit: state.budgetLimit,
      }),
    }
  )
);
