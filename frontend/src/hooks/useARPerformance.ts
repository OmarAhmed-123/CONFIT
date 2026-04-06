/**
 * CONFIT — AR Performance Optimization Hook
 * ==========================================
 * Mobile-optimized performance utilities for AR try-on.
 *
 * Features:
 * - Adaptive frame rate based on device capability
 * - Memory management
 * - Battery optimization
 * - Network-aware processing
 */

import { useState, useEffect, useCallback, useRef } from 'react';

interface PerformanceConfig {
  targetFps: number;
  resolution: { width: number; height: number };
  quality: 'low' | 'medium' | 'high';
  useGpu: boolean;
}

interface DeviceCapabilities {
  isMobile: boolean;
  isLowEnd: boolean;
  hasGpu: boolean;
  cores: number;
  memory: number;
  maxTextureSize: number;
}

/**
 * Detect device capabilities for performance tuning
 */
export function detectDeviceCapabilities(): DeviceCapabilities {
  const navigator_ = window.navigator as any;
  
  // Check if mobile
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );

  // Estimate CPU cores
  const cores = navigator_.hardwareConcurrency || 4;

  // Estimate device memory (Chrome/Edge only)
  const memory = navigator_.deviceMemory || 4;

  // Check for WebGL GPU support
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  let hasGpu = false;
  let maxTextureSize = 4096;

  if (gl && gl instanceof WebGLRenderingContext) {
    hasGpu = true;
    maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
  }

  // Determine if low-end device
  const isLowEnd = isMobile && (cores <= 4 || memory <= 2 || !hasGpu);

  return {
    isMobile,
    isLowEnd,
    hasGpu,
    cores,
    memory,
    maxTextureSize,
  };
}

/**
 * Get optimal performance config based on device
 */
export function getOptimalConfig(capabilities: DeviceCapabilities): PerformanceConfig {
  if (capabilities.isLowEnd) {
    return {
      targetFps: 15,
      resolution: { width: 480, height: 640 },
      quality: 'low',
      useGpu: false,
    };
  }

  if (capabilities.isMobile) {
    return {
      targetFps: 24,
      resolution: { width: 640, height: 854 },
      quality: 'medium',
      useGpu: capabilities.hasGpu,
    };
  }

  // Desktop / high-end
  return {
    targetFps: 30,
    resolution: { width: 1280, height: 720 },
    quality: 'high',
    useGpu: capabilities.hasGpu,
  };
}

/**
 * Hook for AR performance management
 */
export function useARPerformance() {
  const [capabilities] = useState<DeviceCapabilities>(() => detectDeviceCapabilities());
  const [config, setConfig] = useState<PerformanceConfig>(() => getOptimalConfig(capabilities));
  const [currentFps, setCurrentFps] = useState(0);
  const [isThrottled, setIsThrottled] = useState(false);

  const frameTimesRef = useRef<number[]>([]);
  const lastFrameTimeRef = useRef<number>(0);
  const dropCountRef = useRef<number>(0);

  /**
   * Record frame time for FPS calculation
   */
  const recordFrame = useCallback(() => {
    const now = performance.now();
    
    if (lastFrameTimeRef.current > 0) {
      const frameTime = now - lastFrameTimeRef.current;
      frameTimesRef.current.push(frameTime);

      // Keep last 60 frames
      if (frameTimesRef.current.length > 60) {
        frameTimesRef.current.shift();
      }

      // Calculate FPS
      const avgFrameTime = frameTimesRef.current.reduce((a, b) => a + b, 0) / frameTimesRef.current.length;
      const fps = Math.round(1000 / avgFrameTime);
      setCurrentFps(fps);

      // Check for frame drops
      if (frameTime > 1000 / (config.targetFps * 0.8)) {
        dropCountRef.current++;
      }

      // Throttle if too many drops
      if (dropCountRef.current > 10 && !isThrottled) {
        setIsThrottled(true);
        // Reduce quality
        if (config.quality === 'high') {
          setConfig((prev) => ({ ...prev, quality: 'medium', targetFps: 24 }));
        } else if (config.quality === 'medium') {
          setConfig((prev) => ({ ...prev, quality: 'low', targetFps: 15 }));
        }
      }
    }

    lastFrameTimeRef.current = now;
  }, [config.targetFps, config.quality, isThrottled]);

  /**
   * Reset throttling state
   */
  const resetThrottle = useCallback(() => {
    dropCountRef.current = 0;
    setIsThrottled(false);
    setConfig(getOptimalConfig(capabilities));
  }, [capabilities]);

  /**
   * Check if should skip frame (for frame rate limiting)
   */
  const shouldSkipFrame = useCallback(() => {
    const frameInterval = 1000 / config.targetFps;
    const now = performance.now();
    const elapsed = now - lastFrameTimeRef.current;

    return elapsed < frameInterval * 0.9; // 10% tolerance
  }, [config.targetFps]);

  /**
   * Get optimal canvas size
   */
  const getOptimalCanvasSize = useCallback((videoWidth: number, videoHeight: number) => {
    const { resolution } = config;
    const aspectRatio = videoWidth / videoHeight;

    let width: number;
    let height: number;

    if (aspectRatio > resolution.width / resolution.height) {
      width = Math.min(videoWidth, resolution.width);
      height = width / aspectRatio;
    } else {
      height = Math.min(videoHeight, resolution.height);
      width = height * aspectRatio;
    }

    // Ensure even dimensions for video encoding
    width = Math.floor(width / 2) * 2;
    height = Math.floor(height / 2) * 2;

    return { width, height };
  }, [config]);

  /**
   * Cleanup function for memory management
   */
  const cleanup = useCallback(() => {
    frameTimesRef.current = [];
    dropCountRef.current = 0;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  return {
    capabilities,
    config,
    currentFps,
    isThrottled,
    recordFrame,
    shouldSkipFrame,
    getOptimalCanvasSize,
    resetThrottle,
    cleanup,
  };
}

/**
 * Hook for battery-aware processing
 */
export function useBatteryAware() {
  const [batteryLevel, setBatteryLevel] = useState<number | null>(null);
  const [isCharging, setIsCharging] = useState<boolean | null>(null);
  const [shouldConservePower, setShouldConservePower] = useState(false);

  useEffect(() => {
    const navigator_ = window.navigator as any;

    if (!navigator_.getBattery) {
      return;
    }

    let battery: any;

    navigator_.getBattery().then((b: any) => {
      battery = b;
      setBatteryLevel(b.level);
      setIsCharging(b.charging);

      const updatePowerMode = () => {
        // Conserve power if battery is low and not charging
        setShouldConservePower(b.level < 0.2 && !b.charging);
      };

      b.addEventListener('levelchange', () => {
        setBatteryLevel(b.level);
        updatePowerMode();
      });

      b.addEventListener('chargingchange', () => {
        setIsCharging(b.charging);
        updatePowerMode();
      });

      updatePowerMode();
    });

    return () => {
      if (battery) {
        battery.removeEventListener('levelchange', () => {});
        battery.removeEventListener('chargingchange', () => {});
      }
    };
  }, []);

  return {
    batteryLevel,
    isCharging,
    shouldConservePower,
  };
}

/**
 * Hook for network-aware processing
 */
export function useNetworkAware() {
  const [connectionType, setConnectionType] = useState<string>('unknown');
  const [effectiveType, setEffectiveType] = useState<string>('4g');
  const [shouldReduceData, setShouldReduceData] = useState(false);

  useEffect(() => {
    const connection = (navigator as any).connection;

    if (!connection) {
      return;
    }

    const updateConnection = () => {
      setConnectionType(connection.type || 'unknown');
      setEffectiveType(connection.effectiveType || '4g');
      
      // Reduce data on slow connections
      setShouldReduceData(
        connection.effectiveType === 'slow-2g' ||
        connection.effectiveType === '2g' ||
        connection.effectiveType === '3g' ||
        connection.saveData
      );
    };

    updateConnection();

    connection.addEventListener('change', updateConnection);

    return () => {
      connection.removeEventListener('change', updateConnection);
    };
  }, []);

  return {
    connectionType,
    effectiveType,
    shouldReduceData,
  };
}

export default useARPerformance;
