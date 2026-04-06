import { BLAZEPOSE_MODEL_TYPE } from './constants';

export type LoadedPoseBackend = 'blazepose' | 'movenet';

export async function createRealtimePoseDetector(): Promise<{
  detector: import('@tensorflow-models/pose-detection').PoseDetector;
  backend: LoadedPoseBackend;
}> {
  const tf = await import('@tensorflow/tfjs');
  try {
    await import('@tensorflow/tfjs-backend-webgl');
    await tf.setBackend('webgl');
  } catch {
    await tf.setBackend('cpu');
  }
  await tf.ready();

  const poseDetection = await import('@tensorflow-models/pose-detection');

  try {
    const detector = await poseDetection.createDetector(
      poseDetection.SupportedModels.BlazePose,
      {
        runtime: 'tfjs',
        modelType: BLAZEPOSE_MODEL_TYPE,
        enableSmoothing: true,
      }
    );
    return { detector, backend: 'blazepose' };
  } catch (e) {
    console.warn('BlazePose load failed, falling back to MoveNet:', e);
    const detector = await poseDetection.createDetector(
      poseDetection.SupportedModels.MoveNet,
      {
        modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING,
        enableSmoothing: true,
      }
    );
    return { detector, backend: 'movenet' };
  }
}
