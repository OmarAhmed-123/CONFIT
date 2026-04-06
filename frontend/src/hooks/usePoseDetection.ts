/**
 * usePoseDetection — Real-time Pose Detection Hook
 * ===============================================
 * 
 * Uses MediaPipe Pose for client-side body landmark detection.
 * Provides real-time feedback for photo capture quality.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface Keypoint {
  x: number;
  y: number;
  z: number;
  visibility: number;
  name: string;
}

export interface PoseData {
  landmarks: Keypoint[];
  worldLandmarks?: Keypoint[];
  poseScore: number;
  isGoodPose: boolean;
  feedback: string[];
  timestamp: number;
}

export interface PoseDetectionConfig {
  modelComplexity?: 0 | 1 | 2;
  smoothLandmarks?: boolean;
  enableSegmentation?: boolean;
  minDetectionConfidence?: number;
  minTrackingConfidence?: number;
  onPoseDetected?: (pose: PoseData) => void;
  onPoseLost?: () => void;
}

const MEDIAPIPE_LANDMARKS = [
  'nose', 'left_eye_inner', 'left_eye', 'left_eye_outer',
  'right_eye_inner', 'right_eye', 'right_eye_outer',
  'left_ear', 'right_ear', 'mouth_left', 'mouth_right',
  'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
  'left_wrist', 'right_wrist', 'left_pinky', 'right_pinky',
  'left_index', 'right_index', 'left_thumb', 'right_thumb',
  'left_hip', 'right_hip', 'left_knee', 'right_knee',
  'left_ankle', 'right_ankle', 'left_heel', 'right_heel',
  'left_foot_index', 'right_foot_index'
];

export function usePoseDetection(
  videoRef: React.RefObject<HTMLVideoElement>,
  config: PoseDetectionConfig = {}
) {
  const {
    modelComplexity = 1,
    smoothLandmarks = true,
    enableSegmentation = false,
    minDetectionConfidence = 0.5,
    minTrackingConfidence = 0.5,
    onPoseDetected,
    onPoseLost,
  } = config;

  const [poseData, setPoseData] = useState<PoseData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);

  const poseRef = useRef<any>(null);
  const cameraRef = useRef<any>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Initialize MediaPipe
  useEffect(() => {
    let mounted = true;

    const initializePose = async () => {
      try {
        // Dynamically import MediaPipe
        const { Pose } = await import('@mediapipe/pose');
        const { Camera } = await import('@mediapipe/camera_utils');

        if (!mounted) return;

        const pose = new Pose({
          locateFile: (file: string) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
          },
        });

        pose.setOptions({
          modelComplexity,
          smoothLandmarks,
          enableSegmentation,
          minDetectionConfidence,
          minTrackingConfidence,
        });

        pose.onResults((results: any) => {
          if (!mounted) return;

          if (results.poseLandmarks) {
            const landmarks = results.poseLandmarks.map((lm: any, idx: number) => ({
              x: lm.x,
              y: lm.y,
              z: lm.z,
              visibility: lm.visibility || 0,
              name: MEDIAPIPE_LANDMARKS[idx] || `landmark_${idx}`,
            }));

            const { isGoodPose, feedback } = analyzePose(landmarks);
            const poseScore = calculatePoseScore(landmarks);

            const data: PoseData = {
              landmarks,
              worldLandmarks: results.poseWorldLandmarks?.map((lm: any, idx: number) => ({
                x: lm.x,
                y: lm.y,
                z: lm.z,
                visibility: lm.visibility || 0,
                name: MEDIAPIPE_LANDMARKS[idx] || `landmark_${idx}`,
              })),
              poseScore,
              isGoodPose,
              feedback,
              timestamp: Date.now(),
            };

            setPoseData(data);
            onPoseDetected?.(data);
          } else {
            setPoseData(null);
            onPoseLost?.();
          }
        });

        poseRef.current = pose;
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to initialize MediaPipe:', err);
        if (mounted) {
          setError('Failed to load pose detection. Please refresh.');
          setIsLoading(false);
        }
      }
    };

    initializePose();

    return () => {
      mounted = false;
      if (poseRef.current) {
        poseRef.current.close();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [modelComplexity, smoothLandmarks, enableSegmentation, minDetectionConfidence, minTrackingConfidence]);

  // Start detection
  const startDetection = useCallback(async () => {
    if (!videoRef.current || !poseRef.current) return;

    setIsDetecting(true);

    try {
      const { Camera } = await import('@mediapipe/camera_utils');
      
      const camera = new Camera(videoRef.current, {
        onFrame: async () => {
          if (poseRef.current && videoRef.current) {
            await poseRef.current.send({ image: videoRef.current });
          }
        },
        width: 1280,
        height: 720,
      });

      await camera.start();
      cameraRef.current = camera;
    } catch (err) {
      console.error('Failed to start camera:', err);
      setError('Failed to access camera');
      setIsDetecting(false);
    }
  }, [videoRef]);

  // Stop detection
  const stopDetection = useCallback(() => {
    if (cameraRef.current) {
      cameraRef.current.stop();
      cameraRef.current = null;
    }
    setIsDetecting(false);
    setPoseData(null);
  }, []);

  // Capture single frame
  const detectFrame = useCallback(async () => {
    if (!videoRef.current || !poseRef.current) return null;

    try {
      await poseRef.current.send({ image: videoRef.current });
      return poseData;
    } catch (err) {
      console.error('Frame detection failed:', err);
      return null;
    }
  }, [videoRef, poseData]);

  return {
    poseData,
    isLoading,
    error,
    isDetecting,
    startDetection,
    stopDetection,
    detectFrame,
  };
}

/**
 * Analyze pose quality
 */
function analyzePose(landmarks: Keypoint[]): { isGoodPose: boolean; feedback: string[] } {
  const feedback: string[] = [];
  let isGoodPose = true;

  // Check nose visibility (facing camera)
  const nose = landmarks[0];
  if (nose.visibility < 0.7) {
    feedback.push('Please face the camera directly');
    isGoodPose = false;
  }

  // Check shoulder alignment
  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];

  if (leftShoulder.visibility > 0.5 && rightShoulder.visibility > 0.5) {
    const shoulderDiff = Math.abs(leftShoulder.y - rightShoulder.y);
    if (shoulderDiff > 0.1) {
      feedback.push('Level your shoulders');
      isGoodPose = false;
    }
  }

  // Check arms visible
  const leftWrist = landmarks[15];
  const rightWrist = landmarks[16];

  if (leftWrist.visibility < 0.5 && rightWrist.visibility < 0.5) {
    feedback.push('Keep your arms visible for better results');
  }

  // Check distance (body size in frame)
  const leftHip = landmarks[23];
  const rightHip = landmarks[24];

  if (leftHip.visibility > 0.5 && rightHip.visibility > 0.5) {
    const hipWidth = Math.abs(leftHip.x - rightHip.x);

    if (hipWidth < 0.15) {
      feedback.push('Move closer to the camera');
      isGoodPose = false;
    } else if (hipWidth > 0.6) {
      feedback.push('Move back slightly');
      isGoodPose = false;
    }
  }

  // Check if full body visible
  const leftAnkle = landmarks[27];
  const rightAnkle = landmarks[28];

  if (leftAnkle.visibility < 0.3 && rightAnkle.visibility < 0.3) {
    feedback.push('Full body not visible - lower camera or step back');
  }

  return { isGoodPose, feedback };
}

/**
 * Calculate overall pose score
 */
function calculatePoseScore(landmarks: Keypoint[]): float {
  // Key landmarks for try-on
  const keyIndices = [
    0,   // nose
    11, 12,  // shoulders
    13, 14,  // elbows
    15, 16,  // wrists
    23, 24,  // hips
  ];

  const visibilities = keyIndices
    .map(i => landmarks[i]?.visibility || 0)
    .filter(v => v > 0);

  return visibilities.length > 0 
    ? visibilities.reduce((a, b) => a + b, 0) / visibilities.length 
    : 0;
}

/**
 * Get body measurements from pose
 */
export function getBodyMeasurements(landmarks: Keypoint[], imageWidth: number, imageHeight: number) {
  // Shoulder width
  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];
  const shoulderWidth = leftShoulder.visibility > 0.3 && rightShoulder.visibility > 0.3
    ? Math.abs(leftShoulder.x - rightShoulder.x) * imageWidth
    : 0;

  // Hip width
  const leftHip = landmarks[23];
  const rightHip = landmarks[24];
  const hipWidth = leftHip.visibility > 0.3 && rightHip.visibility > 0.3
    ? Math.abs(leftHip.x - rightHip.x) * imageWidth
    : 0;

  // Torso length
  const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
  const hipY = (leftHip.y + rightHip.y) / 2;
  const torsoLength = Math.abs(hipY - shoulderY) * imageHeight;

  // Total height (nose to ankles)
  const nose = landmarks[0];
  const leftAnkle = landmarks[27];
  const rightAnkle = landmarks[28];
  const ankleY = Math.max(
    leftAnkle.visibility > 0.3 ? leftAnkle.y : 0,
    rightAnkle.visibility > 0.3 ? rightAnkle.y : 0
  );
  const totalHeight = ankleY > 0 ? Math.abs(ankleY - nose.y) * imageHeight : 0;

  return {
    shoulderWidth,
    hipWidth,
    torsoLength,
    totalHeight,
    shoulderToHipRatio: hipWidth > 0 ? shoulderWidth / hipWidth : 0,
  };
}

/**
 * Estimate pose angle from landmarks
 */
export function estimatePoseAngle(landmarks: Keypoint[]): number {
  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];

  if (leftShoulder.visibility < 0.3 || rightShoulder.visibility < 0.3) {
    return 0;
  }

  // Calculate shoulder line angle
  const dx = rightShoulder.x - leftShoulder.x;
  const dy = rightShoulder.y - leftShoulder.y;

  const angle = Math.atan2(dy, dx) * (180 / Math.PI);

  return angle;
}

export default usePoseDetection;
