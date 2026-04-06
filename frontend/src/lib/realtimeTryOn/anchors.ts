import type { Point2 } from './tpsWarp';
import { CURRENT_FRAME_WEIGHT, PREVIOUS_FRAME_WEIGHT } from './constants';

export type BodyAnchors = {
  neck: Point2;
  shoulderLeft: Point2;
  shoulderRight: Point2;
  torsoCenter: Point2;
  hipLeft: Point2;
  hipRight: Point2;
  elbowLeft: Point2;
  elbowRight: Point2;
  /** Normalized [0,1] — used for face-safe mask. */
  noseY: number;
  confidence: number;
};

export type KeypointLike = { name?: string; x: number; y: number; score?: number; visibility?: number };

function scoreOf(k: KeypointLike | undefined): number {
  if (!k) return 0;
  return k.score ?? k.visibility ?? 0;
}

function find(kps: KeypointLike[], name: string): KeypointLike | undefined {
  return kps.find((k) => k.name === name);
}

/**
 * Muscle-aware anchor set from pose keypoints (normalized 0–1, image coords).
 */
export function computeBodyAnchors(kps: KeypointLike[]): BodyAnchors | null {
  const nose = find(kps, 'nose');
  const ls = find(kps, 'left_shoulder');
  const rs = find(kps, 'right_shoulder');
  const lh = find(kps, 'left_hip');
  const rh = find(kps, 'right_hip');
  const le = find(kps, 'left_elbow');
  const re = find(kps, 'right_elbow');

  if (!ls || !rs) return null;

  const minConf = Math.min(scoreOf(ls), scoreOf(rs));
  if (minConf < 0.25) return null;

  const midShoulderX = (ls.x + rs.x) / 2;
  const midShoulderY = (ls.y + rs.y) / 2;

  /** Neck: between shoulders, biased toward nose when visible. */
  let neckX = midShoulderX;
  let neckY = midShoulderY - Math.abs(rs.x - ls.x) * 0.35;
  if (nose && scoreOf(nose) > 0.35) {
    neckX = midShoulderX * 0.55 + nose.x * 0.45;
    neckY = Math.min(neckY, nose.y + Math.abs(rs.y - ls.y) * 0.15);
  }

  const torsoCenter: Point2 = {
    x: midShoulderX * 0.5 + (lh && rh ? (lh.x + rh.x) / 2 : midShoulderX) * 0.5,
    y:
      midShoulderY * 0.45 +
      (lh && rh ? (lh.y + rh.y) / 2 : midShoulderY + Math.abs(rs.x - ls.x) * 0.9) * 0.55,
  };

  const hipLeft: Point2 = lh
    ? { x: lh.x, y: lh.y }
    : { x: midShoulderX - Math.abs(rs.x - ls.x) * 0.55, y: torsoCenter.y + Math.abs(rs.x - ls.x) * 0.85 };
  const hipRight: Point2 = rh
    ? { x: rh.x, y: rh.y }
    : { x: midShoulderX + Math.abs(rs.x - ls.x) * 0.55, y: torsoCenter.y + Math.abs(rs.x - ls.x) * 0.85 };

  const elbowLeft: Point2 = le && scoreOf(le) > 0.2 ? { x: le.x, y: le.y } : { x: ls.x, y: ls.y + 0.08 };
  const elbowRight: Point2 = re && scoreOf(re) > 0.2 ? { x: re.x, y: re.y } : { x: rs.x, y: rs.y + 0.08 };

  return {
    neck: { x: neckX, y: neckY },
    shoulderLeft: { x: ls.x, y: ls.y },
    shoulderRight: { x: rs.x, y: rs.y },
    torsoCenter,
    hipLeft,
    hipRight,
    elbowLeft,
    elbowRight,
    noseY: nose ? nose.y : neckY + 0.02,
    confidence: minConf,
  };
}

export function smoothAnchors(prev: BodyAnchors | null, curr: BodyAnchors): BodyAnchors {
  if (!prev) return curr;

  const blend = (a: Point2, b: Point2): Point2 => ({
    x: a.x * PREVIOUS_FRAME_WEIGHT + b.x * CURRENT_FRAME_WEIGHT,
    y: a.y * PREVIOUS_FRAME_WEIGHT + b.y * CURRENT_FRAME_WEIGHT,
  });

  return {
    neck: blend(prev.neck, curr.neck),
    shoulderLeft: blend(prev.shoulderLeft, curr.shoulderLeft),
    shoulderRight: blend(prev.shoulderRight, curr.shoulderRight),
    torsoCenter: blend(prev.torsoCenter, curr.torsoCenter),
    hipLeft: blend(prev.hipLeft, curr.hipLeft),
    hipRight: blend(prev.hipRight, curr.hipRight),
    elbowLeft: blend(prev.elbowLeft, curr.elbowLeft),
    elbowRight: blend(prev.elbowRight, curr.elbowRight),
    noseY: prev.noseY * PREVIOUS_FRAME_WEIGHT + curr.noseY * CURRENT_FRAME_WEIGHT,
    confidence: curr.confidence,
  };
}

/**
 * Canonical garment-space control points (0–1): top-left oriented flat lay.
 * Paired with canvas anchors for TPS.
 */
export function garmentControlPoints(): Point2[] {
  return [
    { x: 0.5, y: 0.04 }, // neck
    { x: 0.1, y: 0.12 }, // L shoulder
    { x: 0.9, y: 0.12 }, // R shoulder
    { x: 0.5, y: 0.42 }, // torso center
    { x: 0.14, y: 0.88 }, // L hip
    { x: 0.86, y: 0.88 }, // R hip
    { x: 0.06, y: 0.38 }, // L elbow guide
    { x: 0.94, y: 0.38 }, // R elbow guide
  ];
}

export function anchorsToCanvasPoints(a: BodyAnchors): Point2[] {
  return [
    a.neck,
    a.shoulderLeft,
    a.shoulderRight,
    a.torsoCenter,
    a.hipLeft,
    a.hipRight,
    a.elbowLeft,
    a.elbowRight,
  ];
}
