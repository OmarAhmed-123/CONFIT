/**
 * Rotation ViewModel
 *
 * Manages state for the interactive 360° rotation viewer:
 * fetches frames from the backend, handles drag/touch rotation,
 * and controls auto-rotation animation.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import type {
    RotationRequestPayload,
    RotationResponsePayload,
    ViewerFrame,
} from '@/models/TryOnModel';

import { apiUrl } from '@/lib/api';

const DEFAULT_FRAME_COUNT = 36;

export function useRotationViewModel() {
    const [frames, setFrames] = useState<ViewerFrame[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [isAutoPlaying, setIsAutoPlaying] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const autoPlayRef = useRef<ReturnType<typeof setInterval> | null>(null);

    /* ── Generate frames from backend ────────────────────────── */

    const generateRotation = useCallback(async (
        sourceImageBase64: string,
        frameCount: number = DEFAULT_FRAME_COUNT,
    ): Promise<boolean> => {
        setIsLoading(true);
        setError(null);
        setFrames([]);
        setCurrentIndex(0);

        try {
            const payload: RotationRequestPayload = {
                sourceImageBase64,
                frameCount,
            };

            const response = await fetch(apiUrl('/api/rotation'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Server error: ${response.status}`);
            }

            const data: RotationResponsePayload = await response.json();

            if (!data.success || data.frames.length === 0) {
                throw new Error(data.error || 'No frames returned');
            }

            const angleStep = 360 / data.frames.length;
            const viewerFrames: ViewerFrame[] = data.frames.map((uri, idx) => ({
                index: idx,
                angleDeg: idx * angleStep,
                dataUri: uri,
            }));

            setFrames(viewerFrames);
            toast.success('360° View Ready', {
                description: `${viewerFrames.length} frames generated. Drag to rotate!`,
                duration: 3000,
            });
            return true;

        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Rotation generation failed';

            /* Fallback: create a single-frame "rotation" from the source */
            if (
                msg.includes('Failed to fetch') ||
                msg.includes('NetworkError') ||
                msg.includes('ERR_CONNECTION_REFUSED')
            ) {
                const fallbackFrames: ViewerFrame[] = [{
                    index: 0,
                    angleDeg: 0,
                    dataUri: sourceImageBase64,
                }];
                setFrames(fallbackFrames);
                toast.info('Backend Offline', {
                    description: 'Showing static view. Start the backend for full 360° rotation.',
                    duration: 4000,
                });
                return true;
            }

            setError(msg);
            toast.error('Rotation Failed', { description: msg });
            return false;

        } finally {
            setIsLoading(false);
        }
    }, []);

    /* ── Manual angle control ────────────────────────────────── */

    const setAngle = useCallback((index: number) => {
        if (frames.length === 0) return;
        const clamped = ((index % frames.length) + frames.length) % frames.length;
        setCurrentIndex(clamped);
    }, [frames.length]);

    const rotateBy = useCallback((delta: number) => {
        setCurrentIndex(prev => {
            if (frames.length === 0) return 0;
            return ((prev + delta) % frames.length + frames.length) % frames.length;
        });
    }, [frames.length]);

    /* ── Auto-rotation ───────────────────────────────────────── */

    const toggleAutoPlay = useCallback(() => {
        setIsAutoPlaying(prev => !prev);
    }, []);

    useEffect(() => {
        if (isAutoPlaying && frames.length > 1) {
            autoPlayRef.current = setInterval(() => {
                setCurrentIndex(prev => (prev + 1) % frames.length);
            }, 80);
        }

        return () => {
            if (autoPlayRef.current) {
                clearInterval(autoPlayRef.current);
                autoPlayRef.current = null;
            }
        };
    }, [isAutoPlaying, frames.length]);

    /* ── Reset ───────────────────────────────────────────────── */

    const reset = useCallback(() => {
        setFrames([]);
        setCurrentIndex(0);
        setIsAutoPlaying(false);
        setError(null);
        if (autoPlayRef.current) {
            clearInterval(autoPlayRef.current);
            autoPlayRef.current = null;
        }
    }, []);

    /* ── Computed values ─────────────────────────────────────── */

    const currentFrame = frames.length > 0 ? frames[currentIndex] : null;
    const currentAngleDeg = currentFrame?.angleDeg ?? 0;

    return {
        frames,
        currentIndex,
        currentFrame,
        currentAngleDeg,
        isLoading,
        isAutoPlaying,
        error,
        generateRotation,
        setAngle,
        rotateBy,
        toggleAutoPlay,
        reset,
    };
}
