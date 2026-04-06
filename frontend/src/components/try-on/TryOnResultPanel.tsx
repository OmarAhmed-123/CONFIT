/**
 * TryOnResultPanel — Merged Image Result Display
 *
 * Shows the composite try-on result with controls to:
 *  - View the 360° rotation
 *  - Download the result
 *  - Compare before / after with a slider
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { RotateCcw, Download, Eye, SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { safeImageSrc } from '@/lib/imageFallback';

interface TryOnResultPanelProps {
    resultImage: string;
    originalImage: string;
    productName: string;
    onView360: () => void;
    is360Loading: boolean;
}

export function TryOnResultPanel({
    resultImage,
    originalImage,
    productName,
    onView360,
    is360Loading,
}: TryOnResultPanelProps) {
    const [showComparison, setShowComparison] = useState(false);
    const [sliderPosition, setSliderPosition] = useState(50);
    const comparisonRef = useRef<HTMLDivElement>(null);

    /* ── Comparison Slider ───────────────────────────────────── */

    const handleComparisonMove = useCallback((e: React.PointerEvent) => {
        if (!comparisonRef.current) return;
        const rect = comparisonRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
        setSliderPosition(pct);
    }, []);

    /* ── Download ────────────────────────────────────────────── */

    const handleDownload = useCallback(() => {
        const link = document.createElement('a');
        link.download = `confit-tryon-${productName.replace(/\s+/g, '-').toLowerCase()}.jpg`;
        link.href = resultImage;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, [resultImage, productName]);

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
        >
            {/* Result / Comparison View */}
            {showComparison ? (
                <div
                    ref={comparisonRef}
                    className="relative aspect-[3/4] rounded-xl overflow-hidden cursor-ew-resize select-none"
                    onPointerMove={handleComparisonMove}
                >
                    {/* Original (left) */}
                    <img
                        src={safeImageSrc(originalImage)}
                        alt="Original photo"
                        className="absolute inset-0 w-full h-full object-cover"
                        onError={(e) => {
                            e.currentTarget.src = safeImageSrc('');
                        }}
                        draggable={false}
                    />

                    {/* Result (right — clipped) */}
                    <div
                        className="absolute inset-0 overflow-hidden"
                        style={{ clipPath: `inset(0 0 0 ${sliderPosition}%)` }}
                    >
                        <img
                            src={safeImageSrc(resultImage)}
                            alt="Try-on result"
                            className="w-full h-full object-cover"
                            onError={(e) => {
                                e.currentTarget.src = safeImageSrc('');
                            }}
                            draggable={false}
                        />
                    </div>

                    {/* Slider Line */}
                    <div
                        className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg"
                        style={{ left: `${sliderPosition}%` }}
                    >
                        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-white shadow-md flex items-center justify-center">
                            <SlidersHorizontal className="h-4 w-4 text-charcoal" />
                        </div>
                    </div>

                    {/* Labels */}
                    <div className="absolute top-3 left-3 bg-background/80 backdrop-blur-sm px-2 py-1 rounded text-xs font-medium">
                        Before
                    </div>
                    <div className="absolute top-3 right-3 bg-background/80 backdrop-blur-sm px-2 py-1 rounded text-xs font-medium">
                        After
                    </div>
                </div>
            ) : (
                <div className="aspect-[3/4] rounded-xl overflow-hidden bg-muted">
                    <img
                        src={safeImageSrc(resultImage)}
                        alt={`${productName} — virtual try-on result`}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                            e.currentTarget.src = safeImageSrc('');
                        }}
                    />
                </div>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-3 gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowComparison(!showComparison)}
                    className="gap-1.5 text-xs"
                >
                    <Eye className="h-3.5 w-3.5" />
                    {showComparison ? 'Result' : 'Compare'}
                </Button>

                <Button
                    variant="hero"
                    size="sm"
                    onClick={onView360}
                    disabled={is360Loading}
                    className="gap-1.5 text-xs"
                >
                    <RotateCcw className="h-3.5 w-3.5" />
                    View 360°
                </Button>

                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDownload}
                    className="gap-1.5 text-xs"
                >
                    <Download className="h-3.5 w-3.5" />
                    Download
                </Button>
            </div>
        </motion.div>
    );
}
