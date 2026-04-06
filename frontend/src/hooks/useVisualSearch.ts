/**
 * CONFIT Frontend - Visual Search Hooks
 * React hooks for SNAP & STYLE visual search functionality
 */

import { useState, useCallback, useRef } from 'react';

// Types
interface DetectedAttributes {
  category?: string;
  subcategory?: string;
  colors: string[];
  patterns: string[];
  materials: string[];
  labels: string[];
}

interface SearchResult {
  product_id: string;
  sku: string;
  name: string;
  brand?: string;
  price?: number;
  currency: string;
  image_url?: string;
  similarity_score: number;
}

interface VisualSearchResponse {
  session_id: string;
  query_attributes?: DetectedAttributes;
  results: SearchResult[];
  total_results: number;
  processing_time_ms: number;
}

interface UseVisualSearchOptions {
  onError?: (error: Error) => void;
  minSimilarity?: number;
}

interface UseVisualSearchReturn {
  // State
  results: SearchResult[];
  detectedAttributes: DetectedAttributes | null;
  isSearching: boolean;
  error: string | null;
  totalResults: number;
  processingTime: number;
  sessionId: string | null;
  
  // Actions
  searchByImage: (image: File, filters?: SearchFilters) => Promise<SearchResult[]>;
  searchByText: (query: string, filters?: SearchFilters) => Promise<SearchResult[]>;
  clearResults: () => void;
}

interface SearchFilters {
  category?: string;
  max_price?: number;
  min_price?: number;
  limit?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/ai';

export function useVisualSearch(options: UseVisualSearchOptions = {}): UseVisualSearchReturn {
  const { onError, minSimilarity = 0.5 } = options;
  
  const [results, setResults] = useState<SearchResult[]>([]);
  const [detectedAttributes, setDetectedAttributes] = useState<DetectedAttributes | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [processingTime, setProcessingTime] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const searchByImage = useCallback(async (
    image: File,
    filters?: SearchFilters
  ): Promise<SearchResult[]> => {
    setIsSearching(true);
    setError(null);
    
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    try {
      const formData = new FormData();
      formData.append('image', image);
      
      // Add filters as query params
      const params = new URLSearchParams();
      if (filters?.category) params.append('category', filters.category);
      if (filters?.max_price) params.append('max_price', filters.max_price.toString());
      if (filters?.min_price) params.append('min_price', filters.min_price.toString());
      if (filters?.limit) params.append('limit', filters.limit.toString());
      
      const url = `${API_BASE}/visual-search/image${params.toString() ? `?${params}` : ''}`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: formData,
        signal: abortControllerRef.current.signal,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        if (response.status === 429) {
          throw new Error('Daily search limit exceeded. Please try again tomorrow.');
        }
        
        throw new Error(errorData.detail || 'Failed to search by image');
      }
      
      const data: VisualSearchResponse = await response.json();
      
      // Filter by minimum similarity
      const filteredResults = data.results.filter(
        r => r.similarity_score >= minSimilarity
      );
      
      setResults(filteredResults);
      setDetectedAttributes(data.query_attributes || null);
      setTotalResults(data.total_results);
      setProcessingTime(data.processing_time_ms);
      setSessionId(data.session_id);
      
      return filteredResults;
      
    } catch (err) {
      const error = err as Error;
      
      if (error.name === 'AbortError') {
        return [];
      }
      
      setError(error.message);
      onError?.(error);
      return [];
      
    } finally {
      setIsSearching(false);
      abortControllerRef.current = null;
    }
  }, [minSimilarity, onError]);

  const searchByText = useCallback(async (
    query: string,
    filters?: SearchFilters
  ): Promise<SearchResult[]> => {
    setIsSearching(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (filters?.category) params.append('category', filters.category);
      if (filters?.max_price) params.append('max_price', filters.max_price.toString());
      if (filters?.limit) params.append('limit', (filters.limit || 20).toString());
      
      const url = `${API_BASE}/visual-search/text${params.toString() ? `?${params}` : ''}`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ query }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to search by text');
      }
      
      const data: VisualSearchResponse = await response.json();
      
      const filteredResults = data.results.filter(
        r => r.similarity_score >= minSimilarity
      );
      
      setResults(filteredResults);
      setDetectedAttributes(data.query_attributes || null);
      setTotalResults(data.total_results);
      setProcessingTime(data.processing_time_ms);
      setSessionId(data.session_id);
      
      return filteredResults;
      
    } catch (err) {
      const error = err as Error;
      setError(error.message);
      onError?.(error);
      return [];
      
    } finally {
      setIsSearching(false);
    }
  }, [minSimilarity, onError]);

  const clearResults = useCallback(() => {
    setResults([]);
    setDetectedAttributes(null);
    setTotalResults(0);
    setProcessingTime(0);
    setSessionId(null);
    setError(null);
  }, []);

  return {
    results,
    detectedAttributes,
    isSearching,
    error,
    totalResults,
    processingTime,
    sessionId,
    searchByImage,
    searchByText,
    clearResults,
  };
}

function getAuthToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token') || '';
  }
  return '';
}

export default useVisualSearch;
