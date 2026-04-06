import { useRef, useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Camera, Upload, Image as ImageIcon, X, Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import type { Product } from '@/types';
import { createTransition } from '@/motion';

interface PhotoUploadAreaProps {
    userImage: string | null;
    resultImage: string | null;
    isProcessing: boolean;
    error: string | null;
    stageLabel?: string;
    selectedProduct: Product;
    onFileSelect: (file: File) => void;
    onReset: () => void;
    onAddToCart?: () => void;
    onSaveLook?: () => void;
    /** Lovable-style: large center image, dark gutters, minimal chrome */
    layout?: 'default' | 'immersive';
    previewOnly?: boolean;
}

export function PhotoUploadArea({
    userImage,
    resultImage,
    isProcessing,
    error,
    stageLabel,
    selectedProduct,
    onFileSelect,
    onReset,
    onAddToCart,
    onSaveLook,
    layout = 'default',
    previewOnly = false,
}: PhotoUploadAreaProps) {
    const immersive = layout === 'immersive';
    const fileInputRef = useRef<HTMLInputElement>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [cameraOpen, setCameraOpen] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const [view, setView] = useState<'after' | 'before'>('after');

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            onFileSelect(file);
        }
    };

    const startCamera = useCallback(() => {
        setCameraError(null);
        navigator.mediaDevices
            ?.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
            .then((stream) => {
                streamRef.current = stream;
                setCameraOpen(true);
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
            })
            .catch((err) => {
                setCameraError(err?.message || 'Camera access denied');
            });
    }, []);

    const stopCamera = useCallback(() => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        setCameraOpen(false);
        setCameraError(null);
    }, []);

    useEffect(() => {
        if (cameraOpen && videoRef.current && streamRef.current) {
            videoRef.current.srcObject = streamRef.current;
        }
        return () => {
            stopCamera();
        };
    }, [cameraOpen, stopCamera]);

    const captureFromCamera = useCallback(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas || video.readyState !== 4) return;
        const w = video.videoWidth;
        const h = video.videoHeight;
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.drawImage(video, 0, 0, w, h);
        canvas.toBlob(
            (blob) => {
                if (!blob) return;
                const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
                stopCamera();
                onFileSelect(file);
            },
            'image/jpeg',
            0.92
        );
    }, [onFileSelect, stopCamera]);

    // Determine which image to show
    const displayImage =
        resultImage && view === 'before'
            ? userImage
            : (resultImage || userImage);

    return (
        <div className={immersive ? 'space-y-0' : 'space-y-6'}>
            {!userImage && (
                <div
                    className={
                        immersive
                            ? 'mx-auto mb-8 max-w-xl rounded-xl border border-white/10 bg-white/[0.03] p-5 backdrop-blur-sm'
                            : 'rounded-xl border border-border bg-card p-4'
                    }
                >
                    <p className="mb-2 text-sm font-medium">For best Try-On results</p>
                    <ul
                        className={`grid gap-1 text-sm text-muted-foreground ${immersive ? 'text-white/65' : ''}`}
                    >
                        <li>- Use a clear, well-lit full-body photo</li>
                        <li>- Face the camera; keep arms slightly away from the body</li>
                        <li>- Avoid heavy shadows and busy backgrounds</li>
                        <li>- Wear fitted clothing for cleaner garment alignment</li>
                    </ul>
                </div>
            )}

            {!!resultImage && !!userImage && (
                <div
                    className={`flex items-center justify-between ${immersive ? 'mb-4 max-w-5xl mx-auto px-1' : ''}`}
                >
                    <div className="inline-flex rounded-full border border-border bg-card p-1">
                        <button
                            type="button"
                            onClick={() => setView('before')}
                            className={`px-4 py-1.5 text-sm rounded-full transition-colors ${view === 'before' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                        >
                            Before
                        </button>
                        <button
                            type="button"
                            onClick={() => setView('after')}
                            className={`px-4 py-1.5 text-sm rounded-full transition-colors ${view === 'after' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                        >
                            After
                        </button>
                    </div>
                    <p className="text-xs text-muted-foreground">Tip: zoom in to inspect details</p>
                </div>
            )}

            <div
                className={
                    immersive
                        ? 'relative mx-auto aspect-[3/4] w-full max-h-[min(88vh,920px)] max-w-5xl overflow-hidden bg-black/50 md:rounded-lg'
                        : 'relative aspect-[3/4] overflow-hidden rounded-xl bg-muted'
                }
            >
                {!displayImage ? (
                    <div
                        className={`absolute inset-0 flex flex-col items-center justify-center p-8 transition-colors ${immersive ? 'hover:bg-white/[0.02]' : 'hover:bg-muted/80'}`}
                        onDragOver={(e) => {
                            e.preventDefault();
                            e.currentTarget.classList.add('bg-accent/5');
                        }}
                        onDragLeave={(e) => {
                            e.preventDefault();
                            e.currentTarget.classList.remove('bg-accent/5');
                        }}
                        onDrop={(e) => {
                            e.preventDefault();
                            e.currentTarget.classList.remove('bg-accent/5');
                            const file = e.dataTransfer.files?.[0];
                            if (file && file.type.startsWith('image/')) {
                                onFileSelect(file);
                            }
                        }}
                    >
                        <div className="w-24 h-24 rounded-full bg-muted-foreground/10 flex items-center justify-center mb-6">
                            <ImageIcon className="h-12 w-12 text-muted-foreground" />
                        </div>
                        <h3 className="font-semibold text-lg mb-2">Upload Your Photo</h3>
                        <p className="text-sm text-muted-foreground text-center mb-6 max-w-[240px]">
                            Drag & drop or click to upload a full-body photo with neutral clothing
                        </p>
                        <div className="flex flex-col sm:flex-row gap-3">
                            <Button variant="hero" onClick={() => fileInputRef.current?.click()}>
                                <Upload className="h-4 w-4 mr-2" />
                                Upload Photo
                            </Button>
                            <Button variant="outline" onClick={startCamera}>
                                <Camera className="h-4 w-4 mr-2" />
                                Use Camera
                            </Button>
                        </div>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleFileUpload}
                            className="hidden"
                        />
                    </div>
                ) : (
                    <>
                        <motion.img
                            key={displayImage}
                            src={displayImage}
                            alt={resultImage ? "Try-on result" : "Your photo"}
                            className={
                                immersive
                                    ? 'h-full w-full max-h-[min(88vh,920px)] object-cover object-center'
                                    : 'h-full w-full object-cover'
                            }
                            initial={{ opacity: 0.4 }}
                            animate={{ opacity: 1 }}
                            transition={createTransition({ duration: 0.25 })}
                        />

                        {/* Processing overlay */}
                        {isProcessing && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/75">
                                <Loader2 className="mb-4 h-16 w-16 animate-spin text-[hsl(45_74%_52%)]" />
                                <p className="font-medium text-white">{stageLabel || 'Generating your look…'}</p>
                                <p className="text-sm text-white/65">This may take up to a minute</p>
                            </div>
                        )}

                        {/* Error overlay */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="absolute bottom-4 left-4 right-4 bg-destructive/95 backdrop-blur-sm rounded-lg p-4"
                            >
                                <p className="text-destructive-foreground font-medium">Try-on failed</p>
                                <p className="text-sm text-destructive-foreground/80">{error}</p>
                            </motion.div>
                        )}

                        {/* Success overlay */}
                        {resultImage && !isProcessing && !error && (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="absolute bottom-4 left-4 right-4 bg-background/95 backdrop-blur-sm rounded-lg p-4"
                            >
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-10 h-10 rounded-full bg-success/10 flex items-center justify-center">
                                        <Check className="h-5 w-5 text-success" />
                                    </div>
                                    <div>
                                        <p className="font-medium">
                                            {previewOnly ? 'Live Preview Ready' : 'Virtual Try-On Complete!'}
                                        </p>
                                        <p className="text-sm text-muted-foreground">
                                            {previewOnly
                                                ? `${selectedProduct.name} preview on your photo`
                                                : `${selectedProduct.name} styled on you`}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <Button variant="hero" size="sm" className="flex-1" onClick={onAddToCart}>
                                        Add to Cart — ${selectedProduct.price}
                                    </Button>
                                    <Button variant="outline" size="sm" onClick={onSaveLook}>
                                        Save Look
                                    </Button>
                                </div>
                            </motion.div>
                        )}

                        {/* Reset button */}
                        <button
                            type="button"
                            onClick={onReset}
                            className={`absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-full transition-colors ${immersive ? 'bg-black/45 text-white backdrop-blur-md hover:bg-black/60' : 'bg-background/90 backdrop-blur-sm hover:bg-background'}`}
                            aria-label="Remove photo"
                        >
                            <X className="h-5 w-5" />
                        </button>

                        {/* Result badge */}
                        {resultImage && !isProcessing && (
                            <div className="absolute top-4 left-4 bg-accent text-accent-foreground px-3 py-1 rounded-full text-xs font-semibold">
                                {previewOnly ? 'Preview Only (No Final GPU Render)' : 'Virtual Preview'}
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Photo Guidelines */}
            {!userImage && (
                <div className={`rounded-lg bg-muted/50 p-4 ${immersive ? 'mx-auto mt-8 max-w-xl border border-white/10 bg-white/[0.04]' : ''}`}>
                    <h4 className="mb-2 text-sm font-medium">Photo tips</h4>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                        <li>• Stand against a plain background</li>
                        <li>• Use good lighting, preferably natural light</li>
                        <li>• Wear fitted, neutral-colored clothing</li>
                        <li>• Face the camera directly with arms relaxed</li>
                    </ul>
                </div>
            )}

            {/* Camera capture dialog */}
            <Dialog open={cameraOpen} onOpenChange={(open) => !open && stopCamera()}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Capture photo</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        {cameraError ? (
                            <p className="text-sm text-destructive">{cameraError}</p>
                        ) : (
                            <>
                                <div className="aspect-[3/4] rounded-lg overflow-hidden bg-muted">
                                    <video
                                        ref={videoRef}
                                        autoPlay
                                        playsInline
                                        muted
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                                <div className="flex gap-2">
                                    <Button variant="hero" className="flex-1" onClick={captureFromCamera}>
                                        Capture
                                    </Button>
                                    <Button variant="outline" onClick={stopCamera}>
                                        Cancel
                                    </Button>
                                </div>
                            </>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
            <canvas ref={canvasRef} className="hidden" />
        </div>
    );
}
