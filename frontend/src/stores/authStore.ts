import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * Local session shape for CONFIT (JWT from FastAPI — no Supabase).
 * Kept compatible with optional future sync to AuthContext storage.
 */
export interface LocalSession {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
}

export interface LocalUser {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  roles?: string[];
}

export interface AuthState {
  user: LocalUser | null;
  session: LocalSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  setUser: (user: LocalUser | null) => void;
  setSession: (session: LocalSession | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  logout: () => void;
  reset: () => void;
}

const initialState = {
  user: null,
  session: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      ...initialState,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
          isLoading: false,
        }),

      setSession: (session) =>
        set({
          session,
          isAuthenticated: !!session,
          isLoading: false,
        }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error, isLoading: false }),

      logout: () =>
        set({
          ...initialState,
          isLoading: false,
        }),

      reset: () => set(initialState),
    }),
    {
      name: 'confit-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        session: state.session,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
