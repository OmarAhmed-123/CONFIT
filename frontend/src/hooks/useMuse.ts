/**
 * CONFIT Frontend - MUSE Virtual Stylist Hooks
 * React hooks for MUSE AI chat functionality
 */

import { useState, useCallback, useRef, useEffect } from 'react';

// Types
interface MuseMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

interface OutfitRecommendation {
  outfit_id: string;
  title: string;
  items: Array<{
    id: string;
    sku: string;
    name: string;
    brand?: string;
    price?: number;
    image_url?: string;
  }>;
  total_price: number;
  occasion?: string;
  styling_tips: string[];
}

interface MuseChatResponse {
  reply: string;
  outfits: OutfitRecommendation[];
  follow_ups: string[];
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  session_id: string;
}

interface UseMuseOptions {
  language?: 'en' | 'ar';
  sessionId?: string;
  onError?: (error: Error) => void;
}

interface UseMuseReturn {
  // State
  messages: MuseMessage[];
  isLoading: boolean;
  error: string | null;
  sessionId: string | null;
  currentOutfits: OutfitRecommendation[];
  followUpQuestions: string[];
  
  // Actions
  sendMessage: (message: string) => Promise<void>;
  clearSession: () => void;
  loadHistory: () => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/ai';

export function useMuse(options: UseMuseOptions = {}): UseMuseReturn {
  const { language = 'en', sessionId: initialSessionId, onError } = options;
  
  const [messages, setMessages] = useState<MuseMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId || null);
  const [currentOutfits, setCurrentOutfits] = useState<OutfitRecommendation[]>([]);
  const [followUpQuestions, setFollowUpQuestions] = useState<string[]>([]);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    setIsLoading(true);
    setError(null);
    
    // Add user message immediately
    const userMessage: MuseMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    
    // Create abort controller for this request
    abortControllerRef.current = new AbortController();
    
    try {
      const response = await fetch(`${API_BASE}/muse/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({
          message,
          language,
          session_id: sessionId,
        }),
        signal: abortControllerRef.current.signal,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        if (response.status === 429) {
          throw new Error('Rate limit exceeded. Please wait before sending more messages.');
        }
        
        throw new Error(errorData.detail || 'Failed to get response from MUSE');
      }
      
      const data: MuseChatResponse = await response.json();
      
      // Add assistant message
      const assistantMessage: MuseMessage = {
        role: 'assistant',
        content: data.reply,
        timestamp: new Date().toISOString(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setSessionId(data.session_id);
      setCurrentOutfits(data.outfits);
      setFollowUpQuestions(data.follow_ups);
      
    } catch (err) {
      const error = err as Error;
      
      if (error.name === 'AbortError') {
        // Request was cancelled, don't show error
        return;
      }
      
      setError(error.message);
      onError?.(error);
      
      // Remove the user message on error
      setMessages(prev => prev.slice(0, -1));
      
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [language, sessionId, onError]);

  const clearSession = useCallback(async () => {
    if (sessionId) {
      try {
        await fetch(`${API_BASE}/muse/session/${sessionId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`,
          },
        });
      } catch (err) {
        console.error('Failed to clear session:', err);
      }
    }
    
    setMessages([]);
    setSessionId(null);
    setCurrentOutfits([]);
    setFollowUpQuestions([]);
    setError(null);
  }, [sessionId]);

  const loadHistory = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      const response = await fetch(`${API_BASE}/muse/session/${sessionId}/history`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  }, [sessionId]);

  return {
    messages,
    isLoading,
    error,
    sessionId,
    currentOutfits,
    followUpQuestions,
    sendMessage,
    clearSession,
    loadHistory,
  };
}

// Helper to get auth token
function getAuthToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token') || '';
  }
  return '';
}

export default useMuse;
