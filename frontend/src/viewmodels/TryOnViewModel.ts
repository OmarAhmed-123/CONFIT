/**
 * Try-On ViewModel
 *
 * Encapsulates state and API calls for the virtual try-on flow.
 *
 * Processing: FastAPI `POST /api/virtual-tryon/process` (local backend).
 * Optional: append a compact entry to browser local history via
 * `appendTryOnSession` (offline substitute for cloud session tables).
 */

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import type {
    TryOnRequestPayload,
    TryOnResponsePayload,
    TryOnStage,
} from '@/models/TryOnModel';

import { apiUrl } from '@/lib/api';
import {
  getTryOnPollMs,
  getTryOnMaxWaitMs,
  isTryOnLocalHistoryEnabled,
} from '@/lib/env';
import { appendTryOnSession } from '@/lib/tryOnLocalSessions';
import { getTryOnFetchTimeoutMs, getTryOnPreviewTimeoutMs } from '@/lib/tryOnConstants';
import { formatTryOnFailureMessage } from '@/lib/tryOnErrors';
import { mirrorService } from '@/services/aiFeaturesService';

/* ── Category detector ────────────────────────────────────────── */

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

    return 'tops';
}

function makeFallbackGarmentDataUri(garmentName: string, garmentCategory?: string): string {
    const category = (garmentCategory || detectCategoryFromName(garmentName) || 'tops').toUpperCase();
    const safeName = (garmentName || 'Garment').replace(/[<>&]/g, '');
    const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1f2937"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" fill="url(#g)"/>
  <rect x="212" y="190" width="600" height="644" rx="56" fill="#e5e7eb"/>
  <rect x="292" y="250" width="440" height="120" rx="24" fill="#cbd5e1"/>
  <text x="512" y="525" text-anchor="middle" fill="#111827" font-family="Arial, sans-serif" font-size="54" font-weight="700">${category}</text>
  <text x="512" y="585" text-anchor="middle" fill="#1f2937" font-family="Arial, sans-serif" font-size="30">${safeName}</text>
</svg>`;
    if (typeof window !== 'undefined' && typeof window.btoa === 'function') {
        return `data:image/svg+xml;base64,${window.btoa(unescape(encodeURIComponent(svg)))}`;
    }
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

/* ── Backend MCP try-on ───────────────────────────────────────── */

async function processViaBackend(
    userImageBase64: string,
    garmentImageUrl: string,
    garmentName: string,
    garmentCategory?: string,
): Promise<TryOnResponsePayload> {
    const payload: TryOnRequestPayload = {
        userImageBase64,
        garmentImageUrl,
        garmentName,
        garmentCategory,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), getTryOnPreviewTimeoutMs());

    try {
        const response = await fetch(apiUrl('/api/tryon/render'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal,
        });

        const envelope = await response.json();
        if (!response.ok) {
            const detail = envelope?.detail || envelope || {};
            const err = new Error(
                detail?.message || detail?.error || `Server error: ${response.status}`
            ) as Error & { failureKind?: string | null };
            err.failureKind = detail?.error_code || null;
            throw err;
        }
        if (envelope?.success === false) {
            throw new Error(envelope?.error || 'Failed to enqueue final render');
        }
        const data: TryOnResponsePayload = envelope?.data ?? envelope;
        return data;
    } finally {
        clearTimeout(timeoutId);
    }
}

async function processPreviewViaBackend(
    userImageBase64: string,
    garmentImageUrl: string,
    garmentName: string,
    garmentCategory?: string,
): Promise<TryOnResponsePayload> {
    const payload: TryOnRequestPayload = {
        userImageBase64,
        garmentImageUrl,
        garmentName,
        garmentCategory,
    };

    const controller = new AbortController();
    // Keep preview timeout aligned with configured try-on timeout.
    // A hard 45s cap causes false client aborts on CPU first-run warmup.
    const timeoutId = setTimeout(() => controller.abort(), getTryOnFetchTimeoutMs());

    try {
        const response = await fetch(apiUrl('/api/tryon/preview/live'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal,
        });

        const envelope = await response.json();
        if (!response.ok) {
            const detail = envelope?.detail || envelope || {};
            const err = new Error(
                detail?.message || detail?.error || `Server error: ${response.status}`
            ) as Error & { failureKind?: string | null };
            err.failureKind = detail?.error_code || null;
            throw err;
        }
        if (envelope?.success === false) {
            throw new Error(envelope?.error || 'Failed to generate preview image');
        }
        const data: TryOnResponsePayload = envelope?.data ?? envelope;
        const image = data?.resultImage ?? data?.image_url;
        if (!data?.success || !image) {
            const err = new Error(data?.error || 'Failed to generate preview image') as Error & {
                failureKind?: string | null;
            };
            err.failureKind = data?.failureKind ?? null;
            throw err;
        }
        return data;
    } finally {
        clearTimeout(timeoutId);
    }
}

/* ── ViewModel Hook ───────────────────────────────────────────── */

export function useTryOnViewModel() {
    const [stage, setStage] = useState<TryOnStage>('idle');
    const [isProcessing, setIsProcessing] = useState(false);
    const [resultImage, setResultImage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [stageLabel, setStageLabel] = useState<string>('');
    const [lastFailureKind, setLastFailureKind] = useState<string | null>(null);
    const [lastBackendUsed, setLastBackendUsed] = useState<string | null>(null);
    const [finalNotice, setFinalNotice] = useState<string | null>(null);
    const [previewOnlyMode, setPreviewOnlyMode] = useState(false);

    const pollJobUntilDone = useCallback(async (jobId: string): Promise<string> => {
        const pollMs = getTryOnPollMs();
        const maxWaitMs = getTryOnMaxWaitMs();
        const maxAttempts = Math.max(1, Math.floor(maxWaitMs / pollMs));
        for (let i = 0; i < maxAttempts; i += 1) {
            const res = await fetch(apiUrl(`/api/tryon/render/${jobId}`));
            const envelope = await res.json().catch(() => ({}));
            if (!res.ok || envelope?.success === false) {
                throw new Error('Could not read render job status.');
            }
            const data = envelope ?? {};
            const status = data?.status;
            if (status === 'completed' && (data?.image_url || data?.imageUrl)) {
                return (data.image_url || data.imageUrl) as string;
            }
            if (status === 'failed') {
                const err = new Error(data?.message || 'Final render failed') as Error & {
                    failureKind?: string | null;
                };
                err.failureKind = data?.error_code || data?.failure_kind || null;
                throw err;
            }
            if (status === 'cancelled') {
                throw new Error('Final render was cancelled.');
            }
            await new Promise((r) => setTimeout(r, pollMs));
        }
        throw new Error('Final render timed out.');
    }, []);

    const processVirtualTryOn = useCallback(async (
        userImageBase64: string,
        garmentImageUrl: string,
        garmentName: string,
        garmentCategory?: string,
        productMeta?: { id: string; name: string },
    ): Promise<boolean> => {
        setIsProcessing(true);
        setError(null);
        setResultImage(null);
        setStage('preview_loading');
        setStageLabel('Generating live preview...');
        setLastFailureKind(null);
        setFinalNotice(null);
        setPreviewOnlyMode(false);

        const category = garmentCategory || detectCategoryFromName(garmentName);

        try {
            const diagRes = await fetch(apiUrl('/api/virtual-tryon/diagnostics'));
            const diagEnvelope = await diagRes.json().catch(() => ({}));
            const diag = diagEnvelope?.data ?? diagEnvelope;
            const finalAvailable = Boolean(diag?.final_render_available);

            const preview = await processPreviewViaBackend(
                userImageBase64,
                garmentImageUrl,
                garmentName,
                category,
            );
            setResultImage(preview.resultImage ?? preview.image_url ?? null);
            setLastBackendUsed('preview_local');
            setStage('preview_ready');
            setStageLabel('Live preview ready');

            if (!finalAvailable) {
                setStage('preview_only_mode');
                setPreviewOnlyMode(true);
                setFinalNotice('Live preview is ready. High-fidelity final render requires GPU backend.');
                return true;
            }

            setStage('final_queued');
            setStageLabel('Final render queued...');
            const renderJob = await processViaBackend(
                userImageBase64,
                garmentImageUrl,
                garmentName,
                category,
            );
            const jobId = (renderJob as { job_id?: string; jobId?: string }).job_id || (renderJob as { jobId?: string }).jobId;
            if (!jobId) {
                throw new Error('Render job id is missing from backend response.');
            }

            setStage('final_rendering');
            setStageLabel('Rendering final output...');
            const finalImage = await pollJobUntilDone(jobId);

            setStage('final_ready');
            setStageLabel('Final render ready');
            setResultImage(finalImage ?? null);
            setLastBackendUsed('neural_final');
            if (
                finalImage &&
                productMeta?.id &&
                isTryOnLocalHistoryEnabled()
            ) {
                void appendTryOnSession({
                    resultImageDataUrl: finalImage,
                    productId: productMeta.id,
                    productName: productMeta.name,
                });
            }
            toast.success('Try-On Complete!', {
                description: 'Your virtual try-on is ready!',
                duration: 4000,
            });
            return true;
        } catch (backendErr) {
            const failureKind =
                (backendErr as { failureKind?: string | null })?.failureKind ?? null;

            // Resilience fallback: if external garment URL cannot be fetched by backend
            // (DNS/network/CDN issue), retry once with an inline garment placeholder.
            if (failureKind === 'garment_fetch') {
                try {
                    const fallbackUri = makeFallbackGarmentDataUri(garmentName, category);
                    const preview = await processPreviewViaBackend(
                        userImageBase64,
                        fallbackUri,
                        garmentName,
                        category,
                    );
                    setResultImage(preview.resultImage ?? preview.image_url ?? null);
                    setLastBackendUsed('preview_inline_fallback');
                    setStage('preview_only_mode');
                    setStageLabel('Preview ready (fallback garment)');
                    setPreviewOnlyMode(true);
                    setFinalNotice('External garment image was unreachable, so a safe inline fallback garment was used.');
                    toast.message('Preview ready with fallback garment', {
                        description: 'Network could not reach the original garment image URL.',
                    });
                    return true;
                } catch {
                    // Continue to regular error handling path if fallback also fails.
                }
            }

            const userMessage = formatTryOnFailureMessage(backendErr);
            if (failureKind === 'FINAL_RENDER_UNAVAILABLE') {
                setStage('preview_only_mode');
                setStageLabel('Preview ready (final unavailable)');
                setFinalNotice(
                    'Live preview is available now. High-fidelity render requires GPU render backend.'
                );
                setPreviewOnlyMode(true);
                setLastFailureKind(failureKind);
                toast.message('Preview ready', {
                    description:
                        'High-fidelity render requires CUDA GPU or configured remote neural backend.',
                });
                return true;
            }
            setStage('final_failed');
            setStageLabel('');
            setError(userMessage);
            setLastFailureKind(failureKind);
            toast.error('Try-On Failed', { description: userMessage, duration: 6000 });
            return false;
        } finally {
            setIsProcessing(false);
        }
    }, [pollJobUntilDone]);

    /* ── v1 MIRROR async try-on ─────────────────────────────── */
    const processMirrorTryOn = useCallback(async (
        userPhotoFile: File,
        productVariantId: string,
        category: string = 'upper_body',
        productMeta?: { id: string; name: string },
    ): Promise<boolean> => {
        setIsProcessing(true);
        setError(null);
        setResultImage(null);
        setStage('preview_loading');
        setStageLabel('Starting virtual try-on...');
        setLastFailureKind(null);
        setFinalNotice(null);

        try {
            // 1. Start async try-on
            const startResult = await mirrorService.startTryOn(userPhotoFile, productVariantId, category);
            setStage('final_rendering');
            setStageLabel('Processing your try-on...');

            // 2. Poll until ready
            const result = await mirrorService.pollUntilReady(
                startResult.task_id,
                (status) => setStageLabel(`Status: ${status}`),
            );

            if (result.status === 'completed' && result.result_image_url) {
                setResultImage(result.result_image_url);
                setStage('final_ready');
                setStageLabel('Try-on complete!');
                setLastBackendUsed('mirror_v1');

                if (productMeta?.id && isTryOnLocalHistoryEnabled()) {
                    void appendTryOnSession({
                        resultImageDataUrl: result.result_image_url,
                        productId: productMeta.id,
                        productName: productMeta.name,
                    });
                }

                toast.success('Try-On Complete!', {
                    description: `Fit score: ${Math.round(result.fit_score * 100)}%`,
                    duration: 4000,
                });
                return true;
            }

            // Failed
            const errMsg = result.error_message || 'Virtual try-on failed. Please try again.';
            setStage('final_failed');
            setError(errMsg);
            toast.error('Try-On Failed', { description: errMsg, duration: 6000 });
            return false;
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Virtual try-on failed.';
            setStage('final_failed');
            setError(msg);
            toast.error('Try-On Failed', { description: msg, duration: 6000 });
            return false;
        } finally {
            setIsProcessing(false);
        }
    }, []);

    const reset = useCallback(() => {
        setResultImage(null);
        setError(null);
        setIsProcessing(false);
        setStage('idle');
        setStageLabel('');
        setLastFailureKind(null);
        setLastBackendUsed(null);
        setFinalNotice(null);
        setPreviewOnlyMode(false);
    }, []);

    return {
        stage,
        isProcessing,
        resultImage,
        error,
        stageLabel,
        lastFailureKind,
        lastBackendUsed,
        finalNotice,
        previewOnlyMode,
        processVirtualTryOn,
        processMirrorTryOn,
        reset,
    };
}
