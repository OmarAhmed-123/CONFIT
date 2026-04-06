/**
 * useVirtualTryOn — React hook for virtual try-on
 *
 * Priority chain:
 *   1. Backend API (/api/virtual-tryon/process) using VTON backends (FASHN / IDM-VTON)
 *   2. Error (no canvas overlay)
 */

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '@/lib/api';
import { getTryOnFetchTimeoutMs } from '@/lib/tryOnConstants';
import { formatTryOnFailureMessage } from '@/lib/tryOnErrors';

interface TryOnResult {
    success: boolean;
    resultImage?: string;
    message?: string;
    error?: string;
}

/**
 * Map a garment name string to a category using keyword matching.
 */
function detectCategoryFromName(name: string): string {
    const lower = name.toLowerCase();

    const map: [string[], string][] = [
        [['dress', 'gown', 'jumpsuit', 'romper'], 'dresses'],
        [['jacket', 'coat', 'blazer', 'cardigan', 'puffer', 'parka'], 'outerwear'],
        [['pants', 'trousers', 'jeans', 'shorts', 'skirt', 'leggings', 'culottes'], 'bottoms'],
        [['shoe', 'boot', 'sneaker', 'heel', 'loafer', 'flat', 'sandal'], 'shoes'],
        [['bag', 'purse', 'clutch', 'backpack', 'tote', 'satchel'], 'bags'],
        [['scarf', 'belt', 'earring', 'watch', 'sunglasses', 'hat', 'necklace', 'bracelet'], 'accessories'],
    ];

    for (const [keywords, category] of map) {
        if (keywords.some(kw => lower.includes(kw))) {
            return category;
        }
    }

    // Default to tops (most common)
    return 'tops';
}

export function useVirtualTryOn() {
    const [isProcessing, setIsProcessing] = useState(false);
    const [resultImage, setResultImage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const processVirtualTryOn = useCallback(async (
        userImageBase64: string,
        garmentImageUrl: string,
        garmentName: string,
        garmentCategory?: string,
    ): Promise<boolean> => {
        setIsProcessing(true);
        setError(null);
        setResultImage(null);

        const category = garmentCategory || detectCategoryFromName(garmentName);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), getTryOnFetchTimeoutMs());

        try {
            const response = await fetch(apiUrl('/api/tryon'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userImageBase64,
                    garmentImageUrl,
                    garmentName,
                    garmentCategory: category,
                }),
                signal: controller.signal,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const detail = errorData.detail;
                const msg =
                    typeof detail === 'string'
                        ? detail
                        : Array.isArray(detail)
                          ? detail.map((d: { msg?: string }) => d?.msg).filter(Boolean).join(' ')
                          : `Server error: ${response.status}`;
                throw new Error(msg || `Server error: ${response.status}`);
            }

            const envelope = await response.json();
            const data: TryOnResult = envelope?.data ?? envelope;

            if (!data?.success || !data?.resultImage) {
                throw new Error(data?.error || 'Failed to generate try-on image');
            }

            setResultImage(data.resultImage);
            toast.success("Try-On Complete!", {
                description: data.message || "Your virtual try-on is ready!",
                duration: 4000,
            });
            return true;

        } catch (backendErr) {
            const userMessage = formatTryOnFailureMessage(backendErr);
            setError(userMessage);
            toast.error("Try-On Failed", {
                description: userMessage,
                duration: 6000,
            });
            return false;
        } finally {
            clearTimeout(timeoutId);
            setIsProcessing(false);
        }
    }, []);

    const reset = useCallback(() => {
        setResultImage(null);
        setError(null);
        setIsProcessing(false);
    }, []);

    return {
        isProcessing,
        resultImage,
        error,
        processVirtualTryOn,
        reset,
    };
}
