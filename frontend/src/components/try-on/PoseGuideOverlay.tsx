/**
 * PoseGuideOverlay — Real-time Pose Guidance for Photo Capture
 * ============================================================
 * 
 * Displays visual feedback during photo capture:
 * - Body outline guide
 * - Pose quality indicators
 * - Real-time feedback messages
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Check, AlertCircle, Camera, ArrowUp, ArrowDown, RotateCcw } from 'lucide-react';
import type { PoseData } from '@/hooks/usePoseDetection';
import { createTransition } from '@/motion';

interface PoseGuideOverlayProps {
  poseData: PoseData | null;
  isCapturing: boolean;
  showGuide: boolean;
  className?: string;
}

export function PoseGuideOverlay({
  poseData,
  isCapturing,
  showGuide,
  className = '',
}: PoseGuideOverlayProps) {
  const isGoodPose = poseData?.isGoodPose ?? false;
  const feedback = poseData?.feedback ?? [];
  const poseScore = poseData?.poseScore ?? 0;

  return (
    <div className={`absolute inset-0 pointer-events-none ${className}`}>
      {/* Body Guide Outline */}
      {showGuide && (
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 1 1"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Ideal pose outline */}
          <ellipse
            cx="0.5"
            cy="0.12"
            rx="0.06"
            ry="0.07"
            fill="none"
            stroke={isGoodPose ? '#22c55e' : '#f59e0b'}
            strokeWidth="0.003"
            strokeDasharray="0.01 0.005"
            opacity={0.6}
          />
          
          {/* Torso guide */}
          <rect
            x="0.35"
            y="0.19"
            width="0.3"
            height="0.25"
            fill="none"
            stroke={isGoodPose ? '#22c55e' : '#f59e0b'}
            strokeWidth="0.003"
            strokeDasharray="0.01 0.005"
            rx="0.05"
            opacity={0.6}
          />
          
          {/* Arms guide */}
          <line
            x1="0.35"
            y1="0.22"
            x2="0.2"
            y2="0.35"
            stroke={isGoodPose ? '#22c55e' : '#f59e0b'}
            strokeWidth="0.003"
            strokeDasharray="0.01 0.005"
            opacity={0.6}
          />
          <line
            x1="0.65"
            y1="0.22"
            x2="0.8"
            y2="0.35"
            stroke={isGoodPose ? '#22c55e' : '#f59e0b'}
            strokeWidth="0.003"
            strokeDasharray="0.01 0.005"
            opacity={0.6}
          />
          
          {/* Legs guide */}
          <line
            x1="0.42"
            y1="0.44"
            x2="0.4"
            y2="0.75"
            stroke={isGoodPose ? '#22c55e' : '#f59e0b'}
            strokeWidth="0.003"
            strokeDasharray="0.01 0.005"
            opacity={0.6}
          />
          <line
            x1="0.58"
            y1="0.44"
            x2="0.6"
            y2="0.75"
            stroke={isGoodPose ? '#22c55e' : '#f59e0b'}
            strokeWidth="0.003"
            strokeDasharray="0.01 0.005"
            opacity={0.6}
          />
        </svg>
      )}

      {/* Pose Landmarks (debug view) */}
      {poseData && showGuide && (
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 1 1"
          preserveAspectRatio="xMidYMid meet"
        >
          {poseData.landmarks.map((landmark, idx) => {
            if (landmark.visibility < 0.3) return null;
            
            // Key landmarks to show
            const keyIndices = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];
            if (!keyIndices.includes(idx)) return null;
            
            return (
              <circle
                key={idx}
                cx={landmark.x}
                cy={landmark.y}
                r="0.008"
                fill={isGoodPose ? '#22c55e' : '#f59e0b'}
                opacity={landmark.visibility}
              />
            );
          })}
          
          {/* Connect body parts */}
          {poseData.landmarks[11]?.visibility > 0.3 && poseData.landmarks[12]?.visibility > 0.3 && (
            <line
              x1={poseData.landmarks[11].x}
              y1={poseData.landmarks[11].y}
              x2={poseData.landmarks[12].x}
              y2={poseData.landmarks[12].y}
              stroke={isGoodPose ? '#22c55e' : '#f59e0b'}
              strokeWidth="0.003"
              opacity={0.5}
            />
          )}
        </svg>
      )}

      {/* Status Indicator */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2">
        <AnimatePresence mode="wait">
          {isCapturing ? (
            <motion.div
              key="capturing"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex items-center gap-2 bg-background/90 backdrop-blur-sm px-4 py-2 rounded-full shadow-lg"
            >
              <Camera className="h-4 w-4 text-accent animate-pulse" />
              <span className="text-sm font-medium">Capturing...</span>
            </motion.div>
          ) : poseData ? (
            <motion.div
              key={isGoodPose ? 'good' : 'adjust'}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className={`flex items-center gap-2 px-4 py-2 rounded-full shadow-lg ${
                isGoodPose
                  ? 'bg-green-500/90 backdrop-blur-sm'
                  : 'bg-yellow-500/90 backdrop-blur-sm'
              }`}
            >
              {isGoodPose ? (
                <>
                  <Check className="h-4 w-4 text-white" />
                  <span className="text-sm font-medium text-white">Perfect pose!</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 text-white" />
                  <span className="text-sm font-medium text-white">Adjust pose</span>
                </>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="no-pose"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex items-center gap-2 bg-background/90 backdrop-blur-sm px-4 py-2 rounded-full shadow-lg"
            >
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Position yourself in frame</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Feedback Messages */}
      <div className="absolute bottom-20 left-1/2 -translate-x-1/2 max-w-[80%]">
        <AnimatePresence mode="wait">
          {feedback.length > 0 && !isGoodPose && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex flex-col items-center gap-1"
            >
              {feedback.slice(0, 2).map((msg, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={createTransition({ delay: idx * 0.1 })}
                  className="flex items-center gap-2 bg-background/90 backdrop-blur-sm px-3 py-1.5 rounded-full shadow-md"
                >
                  <FeedbackIcon message={msg} />
                  <span className="text-xs font-medium">{msg}</span>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Quality Score (debug) */}
      {poseData && (
        <div className="absolute bottom-4 right-4 bg-background/80 backdrop-blur-sm px-2 py-1 rounded text-xs">
          Score: {(poseScore * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}

/**
 * Icon for feedback message
 */
function FeedbackIcon({ message }: { message: string }) {
  const lowerMsg = message.toLowerCase();
  
  if (lowerMsg.includes('closer')) {
    return <ArrowUp className="h-3 w-3" />;
  }
  if (lowerMsg.includes('back') || lowerMsg.includes('step')) {
    return <ArrowDown className="h-3 w-3" />;
  }
  if (lowerMsg.includes('rotate') || lowerMsg.includes('face')) {
    return <RotateCcw className="h-3 w-3" />;
  }
  
  return <AlertCircle className="h-3 w-3" />;
}

export default PoseGuideOverlay;
