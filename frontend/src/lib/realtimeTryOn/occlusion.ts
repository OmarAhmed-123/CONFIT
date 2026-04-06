import type { Point2 } from './tpsWarp';
import type { BodyAnchors } from './anchors';

function thickPolygonPath(
  ctx: CanvasRenderingContext2D,
  points: Point2[],
  canvasW: number,
  canvasH: number,
  lineWidthFrac: number
): void {
  ctx.beginPath();
  const lw = Math.max(18, lineWidthFrac * Math.min(canvasW, canvasH));
  ctx.lineWidth = lw;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  const p = points.map((q) => ({ x: q.x * canvasW, y: q.y * canvasH }));
  ctx.moveTo(p[0].x, p[0].y);
  for (let i = 1; i < p.length; i++) ctx.lineTo(p[i].x, p[i].y);
  ctx.closePath();
}

/**
 * Punch holes in the current canvas alpha where arms overlap the torso garment region
 * (approximate “garment behind arms”).
 */
export function punchArmOcclusion(
  ctx: CanvasRenderingContext2D,
  a: BodyAnchors,
  canvasW: number,
  canvasH: number
): void {
  ctx.save();
  ctx.globalCompositeOperation = 'destination-out';
  ctx.fillStyle = 'rgba(0,0,0,1)';

  /** Left arm: shoulder → elbow → wrist (expanded). */
  const leftArm: Point2[] = [a.shoulderLeft, a.elbowLeft, a.torsoCenter];
  thickPolygonPath(ctx, leftArm, canvasW, canvasH, 0.09);
  ctx.fill();

  const rightArm: Point2[] = [a.shoulderRight, a.elbowRight, a.torsoCenter];
  thickPolygonPath(ctx, rightArm, canvasW, canvasH, 0.09);
  ctx.fill();

  ctx.restore();
}

/**
 * Remove garment from face / hair band (never modify face region).
 */
export function punchFaceSafeBand(
  ctx: CanvasRenderingContext2D,
  noseY: number,
  canvasW: number,
  canvasH: number,
  marginFrac = 0.02
): void {
  const y = Math.max(0, (noseY - marginFrac) * canvasH);
  ctx.save();
  ctx.globalCompositeOperation = 'destination-out';
  ctx.fillStyle = 'rgba(0,0,0,1)';
  ctx.fillRect(0, 0, canvasW, y);
  ctx.restore();
}
