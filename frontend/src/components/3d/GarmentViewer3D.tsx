/**
 * GarmentViewer3D - Interactive 3D Garment Viewer
 * ===============================================
 *
 * Displays garments as true 3D models using Three.js.
 * Features:
 * - glTF model loading with Draco compression
 * - Interactive rotation, zoom, pan
 * - HDR lighting for realistic materials
 * - Level of Detail (LOD) system
 * - Color/variant switching
 */

import { Suspense, useMemo, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  ContactShadows,
  useGLTF,
} from '@react-three/drei';
import * as THREE from 'three';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw, Palette, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import './GarmentViewer3D.css';

// Configure Draco decoder
const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath('/draco/');
dracoLoader.setDecoderConfig({ type: 'js' });

interface GarmentViewer3DProps {
  garmentId: string;
  modelUrl: string;
  thumbnailUrl?: string;
  color?: string;
  availableColors?: Array<{ name: string; hex: string }>;
  onColorChange?: (color: string) => void;
  onModelLoaded?: () => void;
  className?: string;
  showControls?: boolean;
  autoRotate?: boolean;
  enableZoom?: boolean;
  enablePan?: boolean;
  minDistance?: number;
  maxDistance?: number;
}

export function GarmentViewer3D({
  garmentId,
  modelUrl,
  thumbnailUrl,
  color,
  availableColors,
  onColorChange,
  onModelLoaded,
  className = '',
  showControls = true,
  autoRotate = false,
  enableZoom = true,
  enablePan = false,
  minDistance = 1,
  maxDistance = 5,
}: GarmentViewer3DProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedColor, setSelectedColor] = useState(color);
  const [showColorPicker, setShowColorPicker] = useState(false);
  const controlsRef = useRef<any>(null);

  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  const handleColorChange = (hex: string) => {
    setSelectedColor(hex);
    onColorChange?.(hex);
  };

  return (
    <div className={`relative w-full h-full ${className}`} data-garment-id={garmentId}>
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-muted/50 backdrop-blur-sm"
          >
            <Loader2 className="h-10 w-10 text-accent animate-spin mb-3" />
            <p className="text-sm font-medium">Loading 3D Model</p>
            <p className="text-xs text-muted-foreground mt-1">Preparing interactive view...</p>
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-muted/50">
          <p className="text-sm text-destructive">{error}</p>
          {thumbnailUrl && (
            <img
              src={thumbnailUrl}
              alt="Garment preview"
              className="mt-4 max-h-[60%] object-contain rounded-lg"
            />
          )}
        </div>
      )}

      <Canvas
        camera={{ position: [0, 0, 2], fov: 50 }}
        dpr={[1, 2]}
        gl={{
          antialias: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          outputColorSpace: THREE.SRGBColorSpace,
        }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x000000, 0);
        }}
      >
        <Suspense fallback={null}>
          <Environment preset="studio" backgroundBlurriness={0.8} />
          <ambientLight intensity={0.3} />
          <directionalLight position={[5, 5, 5]} intensity={0.5} castShadow />

          <GarmentModel
            url={modelUrl}
            color={selectedColor}
            onLoaded={() => {
              setIsLoading(false);
              onModelLoaded?.();
            }}
            onError={(err) => {
              setError(err);
              setIsLoading(false);
            }}
          />

          <ContactShadows
            position={[0, -0.5, 0]}
            opacity={0.4}
            scale={10}
            blur={2}
            far={4}
            resolution={512}
            color="#000000"
          />

          <OrbitControls
            ref={controlsRef}
            enablePan={enablePan}
            enableZoom={enableZoom}
            minDistance={minDistance}
            maxDistance={maxDistance}
            minPolarAngle={Math.PI / 6}
            maxPolarAngle={Math.PI / 1.5}
            autoRotate={autoRotate}
            autoRotateSpeed={1}
            makeDefault
          />
        </Suspense>
      </Canvas>

      {showControls && !isLoading && !error && (
        <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between pointer-events-none">
          <div className="flex items-center gap-2 pointer-events-auto">
            <Button
              variant="secondary"
              size="sm"
              onClick={resetCamera}
              className="bg-background/80 backdrop-blur-sm"
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              Reset
            </Button>
          </div>

          <div className="flex items-center gap-2 pointer-events-auto">
            {availableColors && availableColors.length > 0 && (
              <div className="relative">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowColorPicker(!showColorPicker)}
                  className="bg-background/80 backdrop-blur-sm"
                >
                  <Palette className="h-4 w-4 mr-1" />
                  Color
                </Button>

                <AnimatePresence>
                  {showColorPicker && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute bottom-full right-0 mb-2 p-2 bg-background/95 backdrop-blur-sm rounded-lg shadow-lg border"
                    >
                      <div className="grid grid-cols-4 gap-1">
                        {availableColors.map((c) => (
                          <button
                            key={c.hex}
                            onClick={() => handleColorChange(c.hex)}
                            className={`garment-color-swatch ${
                              selectedColor === c.hex ? 'garment-color-swatch-selected' : ''
                            }`}
                            title={c.name}
                            aria-label={`Select ${c.name}`}
                            type="button"
                          >
                            <svg viewBox="0 0 24 24" className="garment-color-swatch-icon" aria-hidden="true">
                              <circle cx="12" cy="12" r="10" fill={c.hex} />
                            </svg>
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>
        </div>
      )}

      {!isLoading && !error && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground bg-background/50 backdrop-blur-sm px-3 py-1 rounded-full">
          Drag to rotate • Scroll to zoom
        </div>
      )}
    </div>
  );
}

interface GarmentModelProps {
  url: string;
  color?: string;
  onLoaded?: () => void;
  onError?: (error: string) => void;
}

function GarmentModel({ url, color, onLoaded, onError }: GarmentModelProps) {
  const meshRef = useRef<THREE.Group>(null);

  const { scene } = useGLTF(url, true, true, (loader) => {
    loader.setDRACOLoader(dracoLoader as any);
  });

  const model = useMemo(() => {
    try {
      const cloned = scene.clone(true);

      const box = new THREE.Box3().setFromObject(cloned);
      const center = box.getCenter(new THREE.Vector3());
      cloned.position.sub(center);

      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = maxDim > 0 ? 1.5 / maxDim : 1;
      cloned.scale.setScalar(scale);

      if (color) {
        const colorObj = new THREE.Color(color);
        cloned.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            const material = child.material;
            if (material instanceof THREE.MeshStandardMaterial) {
              material.color.copy(colorObj);
              material.needsUpdate = true;
            }
          }
        });
      }

      cloned.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.castShadow = true;
          child.receiveShadow = true;
        }
      });

      onLoaded?.();
      return cloned;
    } catch {
      onError?.('Failed to process 3D model');
      return scene;
    }
  }, [scene, color, onLoaded, onError]);

  return <primitive ref={meshRef} object={model} />;
}

// Preload common models
useGLTF.preload('/models/default-shirt.glb');
useGLTF.preload('/models/default-pants.glb');

export default GarmentViewer3D;
