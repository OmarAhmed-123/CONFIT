/**
 * useLivePreview — WebSocket hook for real-time try-on streaming
 *
 * Manages a WebSocket connection to the backend for instant garment
 * switching without re-uploading the user photo.
 *
 * Protocol:
 * 1. Connect to ws://<backend>/api/virtual-tryon/ws/live
 * 2. Send user image once
 * 3. Send garment selections as they change
 * 4. Receive try-on results as frames
 */

import { useState, useCallback, useRef, useEffect } from 'react';

interface LivePreviewState {
    isConnected: boolean;
    isProcessing: boolean;
    resultImage: string | null;
    processingTimeMs: number;
    qualityScore: number;
    error: string | null;
    frameCount: number;
}

interface LivePreviewActions {
    connect: () => void;
    disconnect: () => void;
    setUserImage: (imageBase64: string) => void;
    switchGarment: (garmentImageUrl: string, garmentName: string) => void;
    reset: () => void;
}

export type UseLivePreviewReturn = LivePreviewState & LivePreviewActions;

const INITIAL_STATE: LivePreviewState = {
    isConnected: false,
    isProcessing: false,
    resultImage: null,
    processingTimeMs: 0,
    qualityScore: 0,
    error: null,
    frameCount: 0,
};

/** Build WebSocket URL from current location */
function getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // In dev mode, use the backend port directly
    const host =
        process.env.NODE_ENV === 'development'
            ? (() => {
                  try {
                      return new URL(process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000').host;
                  } catch {
                      return 'localhost:8000';
                  }
              })()
            : window.location.host;
    return `${protocol}//${host}/api/virtual-tryon/ws/live`;
}

export function useLivePreview(): UseLivePreviewReturn {
    const [state, setState] = useState<LivePreviewState>(INITIAL_STATE);
    const wsRef = useRef<WebSocket | null>(null);
    const userImageRef = useRef<string | null>(null);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            wsRef.current?.close();
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
        };
    }, []);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        try {
            const ws = new WebSocket(getWsUrl());
            wsRef.current = ws;

            ws.onopen = () => {
                setState(prev => ({ ...prev, isConnected: true, error: null }));
                console.log('[LivePreview] WebSocket connected');

                // Resend user image if we had one
                if (userImageRef.current) {
                    ws.send(JSON.stringify({ userImageBase64: userImageRef.current }));
                }
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    switch (data.type) {
                        case 'result':
                            setState(prev => ({
                                ...prev,
                                isProcessing: false,
                                resultImage: data.resultImage || prev.resultImage,
                                processingTimeMs: data.processingTimeMs || 0,
                                qualityScore: data.qualityScore || 0,
                                frameCount: prev.frameCount + 1,
                            }));
                            break;
                        case 'processing':
                            setState(prev => ({ ...prev, isProcessing: true }));
                            break;
                        case 'error':
                            setState(prev => ({
                                ...prev,
                                isProcessing: false,
                                error: data.error,
                            }));
                            break;
                    }
                } catch {
                    console.warn('[LivePreview] Failed to parse message');
                }
            };

            ws.onclose = () => {
                setState(prev => ({ ...prev, isConnected: false }));
                console.log('[LivePreview] WebSocket disconnected');
            };

            ws.onerror = () => {
                setState(prev => ({
                    ...prev,
                    isConnected: false,
                    error: 'Connection failed — backend may be offline',
                }));
            };
        } catch (err) {
            setState(prev => ({
                ...prev,
                error: 'Failed to create WebSocket connection',
            }));
        }
    }, []);

    const disconnect = useCallback(() => {
        wsRef.current?.close();
        wsRef.current = null;
        setState(prev => ({ ...prev, isConnected: false }));
    }, []);

    const setUserImage = useCallback((imageBase64: string) => {
        userImageRef.current = imageBase64;
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ userImageBase64: imageBase64 }));
        }
    }, []);

    const switchGarment = useCallback((garmentImageUrl: string, garmentName: string) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
            setState(prev => ({ ...prev, error: 'Not connected' }));
            return;
        }
        setState(prev => ({ ...prev, isProcessing: true, error: null }));
        wsRef.current.send(JSON.stringify({ garmentImageUrl, garmentName }));
    }, []);

    const reset = useCallback(() => {
        disconnect();
        userImageRef.current = null;
        setState(INITIAL_STATE);
    }, [disconnect]);

    return {
        ...state,
        connect,
        disconnect,
        setUserImage,
        switchGarment,
        reset,
    };
}
