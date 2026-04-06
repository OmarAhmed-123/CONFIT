/** Temporal blend for anchor positions (reduces jitter). */
export const PREVIOUS_FRAME_WEIGHT = 0.7;
export const CURRENT_FRAME_WEIGHT = 0.3;

/** Target pose inference rate (ms between estimates). ~30 FPS. */
export const POSE_INTERVAL_MS = 33;

/** BlazePose model: lite balances latency vs accuracy for real-time. */
export const BLAZEPOSE_MODEL_TYPE = 'lite' as const;
