/**
 * LivePreviewCanvas — Real-time try-on result display
 *
 * Features:
 * - Smooth image transitions on garment switch
 * - Loading skeleton overlay
 * - Before/after comparison slider
 * - Processing time indicator
 */

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Zap, Clock } from 'lucide-react';
import { createTransition } from '@/motion';
import { safeImageSrc } from '@/lib/imageFallback';

interface LivePreviewCanvasProps {
    resultImage: string | null;
    originalImage: string | null;
    isProcessing: boolean;
    processingTimeMs: number;
    qualityScore: number;
    frameCount: number;
}

export function LivePreviewCanvas({
    resultImage,
    originalImage,
    isProcessing,
    processingTimeMs,
    qualityScore,
    frameCount,
}: LivePreviewCanvasProps) {
    const [showComparison, setShowComparison] = useState(false);
    const [sliderPos, setSliderPos] = useState(50);
    const containerRef = useRef<HTMLDivElement>(null);

    const handlePointerMove = useCallback((e: React.PointerEvent) => {
        if (!containerRef.current || !showComparison) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        setSliderPos(Math.max(0, Math.min(100, (x / rect.width) * 100)));
    }, [showComparison]);

    const displayImage = resultImage || originalImage;

    return (
        <div className="relative">
            {/* Main Image Area */}
            <div
                ref={containerRef}
                className={`relative aspect-[3/4] rounded-xl overflow-hidden bg-muted/50 ${
                    showComparison ? 'cursor-ew-resize' : ''
                }`}
                onPointerMove={handlePointerMove}
            >
                {displayImage ? (
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={resultImage || 'original'}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={createTransition({ duration: 0.3 })}
                            className="absolute inset-0"
                        >
                            {showComparison && originalImage ? (
                                <>
                                    <img
                                        src={safeImageSrc(originalImage)}
                                        alt="Original"
                                        className="absolute inset-0 w-full h-full object-cover"
                                        onError={(e) => {
                                            e.currentTarget.src = safeImageSrc('');
                                        }}
                                        draggable={false}
                                    />
                                    <div
                                        className="absolute inset-0 overflow-hidden"
                                        style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
                                    >
                                        <img
                                            src={safeImageSrc(resultImage || originalImage)}
                                            alt="Try-on result"
                                            className="w-full h-full object-cover"
                                            onError={(e) => {
                                                e.currentTarget.src = safeImageSrc('');
                                            }}
                                            draggable={false}
                                        />
                                    </div>
                                    <div
                                        className="absolute top-0 bottom-0 w-0.5 bg-white/80 shadow-lg"
                                        style={{ left: `${sliderPos}%` }}
                                    >
                                        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-white shadow-md" />
                                    </div>
                                    <div className="absolute top-2 left-2 bg-black/50 text-white px-2 py-0.5 rounded text-xs">
                                        Before
                                    </div>
                                    <div className="absolute top-2 right-2 bg-black/50 text-white px-2 py-0.5 rounded text-xs">
                                        After
                                    </div>
                                </>
                            ) : (
                                <img
                                    src={safeImageSrc(displayImage)}
                                    alt="Try-on preview"
                                    className="w-full h-full object-cover"
                                    onError={(e) => {
                                        e.currentTarget.src = safeImageSrc('');
                                    }}
                                />
                            )}
                        </motion.div>
                    </AnimatePresence>
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                        <p className="text-sm">Upload a photo to get started</p>
                    </div>
                )}

                {/* Processing Overlay */}
                <AnimatePresence>
                    {isProcessing && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center"
                        >
                            <div className="bg-background/90 rounded-xl px-4 py-3 flex items-center gap-3 shadow-lg">
                                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                                <span className="text-sm font-medium">Trying on...</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Stats Bar */}
            <div className="flex items-center justify-between mt-2 px-1">
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    {processingTimeMs > 0 && (
                        <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {processingTimeMs < 1000
                                ? `${Math.round(processingTimeMs)}ms`
                                : `${(processingTimeMs / 1000).toFixed(1)}s`}
                        </span>
                    )}
                    {qualityScore > 0 && (
                        <span className="flex items-center gap-1">
                            <Zap className="h-3 w-3" />
                            {Math.round(qualityScore * 100)}% quality
                        </span>
                    )}
                </div>
                {resultImage && originalImage && (
                    <button
                        onClick={() => setShowComparison(!showComparison)}
                        className="text-xs text-primary hover:underline"
                    >
                        {showComparison ? 'Hide comparison' : 'Compare'}
                    </button>
                )}
            </div>
        </div>
    );
}
