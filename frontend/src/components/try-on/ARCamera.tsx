/**
 * CONFIT — AR Virtual Try-On Camera Component
 * =============================================
 * Real-time muscle & pose adaptation: MediaPipe BlazePose (TF.js) + TPS mesh warp,
 * temporal anchor smoothing, arm-occlusion punch-out, face-safe band, static fallback.
 */

import { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Camera,
  CameraOff,
  SwitchCamera,
  Download,
  Share2,
  Loader2,
  AlertCircle,
  Check,
  X,
  Shirt,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import type { Product } from '@/types';
import { safeImageSrc } from '@/lib/imageFallback';
import { getPrimaryProductImageUrl } from '@/lib/productImages';
import { resolveArOverlayCategory, type ArOverlayCategory } from '@/lib/arGarmentCategory';
import { computeBodyAnchors, smoothAnchors, type BodyAnchors } from '@/lib/realtimeTryOn/anchors';
import { POSE_INTERVAL_MS } from '@/lib/realtimeTryOn/constants';
import { createRealtimePoseDetector, type LoadedPoseBackend } from '@/lib/realtimeTryOn/poseDetector';
import { drawRealtimeWarpedGarment } from '@/lib/realtimeTryOn/drawWarpedGarment';

interface Keypoint {
  x: number;
  y: number;
  z?: number;
  visibility?: number;
  score?: number;
  name: string;
}

interface PoseResult {
  keypoints: Keypoint[];
  boundingBox: { x: number; y: number; width: number; height: number };
  confidence: number;
  rotationAngle: number;
  isValid: boolean;
}

interface ARCameraProps {
  selectedProduct: Product;
  onAddToCart?: () => void;
  onSaveLook?: (imageData: string) => void;
  className?: string;
}

function poseFromEstimate(
  pose: import('@tensorflow-models/pose-detection').Pose,
  video: HTMLVideoElement
): PoseResult {
  const w = video.videoWidth;
  const h = video.videoHeight;
  const keypoints = pose.keypoints.map((kp) => ({
    x: kp.x / w,
    y: kp.y / h,
    z: kp.z,
    visibility: kp.score,
    score: kp.score,
    name: kp.name ?? '',
  }));

  const validKps = keypoints.filter((kp) => (kp.visibility ?? 0) > 0.3);
  let boundingBox = { x: 0, y: 0, width: 0, height: 0 };
  if (validKps.length > 0) {
    const xs = validKps.map((kp) => kp.x);
    const ys = validKps.map((kp) => kp.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    boundingBox = { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }

  const leftShoulder = keypoints.find((kp) => kp.name === 'left_shoulder');
  const rightShoulder = keypoints.find((kp) => kp.name === 'right_shoulder');
  const nose = keypoints.find((kp) => kp.name === 'nose');

  let rotationAngle = 0;
  if (leftShoulder && rightShoulder) {
    const dx = rightShoulder.x - leftShoulder.x;
    const dy = rightShoulder.y - leftShoulder.y;
    rotationAngle = Math.atan2(dy, dx) * (180 / Math.PI);
  }

  const isValid =
    (nose?.visibility ?? 0) > 0.45 &&
    (leftShoulder?.visibility ?? 0) > 0.45 &&
    (rightShoulder?.visibility ?? 0) > 0.45;

  return {
    keypoints,
    boundingBox,
    confidence: pose.score ?? 0.5,
    rotationAngle,
    isValid,
  };
}

// ==========================================
// Main AR Camera Component
// ==========================================

export function ARCamera({
  selectedProduct,
  onAddToCart,
  onSaveLook,
  className = '',
}: ARCameraProps) {
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationRef = useRef<number | null>(null);
  const detectorRef = useRef<import('@tensorflow-models/pose-detection').PoseDetector | null>(null);
  const poseBusyRef = useRef(false);
  const lastPoseTimeRef = useRef(0);
  const lastPoseRef = useRef<PoseResult | null>(null);
  const smoothedAnchorsRef = useRef<BodyAnchors | null>(null);
  const garmentImgRef = useRef<HTMLImageElement | null>(null);

  // State
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isFrontCamera, setIsFrontCamera] = useState(true);
  const [currentPose, setCurrentPose] = useState<PoseResult | null>(null);
  const [fps, setFps] = useState(0);
  const [overlayOpacity, setOverlayOpacity] = useState(85);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  /** True when video element has usable dimensions (avoids 0×0 canvas / blank preview). */
  const [videoStreamReady, setVideoStreamReady] = useState(false);
  const [isPoseLoading, setIsPoseLoading] = useState(false);
  const [isPoseReady, setIsPoseReady] = useState(false);
  const [poseError, setPoseError] = useState<string | null>(null);
  const [poseBackend, setPoseBackend] = useState<LoadedPoseBackend | null>(null);
  const [poseInferenceMs, setPoseInferenceMs] = useState(0);

  const garmentImage = selectedProduct ? getPrimaryProductImageUrl(selectedProduct) : null;
  const category = useMemo<ArOverlayCategory>(
    () => (selectedProduct ? resolveArOverlayCategory(selectedProduct) : 'tops'),
    [selectedProduct]
  );

  const [isGarmentLoaded, setIsGarmentLoaded] = useState(false);

  useEffect(() => {
    smoothedAnchorsRef.current = null;
    if (!garmentImage) {
      garmentImgRef.current = null;
      setIsGarmentLoaded(false);
      return;
    }
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      garmentImgRef.current = img;
      setIsGarmentLoaded(true);
    };
    img.onerror = () => {
      garmentImgRef.current = null;
      setIsGarmentLoaded(false);
    };
    img.src = garmentImage;
  }, [garmentImage, selectedProduct?.id]);

  const loadDetector = useCallback(async () => {
    if (detectorRef.current) return;
    setIsPoseLoading(true);
    setPoseError(null);
    try {
      const { detector, backend } = await createRealtimePoseDetector();
      detectorRef.current = detector;
      setPoseBackend(backend);
      setIsPoseReady(true);
    } catch (err: unknown) {
      console.error(err);
      setPoseError(err instanceof Error ? err.message : 'Pose model failed');
    } finally {
      setIsPoseLoading(false);
    }
  }, []);

  // FPS tracking
  const frameCountRef = useRef(0);
  const lastFpsUpdateRef = useRef(Date.now());

  // Start camera
  const startCamera = useCallback(async () => {
    setCameraError(null);

    try {
      // Load pose detector
      if (!isPoseReady) {
        await loadDetector();
      }

      // Get camera stream
      const constraints = {
        video: {
          facingMode: isFrontCamera ? 'user' : 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };

      const media =
        typeof navigator !== 'undefined' ? navigator.mediaDevices : undefined;
      if (!media?.getUserMedia) {
        throw new Error(
          'Camera unavailable: use https:// or http://localhost, and a modern browser with camera permission.'
        );
      }
      const stream = await media.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        const v = videoRef.current;
        v.srcObject = stream;
        await v.play();
        // Wait for intrinsic size so canvas matches (fixes blank / grey stage).
        if (v.readyState < 2) {
          await new Promise<void>((resolve) => {
            const done = () => resolve();
            v.addEventListener('loadeddata', done, { once: true });
            v.addEventListener('loadedmetadata', done, { once: true });
            setTimeout(done, 3000);
          });
        }
        setVideoStreamReady(v.videoWidth > 0 && v.videoHeight > 0);
        smoothedAnchorsRef.current = null;
        lastPoseRef.current = null;
        setIsCameraActive(true);
      }
    } catch (err: any) {
      console.error('Camera error:', err);
      setCameraError(err.message || 'Camera access denied');
    }
  }, [isFrontCamera, isPoseReady, loadDetector]);

  // Stop camera
  const stopCamera = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsCameraActive(false);
    setCurrentPose(null);
  }, []);

  // Switch camera
  const switchCamera = useCallback(async () => {
    stopCamera();
    setIsFrontCamera((prev) => !prev);
    // Small delay before starting again
    setTimeout(() => startCamera(), 100);
  }, [stopCamera, startCamera]);

  // Main render loop (pose inference async — never blocks paint)
  const renderFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas || !isCameraActive) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = video.videoWidth;
    const height = video.videoHeight;

    if (width === 0 || height === 0) {
      animationRef.current = requestAnimationFrame(renderFrame);
      return;
    }

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    ctx.save();
    if (isFrontCamera) {
      ctx.scale(-1, 1);
      ctx.drawImage(video, -width, 0, width, height);
    } else {
      ctx.drawImage(video, 0, 0, width, height);
    }
    ctx.restore();

    const now = performance.now();
    const detector = detectorRef.current;
    if (isPoseReady && detector && !poseBusyRef.current && now - lastPoseTimeRef.current >= POSE_INTERVAL_MS) {
      poseBusyRef.current = true;
      const t0 = performance.now();
      void detector
        .estimatePoses(video, { flipHorizontal: isFrontCamera })
        .then((poses) => {
          const ms = performance.now() - t0;
          setPoseInferenceMs(ms);
          poseBusyRef.current = false;
          lastPoseTimeRef.current = performance.now();

          if (!poses.length) {
            lastPoseRef.current = {
              keypoints: [],
              boundingBox: { x: 0, y: 0, width: 0, height: 0 },
              confidence: 0,
              rotationAngle: 0,
              isValid: false,
            };
            setCurrentPose(lastPoseRef.current);
            return;
          }

          const pose = poseFromEstimate(poses[0], video);
          lastPoseRef.current = pose;
          setCurrentPose(pose);

          const raw = computeBodyAnchors(pose.keypoints);
          if (raw && pose.isValid) {
            smoothedAnchorsRef.current = smoothAnchors(smoothedAnchorsRef.current, raw);
          }
        })
        .catch(() => {
          poseBusyRef.current = false;
        });
    }

    const pose = lastPoseRef.current;
    const img = garmentImgRef.current;
    if (isGarmentLoaded && img && pose && smoothedAnchorsRef.current) {
      ctx.globalAlpha = overlayOpacity / 100;
      drawRealtimeWarpedGarment(
        ctx,
        Boolean(pose.isValid),
        smoothedAnchorsRef.current,
        img,
        img.naturalWidth,
        img.naturalHeight,
        width,
        height,
        category
      );
      ctx.globalAlpha = 1;
    }

    frameCountRef.current++;
    const nowFps = Date.now();
    if (nowFps - lastFpsUpdateRef.current >= 1000) {
      setFps(frameCountRef.current);
      frameCountRef.current = 0;
      lastFpsUpdateRef.current = nowFps;
    }

    animationRef.current = requestAnimationFrame(renderFrame);
  }, [
    isCameraActive,
    isFrontCamera,
    isPoseReady,
    isGarmentLoaded,
    overlayOpacity,
    category,
  ]);

  // Start render loop when camera is active and video has frames
  useEffect(() => {
    const v = videoRef.current;
    if (isCameraActive && v && v.readyState >= 2 && v.videoWidth > 0) {
      renderFrame();
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isCameraActive, videoStreamReady, renderFrame]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  // Capture screenshot
  const captureScreenshot = useCallback(async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    setIsCapturing(true);

    try {
      // Convert to data URL
      const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
      setCapturedImage(dataUrl);

      toast.success('Screenshot captured!', {
        description: 'You can save or share your virtual try-on look.',
      });
    } catch (err) {
      console.error('Screenshot error:', err);
      toast.error('Failed to capture screenshot');
    } finally {
      setIsCapturing(false);
    }
  }, []);

  // Download image
  const downloadImage = useCallback(() => {
    if (!capturedImage) return;

    const link = document.createElement('a');
    link.href = capturedImage;
    link.download = `confit-tryon-${selectedProduct?.name || 'look'}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast.success('Image downloaded!');
  }, [capturedImage, selectedProduct?.name]);

  // Share image
  const shareImage = useCallback(async () => {
    if (!capturedImage || !navigator.share) {
      toast.error('Sharing not supported on this device');
      return;
    }

    try {
      // Convert data URL to blob
      const response = await fetch(capturedImage);
      const blob = await response.blob();
      const file = new File([blob], 'tryon-look.jpg', { type: 'image/jpeg' });

      await navigator.share({
        title: 'My CONFIT Virtual Try-On',
        text: `Check out how ${selectedProduct?.name || 'this item'} looks on me!`,
        files: [file],
      });

      toast.success('Shared successfully!');
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Share error:', err);
        toast.error('Failed to share');
      }
    }
  }, [capturedImage, selectedProduct?.name]);

  // Save look to wardrobe
  const handleSaveLook = useCallback(() => {
    if (capturedImage && onSaveLook) {
      onSaveLook(capturedImage);
      toast.success('Look saved to your wardrobe!');
    }
  }, [capturedImage, onSaveLook]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shirt className="h-5 w-5 text-primary" />
          <span className="font-medium">AR Try-On</span>
          {isCameraActive && (
            <Badge variant="outline" className="ml-2">
              <span className="relative flex h-2 w-2 mr-1">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Live
            </Badge>
          )}
        </div>

          {isCameraActive && (
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{fps} FPS</span>
            {poseBackend && (
              <Badge variant="outline" className="text-xs font-normal">
                {poseBackend === 'blazepose' ? 'BlazePose' : 'MoveNet'}
              </Badge>
            )}
            <span className="text-xs">{poseInferenceMs.toFixed(0)} ms infer</span>
            {currentPose?.isValid && (
              <Badge variant="secondary" className="text-xs">
                <Check className="h-3 w-3 mr-1" />
                Tracking
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Camera View */}
      <div className="relative aspect-[3/4] bg-muted rounded-xl overflow-hidden">
        {!isCameraActive ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-8">
            <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Camera className="h-10 w-10 text-primary" />
            </div>
            <h3 className="font-semibold text-lg mb-2">Start AR Try-On</h3>
            <p className="text-sm text-muted-foreground text-center mb-6 max-w-[240px]">
              See how {selectedProduct?.name || 'this item'} looks on you in real-time
            </p>

            {cameraError && (
              <div className="mb-4 p-3 bg-destructive/10 rounded-lg flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                <p className="text-sm text-destructive">{cameraError}</p>
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Button
                variant="hero"
                onClick={startCamera}
                disabled={isPoseLoading}
                className="min-w-[200px]"
              >
                {isPoseLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading AI...
                  </>
                ) : (
                  <>
                    <Camera className="h-4 w-4 mr-2" />
                    Start Camera
                  </>
                )}
              </Button>
              {poseError && (
                <p className="text-xs text-muted-foreground text-center">
                  Note: {poseError}. Basic camera will still work.
                </p>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Live feed: video underlay (visible if canvas not yet sized); canvas draws video + overlay */}
            <video
              ref={videoRef}
              playsInline
              muted
              autoPlay
              className={`absolute inset-0 z-0 h-full w-full object-cover ${isFrontCamera ? 'scale-x-[-1]' : ''}`}
              onLoadedMetadata={() => {
                const v = videoRef.current;
                if (v && v.videoWidth > 0) setVideoStreamReady(true);
              }}
            />

            <canvas
              ref={canvasRef}
              className="pointer-events-none absolute inset-0 z-10 h-full w-full object-cover"
            />

            {/* Controls overlay */}
            <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="icon"
                  onClick={switchCamera}
                  className="bg-background/80 backdrop-blur-sm"
                >
                  <SwitchCamera className="h-4 w-4" />
                </Button>
                <Button
                  variant="secondary"
                  size="icon"
                  onClick={() => setShowSettings(true)}
                  className="bg-background/80 backdrop-blur-sm"
                >
                  <Sparkles className="h-4 w-4" />
                </Button>
              </div>

              <Button
                variant="hero"
                size="lg"
                onClick={captureScreenshot}
                disabled={isCapturing}
                className="rounded-full h-14 w-14"
              >
                {isCapturing ? (
                  <Loader2 className="h-6 w-6 animate-spin" />
                ) : (
                  <Camera className="h-6 w-6" />
                )}
              </Button>

              <Button
                variant="secondary"
                size="icon"
                onClick={stopCamera}
                className="bg-background/80 backdrop-blur-sm"
              >
                <CameraOff className="h-4 w-4" />
              </Button>
            </div>

            {/* Pose indicator */}
            {currentPose && !currentPose.isValid && (
              <div className="absolute top-4 left-4 right-4 bg-yellow-500/90 backdrop-blur-sm rounded-lg p-3">
                <p className="text-sm font-medium text-yellow-950">
                  Adjust your position
                </p>
                <p className="text-xs text-yellow-900">
                  Face the camera and ensure your upper body is visible
                </p>
              </div>
            )}

            {/* Product badge */}
            <div className="absolute top-4 left-4 bg-background/80 backdrop-blur-sm rounded-lg px-3 py-1.5">
              <p className="text-xs font-medium">{selectedProduct?.name}</p>
              <p className="text-xs text-muted-foreground">${selectedProduct?.price}</p>
            </div>
          </>
        )}
      </div>

      {/* Captured Image Preview */}
      <AnimatePresence>
        {capturedImage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
          >
            <Card>
              <CardContent className="p-4">
                <div className="flex gap-4">
                  <img
                    src={safeImageSrc(capturedImage)}
                    alt="Captured try-on"
                    className="w-24 h-32 object-cover rounded-lg"
                    onError={(e) => {
                      e.currentTarget.src = safeImageSrc('');
                    }}
                  />
                  <div className="flex-1 space-y-3">
                    <div>
                      <p className="font-medium text-sm">Your Virtual Try-On</p>
                      <p className="text-xs text-muted-foreground">
                        {selectedProduct?.name} • ${selectedProduct?.price}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={downloadImage}>
                        <Download className="h-3 w-3 mr-1" />
                        Save
                      </Button>
                      <Button size="sm" variant="outline" onClick={shareImage}>
                        <Share2 className="h-3 w-3 mr-1" />
                        Share
                      </Button>
                      {onSaveLook && (
                        <Button size="sm" variant="outline" onClick={handleSaveLook}>
                          <Shirt className="h-3 w-3 mr-1" />
                          Wardrobe
                        </Button>
                      )}
                      {onAddToCart && (
                        <Button size="sm" variant="hero" onClick={onAddToCart}>
                          Add to Cart
                        </Button>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setCapturedImage(null)}
                    className="self-start"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Privacy Notice */}
      <div className="bg-muted/50 rounded-lg p-3">
        <p className="text-xs text-muted-foreground flex items-center gap-2">
          <Check className="h-3 w-3 text-green-500" />
          Privacy-first: Images are processed locally and not stored on our servers
        </p>
      </div>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>AR Try-On Settings</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            <div className="space-y-3">
              <Label>Garment Opacity: {overlayOpacity}%</Label>
              <Slider
                value={[overlayOpacity]}
                onValueChange={(value) => setOverlayOpacity(value[0])}
                min={50}
                max={100}
                step={5}
              />
              <p className="text-xs text-muted-foreground">
                Adjust how transparent the garment overlay appears
              </p>
            </div>

            <div className="space-y-3">
              <Label>Performance</Label>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div className="bg-muted rounded-lg p-3 text-center">
                  <p className="font-medium">{fps} FPS</p>
                  <p className="text-xs text-muted-foreground">Render</p>
                </div>
                <div className="bg-muted rounded-lg p-3 text-center">
                  <p className="font-medium">{poseInferenceMs.toFixed(0)} ms</p>
                  <p className="text-xs text-muted-foreground">Pose infer</p>
                </div>
                <div className="bg-muted rounded-lg p-3 text-center">
                  <p className="font-medium">
                    {currentPose?.isValid ? 'Live' : 'Fallback'}
                  </p>
                  <p className="text-xs text-muted-foreground">TPS warp</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Real-time mode: TPS mesh warp + 0.7/0.3 anchor smoothing, face-safe band, arm
                occlusion. Target &lt;80 ms total per frame on GPU.
              </p>
            </div>

            <div className="bg-primary/5 rounded-lg p-3">
              <p className="text-xs font-medium mb-1">Tips for Best Results</p>
              <ul className="text-xs text-muted-foreground space-y-1">
                <li>• Stand in good lighting</li>
                <li>• Keep your upper body visible</li>
                <li>• Face the camera directly</li>
                <li>• Wear fitted clothing underneath</li>
              </ul>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default ARCamera;
