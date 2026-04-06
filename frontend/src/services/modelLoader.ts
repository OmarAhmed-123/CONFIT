/**
 * Model Loader Service
 * ====================
 * Handles glTF loading with Draco compression for 3D garments.
 */

import * as THREE from 'three';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/examples/jsm/loaders/KTX2Loader.js';

// ===========================================
// Loader Configuration
// ===========================================

// Draco decoder configuration
const dracoLoader = new DRACOLoader();
// Use CDN for Draco decoder (more reliable)
dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
dracoLoader.setDecoderConfig({ type: 'js' });

// glTF loader with Draco support
const gltfLoader = new GLTFLoader();
gltfLoader.setDRACOLoader(dracoLoader);

// KTX2 loader for compressed textures (optional)
let ktx2Loader: KTX2Loader | null = null;

function getKTX2Loader(renderer: THREE.WebGLRenderer): KTX2Loader {
  if (!ktx2Loader) {
    ktx2Loader = new KTX2Loader(renderer);
    ktx2Loader.setTranscoderPath('/ktx2/');
    ktx2Loader.detectSupport(renderer);
  }
  return ktx2Loader;
}

// ===========================================
// Types
// ===========================================

export interface LoadedModel {
  scene: THREE.Group;
  animations: THREE.AnimationClip[];
  cameras: THREE.Camera[];
  asset: Record<string, unknown>;
  parser: unknown;
}

export interface ModelLoadOptions {
  onProgress?: (progress: number) => void;
  castShadow?: boolean;
  receiveShadow?: boolean;
  center?: boolean;
  scale?: number | 'auto';
  envMapIntensity?: number;
  useCompressedTextures?: boolean;
}

export interface ModelInfo {
  url: string;
  vertexCount: number;
  meshCount: number;
  materialCount: number;
  hasAnimations: boolean;
  boundingBox: THREE.Box3;
  size: THREE.Vector3;
}

// ===========================================
// Model Cache
// ===========================================

const modelCache = new Map<string, Promise<LoadedModel>>();
const modelInfoCache = new Map<string, ModelInfo>();

// ===========================================
// Loading Functions
// ===========================================

/**
 * Load glTF model with error handling and progress
 */
export async function loadGLTFModel(
  url: string,
  options: ModelLoadOptions = {}
): Promise<LoadedModel> {
  // Check cache first
  if (modelCache.has(url)) {
    console.log(`[ModelLoader] Using cached model: ${url}`);
    return modelCache.get(url)!;
  }

  const loadPromise = new Promise<LoadedModel>((resolve, reject) => {
    console.log(`[ModelLoader] Loading model: ${url}`);

    gltfLoader.load(
      url,
      (gltf) => {
        const { scene, animations, cameras, asset, parser } = gltf;

        // Configure shadows
        if (options.castShadow !== false) {
          scene.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.castShadow = true;
            }
          });
        }

        if (options.receiveShadow !== false) {
          scene.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.receiveShadow = true;
            }
          });
        }

        // Center model
        if (options.center !== false) {
          const box = new THREE.Box3().setFromObject(scene);
          const center = box.getCenter(new THREE.Vector3());
          scene.position.sub(center);
        }

        // Auto-scale
        if (options.scale === 'auto') {
          const box = new THREE.Box3().setFromObject(scene);
          const size = box.getSize(new THREE.Vector3());
          const maxDim = Math.max(size.x, size.y, size.z);
          const scale = 1.5 / maxDim;
          scene.scale.setScalar(scale);
        } else if (typeof options.scale === 'number') {
          scene.scale.setScalar(options.scale);
        }

        // Environment map intensity
        if (options.envMapIntensity !== undefined) {
          scene.traverse((child) => {
            if (child instanceof THREE.Mesh && child.material) {
              const material = child.material as THREE.MeshStandardMaterial;
              if (material.isMeshStandardMaterial) {
                material.envMapIntensity = options.envMapIntensity!;
              }
            }
          });
        }

        console.log(`[ModelLoader] Loaded: ${url}`);
        resolve({ scene, animations, cameras, asset, parser });
      },
      (progress) => {
        if (options.onProgress && progress.total > 0) {
          const percent = (progress.loaded / progress.total) * 100;
          options.onProgress(percent);
        }
      },
      (error) => {
        console.error(`[ModelLoader] Failed to load ${url}:`, error);
        reject(new Error(`Failed to load model: ${error.message || 'Unknown error'}`));
      }
    );
  });

  // Cache the promise
  modelCache.set(url, loadPromise);

  return loadPromise;
}

/**
 * Preload model for faster access later
 */
export function preloadModel(url: string): Promise<LoadedModel> {
  return loadGLTFModel(url);
}

/**
 * Load multiple models in parallel
 */
export async function loadModelsParallel(
  urls: string[],
  options: ModelLoadOptions = {}
): Promise<Map<string, LoadedModel>> {
  const results = new Map<string, LoadedModel>();

  await Promise.all(
    urls.map(async (url) => {
      const model = await loadGLTFModel(url, options);
      results.set(url, model);
    })
  );

  return results;
}

/**
 * Load model with LOD (Level of Detail)
 */
export async function loadModelWithLOD(
  lodUrls: { lod0: string; lod1: string; lod2: string },
  options: ModelLoadOptions = {}
): Promise<{ lod0: LoadedModel; lod1: LoadedModel; lod2: LoadedModel }> {
  const [lod0, lod1, lod2] = await Promise.all([
    loadGLTFModel(lodUrls.lod0, options),
    loadGLTFModel(lodUrls.lod1, options),
    loadGLTFModel(lodUrls.lod2, options),
  ]);

  return { lod0, lod1, lod2 };
}

// ===========================================
// Model Analysis
// ===========================================

/**
 * Get model info without full loading
 */
export async function getModelInfo(url: string): Promise<ModelInfo> {
  if (modelInfoCache.has(url)) {
    return modelInfoCache.get(url)!;
  }

  const { scene, animations } = await loadGLTFModel(url);

  let vertexCount = 0;
  let meshCount = 0;
  let materialCount = 0;
  const materials = new Set<THREE.Material>();

  scene.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      meshCount++;
      const geometry = child.geometry;
      if (geometry.attributes.position) {
        vertexCount += geometry.attributes.position.count;
      }
      if (Array.isArray(child.material)) {
        child.material.forEach((m) => materials.add(m));
      } else if (child.material) {
        materials.add(child.material);
      }
    }
  });

  materialCount = materials.size;
  const boundingBox = new THREE.Box3().setFromObject(scene);
  const size = boundingBox.getSize(new THREE.Vector3());

  const info: ModelInfo = {
    url,
    vertexCount,
    meshCount,
    materialCount,
    hasAnimations: animations.length > 0,
    boundingBox,
    size,
  };

  modelInfoCache.set(url, info);
  return info;
}

// ===========================================
// Material Utilities
// ===========================================

/**
 * Apply color to model materials
 */
export function applyModelColor(model: THREE.Group, color: string): void {
  const colorObj = new THREE.Color(color);

  model.traverse((child) => {
    if (child instanceof THREE.Mesh && child.material) {
      const material = child.material as THREE.MeshStandardMaterial;
      if (material.isMeshStandardMaterial) {
        material.color.copy(colorObj);
        material.needsUpdate = true;
      }
    }
  });
}

/**
 * Apply texture to model
 */
export function applyModelTexture(
  model: THREE.Group,
  texture: THREE.Texture,
  channel: 'map' | 'normalMap' | 'roughnessMap' | 'metalnessMap' = 'map'
): void {
  model.traverse((child) => {
    if (child instanceof THREE.Mesh && child.material) {
      const material = child.material as THREE.MeshStandardMaterial;
      if (material.isMeshStandardMaterial) {
        material[channel] = texture;
        material.needsUpdate = true;
      }
    }
  });
}

/**
 * Create material variant
 */
export function createMaterialVariant(
  baseMaterial: THREE.MeshStandardMaterial,
  overrides: Partial<THREE.MeshStandardMaterialParameters>
): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    ...baseMaterial,
    ...overrides,
  });
}

// ===========================================
// Cleanup
// ===========================================

/**
 * Dispose model and free memory
 */
export function disposeModel(model: THREE.Group): void {
  model.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      // Dispose geometry
      if (child.geometry) {
        child.geometry.dispose();
      }

      // Dispose materials
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((material) => material.dispose());
        } else {
          child.material.dispose();
        }
      }
    }
  });
}

/**
 * Clear all caches
 */
export function clearModelCache(): void {
  modelCache.clear();
  modelInfoCache.clear();
  dracoLoader.dispose();

  console.log('[ModelLoader] Cache cleared');
}

// ===========================================
// Export Default
// ===========================================

export default {
  loadGLTFModel,
  preloadModel,
  loadModelsParallel,
  loadModelWithLOD,
  getModelInfo,
  applyModelColor,
  applyModelTexture,
  createMaterialVariant,
  disposeModel,
  clearModelCache,
};
