import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';
export type GenderPreference = 'male' | 'female' | 'unisex';

export interface UIState {
  theme: Theme;
  genderPreference: GenderPreference;
  sidebarOpen: boolean;
  mobileMenuOpen: boolean;
  searchOpen: boolean;
  notifications: Notification[];
  toasts: Toast[];
  isLoading: boolean;
  isOffline: boolean;
  
  // Actions
  setTheme: (theme: Theme) => void;
  setGenderPreference: (preference: GenderPreference) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleMobileMenu: () => void;
  setMobileMenuOpen: (open: boolean) => void;
  toggleSearch: () => void;
  setSearchOpen: (open: boolean) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setOffline: (offline: boolean) => void;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  actionUrl?: string;
}

export interface Toast {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  duration?: number;
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'system',
      genderPreference: 'unisex',
      sidebarOpen: true,
      mobileMenuOpen: false,
      searchOpen: false,
      notifications: [],
      toasts: [],
      isLoading: false,
      isOffline: !navigator.onLine,
      
      setTheme: (theme) => set({ theme }),
      
      setGenderPreference: (preference) => set({ genderPreference: preference }),
      
      toggleSidebar: () => set({ sidebarOpen: !set().sidebarOpen }),
      
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      
      toggleMobileMenu: () => set({ mobileMenuOpen: !set().mobileMenuOpen }),
      
      setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
      
      toggleSearch: () => set({ searchOpen: !set().searchOpen }),
      
      setSearchOpen: (open) => set({ searchOpen: open }),
      
      addNotification: (notification) =>
        set({
          notifications: [
            {
              ...notification,
              id: generateId(),
              createdAt: new Date().toISOString(),
              read: false,
            },
            ...set().notifications,
          ].slice(0, 50), // Keep last 50
        }),
        
      removeNotification: (id) =>
        set({ notifications: set().notifications.filter((n) => n.id !== id) }),
        
      clearNotifications: () => set({ notifications: [] }),
      
      addToast: (toast) => {
        const id = generateId();
        set({ toasts: [...set().toasts, { ...toast, id }] });
        
        // Auto remove after duration
        const duration = toast.duration ?? 5000;
        setTimeout(() => {
          set({ toasts: set().toasts.filter((t) => t.id !== id) });
        }, duration);
      },
      
      removeToast: (id) =>
        set({ toasts: set().toasts.filter((t) => t.id !== id) }),
        
      setLoading: (loading) => set({ isLoading: loading }),
      
      setOffline: (offline) => set({ isOffline: offline }),
    }),
    {
      name: 'confit-ui',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        genderPreference: state.genderPreference,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
);

// Listen for online/offline events
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => useUIStore.getState().setOffline(false));
  window.addEventListener('offline', () => useUIStore.getState().setOffline(true));
}
