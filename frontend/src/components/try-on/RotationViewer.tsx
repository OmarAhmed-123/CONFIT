/**
 * RotationViewer — Interactive 360° CSS3D Rotation Component
 *
 * Displays a try-on result with CSS perspective transforms.
 * Supports mouse drag, touch swipe, and auto-rotation.
 */

import { useRef, useCallback, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { RotateCcw, Play, Pause, Download, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ViewerFrame } from '@/models/TryOnModel';

interface RotationViewerProps {
    frames: ViewerFrame[];
    currentIndex: number;
    currentAngleDeg: number;
    isLoading: boolean;
    isAutoPlaying: boolean;
    onRotateBy: (delta: number) => void;
    onToggleAutoPlay: () => void;
}

export function RotationViewer({
    frames,
    currentIndex,
    currentAngleDeg,
    isLoading,
    isAutoPlaying,
    onRotateBy,
    onToggleAutoPlay,
}: RotationViewerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const dragStartX = useRef<number | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const currentFrame = frames.length > 0 ? frames[currentIndex] : null;

    /* ── Mouse / Touch Drag ──────────────────────────────────── */

    const handlePointerDown = useCallback((e: React.PointerEvent) => {
        dragStartX.current = e.clientX;
        setIsDragging(true);
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
    }, []);

    const handlePointerMove = useCallback((e: React.PointerEvent) => {
        if (dragStartX.current === null) return;

        const delta = e.clientX - dragStartX.current;
        const sensitivity = 8;

        if (Math.abs(delta) >= sensitivity) {
            onRotateBy(delta > 0 ? 1 : -1);
            dragStartX.current = e.clientX;
        }
    }, [onRotateBy]);

    const handlePointerUp = useCallback(() => {
        dragStartX.current = null;
        setIsDragging(false);
    }, []);

    /* ── Keyboard Arrow Keys ─────────────────────────────────── */

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowLeft') onRotateBy(-1);
            if (e.key === 'ArrowRight') onRotateBy(1);
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onRotateBy]);

    /* ── Download Current Frame ──────────────────────────────── */

    const handleDownload = useCallback(() => {
        if (!currentFrame) return;
        const link = document.createElement('a');
        link.download = `confit-360-frame-${currentIndex}.jpg`;
        link.href = currentFrame.dataUri;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, [currentFrame, currentIndex]);

    /* ── Loading State ───────────────────────────────────────── */

    if (isLoading) {
        return (
            <div className="aspect-square bg-muted rounded-xl flex flex-col items-center justify-center">
                <Loader2 className="h-12 w-12 text-accent animate-spin mb-4" />
                <p className="font-medium text-sm">Generating 360° view...</p>
                <p className="text-xs text-muted-foreground">This may take a few seconds</p>
            </div>
        );
    }

    if (frames.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
        >
            {/* Viewer */}
            <div
                ref={containerRef}
                className="relative aspect-[3/4] bg-gradient-to-b from-muted/30 to-muted rounded-xl overflow-hidden select-none"
                style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerLeave={handlePointerUp}
            >
                {currentFrame && (
                    <img
                        src={currentFrame.dataUri}
                        alt={`360° view at ${currentAngleDeg}°`}
                        className="w-full h-full object-contain pointer-events-none"
                        draggable={false}
                        style={{
                            transform: `perspective(800px) rotateY(${currentAngleDeg * 0.05}deg)`,
                            transition: isDragging ? 'none' : 'transform 0.15s ease-out',
                        }}
                    />
                )}

                {/* Angle Badge */}
                <div className="absolute top-4 left-4 bg-background/90 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-medium">
                    {Math.round(currentAngleDeg)}°
                </div>

                {/* Drag Hint */}
                {!isDragging && !isAutoPlaying && (
                    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-background/80 backdrop-blur-sm px-4 py-2 rounded-full text-xs text-muted-foreground flex items-center gap-2">
                        <RotateCcw className="h-3 w-3" />
                        Drag to rotate
                    </div>
                )}
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onToggleAutoPlay}
                        className="gap-1.5"
                    >
                        {isAutoPlaying ? (
                            <><Pause className="h-3.5 w-3.5" /> Pause</>
                        ) : (
                            <><Play className="h-3.5 w-3.5" /> Auto Rotate</>
                        )}
                    </Button>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDownload}
                        className="gap-1.5"
                    >
                        <Download className="h-3.5 w-3.5" />
                        Save Frame
                    </Button>
                </div>
            </div>

            {/* Frame Indicator */}
            {frames.length > 1 && (
                <div className="flex items-center gap-0.5 justify-center">
                    {frames.map((_, idx) => (
                        <button
                            key={idx}
                            onClick={() => onRotateBy(idx - currentIndex)}
                            className={`w-1.5 h-1.5 rounded-full transition-all ${idx === currentIndex
                                    ? 'bg-accent w-3'
                                    : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
                                }`}
                        />
                    ))}
                </div>
            )}
        </motion.div>
    );
}
