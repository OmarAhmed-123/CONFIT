/**
 * Affine map from garment texture space (sx, sy) to canvas (dx, dy):
 * dx = a*sx + b*sy + c, dy = d*sx + e*sy + f
 * Canvas setTransform(a, d, b, e, c, f) uses x' = a*x + c*y + e, y' = b*x + d*y + f
 * so we pass (a, b, d, e, c, f) as (a, b, c, d, e, f) in canvas terms... see drawWarpedGarment.
 */

export type Affine2D = { a: number; b: number; c: number; d: number; e: number; f: number };

/** Solve 6x6 linear system via Gaussian elimination (small, stable enough for triangles). */
function solve6x6(m: number[][], rhs: number[]): number[] | null {
  const n = 6;
  const aug = m.map((row, i) => [...row, rhs[i]]);

  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) {
      if (Math.abs(aug[r][col]) > Math.abs(aug[pivot][col])) pivot = r;
    }
    if (Math.abs(aug[pivot][col]) < 1e-12) return null;
    if (pivot !== col) [aug[col], aug[pivot]] = [aug[pivot], aug[col]];

    const div = aug[col][col];
    for (let j = col; j <= n; j++) aug[col][j] /= div;

    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = aug[r][col];
      if (Math.abs(f) < 1e-15) continue;
      for (let j = col; j <= n; j++) aug[r][j] -= f * aug[col][j];
    }
  }

  return aug.map((row) => row[n]);
}

/**
 * Affine transform mapping three source points to three destination points
 * (texture / normalized space -> canvas pixels).
 */
export function affineFromTriangle(
  s0: [number, number],
  s1: [number, number],
  s2: [number, number],
  d0: [number, number],
  d1: [number, number],
  d2: [number, number]
): Affine2D | null {
  // dx = a*sx + b*sy + c
  // dy = d*sx + e*sy + f
  const m = [
    [s0[0], s0[1], 1, 0, 0, 0],
    [s1[0], s1[1], 1, 0, 0, 0],
    [s2[0], s2[1], 1, 0, 0, 0],
    [0, 0, 0, s0[0], s0[1], 1],
    [0, 0, 0, s1[0], s1[1], 1],
    [0, 0, 0, s2[0], s2[1], 1],
  ];
  const rhs = [d0[0], d1[0], d2[0], d0[1], d1[1], d2[1]];
  const sol = solve6x6(m, rhs);
  if (!sol) return null;
  return { a: sol[0], b: sol[1], c: sol[2], d: sol[3], e: sol[4], f: sol[5] };
}
