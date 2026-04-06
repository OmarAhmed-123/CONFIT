/**
 * CONFIT Frontend - MIRROR Virtual Try-On Hooks
 * React hooks for virtual try-on functionality
 */

import { useState, useCallback, useRef, useEffect } from 'react';

// Types
type TryOnStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'expired';

interface TryOnSession {
  session_id: string;
  status: TryOnStatus;
  result_url?: string;
  quality_score: number;
  error_message?: string;
  cost_usd: number;
  latency_ms: number;
}

interface UseMirrorOptions {
  pollInterval?: number;
  maxPollTime?: number;
  onComplete?: (session: TryOnSession) => void;
  onError?: (error: Error) => void;
}

interface UseMirrorReturn {
  // State
  currentSession: TryOnSession | null;
  isUploading: boolean;
  isProcessing: boolean;
  error: string | null;
  sessions: TryOnSession[];
  
  // Actions
  startTryOn: (productId: string, productSku: string, personImage: File, garmentImage?: File) => Promise<TryOnSession | null>;
  checkStatus: (sessionId: string) => Promise<TryOnSession>;
  waitForResult: (sessionId: string, timeout?: number) => Promise<TryOnSession>;
  getSessions: () => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/ai';

export function useMirror(options: UseMirrorOptions = {}): UseMirrorReturn {
  const { 
    pollInterval = 3000, 
    maxPollTime = 120000,
    onComplete,
    onError 
  } = options;
  
  const [currentSession, setCurrentSession] = useState<TryOnSession | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<TryOnSession[]>([]);
  
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, []);

  const startTryOn = useCallback(async (
    productId: string,
    productSku: string,
    personImage: File,
    garmentImage?: File
  ): Promise<TryOnSession | null> => {
    setIsUploading(true);
    setError(null);
    setCurrentSession(null);
    
    try {
      const formData = new FormData();
      formData.append('product_id', productId);
      formData.append('product_sku', productSku);
      formData.append('person_image', personImage);
      
      if (garmentImage) {
        formData.append('garment_image', garmentImage);
      }
      
      const response = await fetch(`${API_BASE}/mirror/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        if (response.status === 429) {
          throw new Error('Daily try-on limit exceeded. Please try again tomorrow.');
        }
        
        throw new Error(errorData.detail || 'Failed to start try-on');
      }
      
      const session: TryOnSession = await response.json();
      setCurrentSession(session);
      
      // Start polling for result
      if (session.status === 'pending' || session.status === 'processing') {
        setIsProcessing(true);
        startTimeRef.current = Date.now();
        pollForResult(session.session_id);
      }
      
      return session;
      
    } catch (err) {
      const error = err as Error;
      setError(error.message);
      onError?.(error);
      return null;
      
    } finally {
      setIsUploading(false);
    }
  }, [onError]);

  const pollForResult = useCallback((sessionId: string) => {
    const poll = async () => {
      // Check if we've exceeded max poll time
      if (Date.now() - startTimeRef.current > maxPollTime) {
        setIsProcessing(false);
        setError('Try-on taking too long. Please check back later.');
        return;
      }
      
      try {
        const session = await checkStatus(sessionId);
        setCurrentSession(session);
        
        if (session.status === 'completed') {
          setIsProcessing(false);
          onComplete?.(session);
          return;
        }
        
        if (session.status === 'failed') {
          setIsProcessing(false);
          setError(session.error_message || 'Try-on failed');
          return;
        }
        
        // Continue polling
        pollTimeoutRef.current = setTimeout(poll, pollInterval);
        
      } catch (err) {
        setIsProcessing(false);
        const error = err as Error;
        setError(error.message);
        onError?.(error);
      }
    };
    
    poll();
  }, [maxPollTime, pollInterval, onComplete, onError]);

  const checkStatus = useCallback(async (sessionId: string): Promise<TryOnSession> => {
    const response = await fetch(`${API_BASE}/mirror/status/${sessionId}`, {
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to check try-on status');
    }
    
    return response.json();
  }, []);

  const waitForResult = useCallback(async (
    sessionId: string,
    timeout?: number
  ): Promise<TryOnSession> => {
    const response = await fetch(`${API_BASE}/mirror/wait/${sessionId}?timeout=${timeout || 120}`, {
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to wait for try-on result');
    }
    
    const session: TryOnSession = await response.json();
    setCurrentSession(session);
    
    if (session.status === 'completed') {
      onComplete?.(session);
    }
    
    return session;
  }, [onComplete]);

  const getSessions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/mirror/sessions`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (err) {
      console.error('Failed to get sessions:', err);
    }
  }, []);

  return {
    currentSession,
    isUploading,
    isProcessing,
    error,
    sessions,
    startTryOn,
    checkStatus,
    waitForResult,
    getSessions,
  };
}

function getAuthToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token') || '';
  }
  return '';
}

export default useMirror;
