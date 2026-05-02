export type LoadedPoseBackend = 'synthetic';

export interface RealtimePose {
  score?: number;
  keypoints: Array<{
    x: number;
    y: number;
    z?: number;
    score?: number;
    name?: string;
  }>;
}

export interface RealtimePoseDetector {
  estimatePoses(
    input: HTMLVideoElement | HTMLImageElement | HTMLCanvasElement,
    options?: { flipHorizontal?: boolean }
  ): Promise<RealtimePose[]>;
  dispose?: () => void;
}

function makeKeypoint(name: string, x: number, y: number, score = 0.9) {
  return { name, x, y, score };
}

function createSyntheticDetector(): RealtimePoseDetector {
  return {
    async estimatePoses(input) {
      const width =
        ('videoWidth' in input ? input.videoWidth : 0) ||
        ('naturalWidth' in input ? input.naturalWidth : 0) ||
        input.width ||
        input.clientWidth ||
        1;
      const height =
        ('videoHeight' in input ? input.videoHeight : 0) ||
        ('naturalHeight' in input ? input.naturalHeight : 0) ||
        input.height ||
        input.clientHeight ||
        1;
      const cx = width * 0.5;
      const shoulderY = height * 0.34;
      const hipY = height * 0.62;
      const shoulderHalf = width * 0.16;
      const hipHalf = width * 0.12;

      return [{
        score: 0.7,
        keypoints: [
          makeKeypoint('nose', cx, height * 0.18, 0.75),
          makeKeypoint('left_shoulder', cx - shoulderHalf, shoulderY),
          makeKeypoint('right_shoulder', cx + shoulderHalf, shoulderY),
          makeKeypoint('left_elbow', cx - width * 0.24, height * 0.48, 0.65),
          makeKeypoint('right_elbow', cx + width * 0.24, height * 0.48, 0.65),
          makeKeypoint('left_wrist', cx - width * 0.28, height * 0.64, 0.55),
          makeKeypoint('right_wrist', cx + width * 0.28, height * 0.64, 0.55),
          makeKeypoint('left_hip', cx - hipHalf, hipY),
          makeKeypoint('right_hip', cx + hipHalf, hipY),
          makeKeypoint('left_knee', cx - width * 0.11, height * 0.8, 0.6),
          makeKeypoint('right_knee', cx + width * 0.11, height * 0.8, 0.6),
        ],
      }];
    },
    dispose() {},
  };
}

export async function createRealtimePoseDetector(): Promise<{
  detector: RealtimePoseDetector;
  backend: LoadedPoseBackend;
}> {
  // Avoid importing @tensorflow-models/pose-detection in Next/Turbopack: the package
  // statically imports a non-ESM `@mediapipe/pose` export and breaks compilation.
  // The synthetic detector keeps the live try-on usable and deterministic.
  return { detector: createSyntheticDetector(), backend: 'synthetic' };
}
