import type { ArOverlayCategory } from '@/lib/arGarmentCategory';
import { affineFromTriangle } from './affine';
import { anchorsToCanvasPoints, garmentControlPoints, type BodyAnchors } from './anchors';
import { evaluateTPS1D, fitDisplacementTPS, type Point2 } from './tpsWarp';
import { punchArmOcclusion, punchFaceSafeBand } from './occlusion';

const GRID = 7;

function categoryVerticalRange(cat: ArOverlayCategory): { top: number; bottom: number } {
  switch (cat) {
    case 'pants':
      return { top: 0.38, bottom: 0.98 };
    case 'dress':
      return { top: 0.04, bottom: 0.98 };
    case 'outerwear':
      return { top: 0.02, bottom: 0.72 };
    case 'tops':
    default:
      return { top: 0.02, bottom: 0.62 };
  }
}

/** Build grid vertices in garment normalized space and warped canvas pixels. */
function buildWarpGrid(
  imgW: number,
  imgH: number,
  canvasW: number,
  canvasH: number,
  cat: ArOverlayCategory,
  destControl: Point2[]
): { srcPx: Point2[][]; dstPx: Point2[][] } | null {
  const srcCtl = garmentControlPoints();
  const vr = categoryVerticalRange(cat);
  const tps = fitDisplacementTPS(srcCtl, destControl);
  if (!tps) return null;

  const srcPx: Point2[][] = [];
  const dstPx: Point2[][] = [];

  for (let j = 0; j <= GRID; j++) {
    const rowS: Point2[] = [];
    const rowD: Point2[] = [];
    const v = j / GRID;
    for (let i = 0; i <= GRID; i++) {
      const u = i / GRID;
      /** Crop garment UV to category vertical band (reduces stretch at extremes). */
      const gu = u;
      const gv = vr.top + v * (vr.bottom - vr.top);
      const srcNorm: Point2 = { x: gu, y: gv };
      const dx = evaluateTPS1D(tps.tpsX, srcNorm);
      const dy = evaluateTPS1D(tps.tpsY, srcNorm);
      const destN: Point2 = { x: srcNorm.x + dx, y: srcNorm.y + dy };
      rowS.push({ x: gu * imgW, y: gv * imgH });
      rowD.push({ x: destN.x * canvasW, y: destN.y * canvasH });
    }
    srcPx.push(rowS);
    dstPx.push(rowD);
  }

  return { srcPx, dstPx };
}

function drawTriangle(
  ctx: CanvasRenderingContext2D,
  img: CanvasImageSource,
  imgW: number,
  imgH: number,
  s0: Point2,
  s1: Point2,
  s2: Point2,
  d0: Point2,
  d1: Point2,
  d2: Point2
): void {
  const aff = affineFromTriangle(
    [s0.x, s0.y],
    [s1.x, s1.y],
    [s2.x, s2.y],
    [d0.x, d0.y],
    [d1.x, d1.y],
    [d2.x, d2.y]
  );
  if (!aff) return;

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(d0.x, d0.y);
  ctx.lineTo(d1.x, d1.y);
  ctx.lineTo(d2.x, d2.y);
  ctx.closePath();
  ctx.clip();

  // x' = a*sx + b*sy + c, y' = d*sx + e*sy + f  →  Canvas setTransform(a, d, b, e, c, f)
  ctx.setTransform(aff.a, aff.d, aff.b, aff.e, aff.c, aff.f);
  ctx.drawImage(img, 0, 0, imgW, imgH);
  ctx.restore();
}

function drawGridMesh(
  ctx: CanvasRenderingContext2D,
  img: CanvasImageSource,
  imgW: number,
  imgH: number,
  srcPx: Point2[][],
  dstPx: Point2[][]
): void {
  const g = GRID;
  for (let j = 0; j < g; j++) {
    for (let i = 0; i < g; i++) {
      const s00 = srcPx[j][i];
      const s10 = srcPx[j][i + 1];
      const s01 = srcPx[j + 1][i];
      const s11 = srcPx[j + 1][i + 1];
      const d00 = dstPx[j][i];
      const d10 = dstPx[j][i + 1];
      const d01 = dstPx[j + 1][i];
      const d11 = dstPx[j + 1][i + 1];

      drawTriangle(ctx, img, imgW, imgH, s00, s10, s01, d00, d10, d01);
      drawTriangle(ctx, img, imgW, imgH, s10, s11, s01, d10, d11, d01);
    }
  }
}

/** Static billboard overlay when TPS fails or pose invalid — same spirit as legacy overlay. */
export function drawStaticGarmentBillboard(
  ctx: CanvasRenderingContext2D,
  img: CanvasImageSource,
  a: BodyAnchors,
  canvasW: number,
  canvasH: number,
  cat: ArOverlayCategory
): void {
  const ls = a.shoulderLeft;
  const rs = a.shoulderRight;
  const lh = a.hipLeft;
  const rh = a.hipRight;
  const shoulderW = Math.max(Math.abs(rs.x - ls.x) * canvasW, canvasW * 0.08);
  const topY = Math.min(ls.y, rs.y) * canvasH - canvasH * 0.04;
  let x: number;
  let y: number;
  let width: number;
  let height: number;

  if (cat === 'pants' && lh && rh) {
    const hipW = Math.max(Math.abs(rh.x - lh.x) * canvasW, canvasW * 0.1);
    y = Math.min(lh.y, rh.y) * canvasH - canvasH * 0.02;
    width = hipW * 1.75;
    height = Math.min(canvasH - y, canvasH * 0.55);
    x = ((lh.x + rh.x) / 2) * canvasW - width / 2;
  } else if (cat === 'dress') {
    width = shoulderW * 1.55;
    height = Math.min(canvasH - topY, canvasH * 0.92);
    x = ((ls.x + rs.x) / 2) * canvasW - width / 2;
    y = topY;
  } else {
    const bottomY =
      lh && rh ? Math.max(lh.y, rh.y) * canvasH + canvasH * 0.04 : topY + shoulderW * 1.2;
    const topMult = cat === 'outerwear' ? 1.5 : 1.38;
    const heightMult = cat === 'outerwear' ? 1.22 : 1.18;
    width = shoulderW * topMult;
    height = Math.max((bottomY - topY) * heightMult, shoulderW * 0.85);
    x = ((ls.x + rs.x) / 2) * canvasW - width / 2;
    y = topY;
  }

  width = Math.min(width, canvasW * 1.05);
  height = Math.min(height, canvasH * 0.98);
  x = Math.max(0, Math.min(x, canvasW - width));
  y = Math.max(0, Math.min(y, canvasH - height));

  ctx.save();
  ctx.drawImage(img, x, y, width, height);
  ctx.restore();
}

/**
 * @param poseValid — whether current frame has confident tracking
 * @param anchors — temporally smoothed body anchors (or null before first lock)
 */
export function drawRealtimeWarpedGarment(
  ctx: CanvasRenderingContext2D,
  poseValid: boolean,
  anchors: BodyAnchors | null,
  img: CanvasImageSource,
  imgW: number,
  imgH: number,
  canvasW: number,
  canvasH: number,
  cat: ArOverlayCategory
): void {
  if (!anchors) return;

  if (!poseValid) {
    ctx.save();
    ctx.globalAlpha = 0.88;
    drawStaticGarmentBillboard(ctx, img, anchors, canvasW, canvasH, cat);
    punchFaceSafeBand(ctx, anchors.noseY, canvasW, canvasH);
    punchArmOcclusion(ctx, anchors, canvasW, canvasH);
    ctx.restore();
    return;
  }

  const destControl = anchorsToCanvasPoints(anchors);
  const grid = buildWarpGrid(imgW, imgH, canvasW, canvasH, cat, destControl);

  ctx.save();
  ctx.globalAlpha = 0.9;

  if (!grid) {
    drawStaticGarmentBillboard(ctx, img, anchors, canvasW, canvasH, cat);
  } else {
    drawGridMesh(ctx, img, imgW, imgH, grid.srcPx, grid.dstPx);
  }

  punchFaceSafeBand(ctx, anchors.noseY, canvasW, canvasH);
  punchArmOcclusion(ctx, anchors, canvasW, canvasH);

  ctx.restore();
}
