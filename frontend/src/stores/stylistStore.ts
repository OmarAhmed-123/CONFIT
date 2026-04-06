import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  suggestions?: StyleSuggestion[];
  products?: ProductRecommendation[];
}

export interface StyleSuggestion {
  id: string;
  type: 'item' | 'outfit' | 'tip';
  title: string;
  description: string;
  image?: string;
  confidence: number;
}

export interface ProductRecommendation {
  id: string;
  productId: string;
  name: string;
  brand: string;
  price: number;
  image: string;
  matchScore: number;
}

export interface StylistState {
  messages: ChatMessage[];
  isTyping: boolean;
  conversationId: string | null;
  styleProfile: StyleProfile | null;
  preferences: StylistPreferences;
  
  // Actions
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  setTyping: (typing: boolean) => void;
  setConversationId: (id: string | null) => void;
  clearConversation: () => void;
  setStyleProfile: (profile: StyleProfile) => void;
  updatePreferences: (prefs: Partial<StylistPreferences>) => void;
}

export interface StyleProfile {
  bodyType?: string;
  skinTone?: string;
  colorSeason?: string;
  preferredStyle?: string;
  preferredStyleWords?: string[];
  fitPreferences?: string[];
  avoidedStyles?: string[];
}

export interface StylistPreferences {
  budget: 'low' | 'medium' | 'high' | 'luxury';
  sustainabilityPriority: boolean;
  preferredBrands: string[];
  avoidedColors: string[];
  sizing: {
    tops?: string;
    bottoms?: string;
    shoes?: string;
  };
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

export const useStylistStore = create<StylistState>((set, get) => ({
  messages: [],
  isTyping: false,
  conversationId: null,
  styleProfile: null,
  preferences: {
    budget: 'medium',
    sustainabilityPriority: false,
    preferredBrands: [],
    avoidedColors: [],
    sizing: {},
  },
  
  addMessage: (message) =>
    set({
      messages: [
        ...get().messages,
        {
          ...message,
          id: generateId(),
          timestamp: new Date().toISOString(),
        },
      ],
    }),
    
  setTyping: (typing) => set({ isTyping: typing }),
  
  setConversationId: (id) => set({ conversationId: id }),
  
  clearConversation: () =>
    set({
      messages: [],
      conversationId: null,
      isTyping: false,
    }),
    
  setStyleProfile: (profile) => set({ styleProfile: profile }),
  
  updatePreferences: (prefs) =>
    set({ preferences: { ...get().preferences, ...prefs } }),
}));
