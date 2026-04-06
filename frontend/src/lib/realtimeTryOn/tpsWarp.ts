/**
 * 2D thin-plate spline (TPS) for smooth mesh warping.
 * φ(r) = r² log(r² + ε) — classic TPS basis in 2D.
 */

const EPS = 1e-8;

function phi(r2: number): number {
  const r2c = Math.max(r2, EPS);
  return r2c * Math.log(r2c + EPS);
}

export type Point2 = { x: number; y: number };

function buildSystem(control: Point2[]): { mat: number[][]; n: number } | null {
  const k = control.length;
  if (k < 3) return null;
  const dim = k + 3;
  const mat: number[][] = Array(dim)
    .fill(null)
    .map(() => Array(dim + 1).fill(0));

  for (let i = 0; i < k; i++) {
    for (let j = 0; j < k; j++) {
      const dx = control[i].x - control[j].x;
      const dy = control[i].y - control[j].y;
      mat[i][j] = phi(dx * dx + dy * dy);
    }
    mat[i][k] = 1;
    mat[i][k + 1] = control[i].x;
    mat[i][k + 2] = control[i].y;
  }

  for (let j = 0; j < k; j++) {
    mat[k][j] = 1;
    mat[k + 1][j] = control[j].x;
    mat[k + 2][j] = control[j].y;
  }

  return { mat, n: dim };
}

/** Gaussian elimination with partial pivoting; aug is n x (n+1). */
function solveLinear(aug: number[][], n: number): number[] | null {
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

export type TpsCoeffs = {
  control: Point2[];
  w: number[];
  a0: number;
  ax: number;
  ay: number;
};

export function fitTPS1D(control: Point2[], values: number[]): TpsCoeffs | null {
  const sys = buildSystem(control);
  if (!sys) return null;
  const { mat, n } = sys;
  const k = control.length;
  const rhs = new Array(n).fill(0);
  for (let i = 0; i < k; i++) rhs[i] = values[i];

  for (let i = 0; i < n; i++) mat[i][n] = rhs[i];

  const sol = solveLinear(mat, n);
  if (!sol) return null;

  return {
    control,
    w: sol.slice(0, k),
    a0: sol[k],
    ax: sol[k + 1],
    ay: sol[k + 2],
  };
}

export function evaluateTPS1D(c: TpsCoeffs, p: Point2): number {
  let s = c.a0 + c.ax * p.x + c.ay * p.y;
  for (let i = 0; i < c.control.length; i++) {
    const dx = p.x - c.control[i].x;
    const dy = p.y - c.control[i].y;
    s += c.w[i] * phi(dx * dx + dy * dy);
  }
  return s;
}

/** Fit two TPS surfaces for x/y displacement from normalized garment coords to canvas. */
export function fitDisplacementTPS(
  source: Point2[],
  dest: Point2[]
): { tpsX: TpsCoeffs; tpsY: TpsCoeffs } | null {
  if (source.length !== dest.length || source.length < 3) return null;
  const vx = dest.map((d, i) => d.x - source[i].x);
  const vy = dest.map((d, i) => d.y - source[i].y);
  const tpsX = fitTPS1D(source, vx);
  const tpsY = fitTPS1D(source, vy);
  if (!tpsX || !tpsY) return null;
  return { tpsX, tpsY };
}

export function evaluateTPS2D(
  tpsX: TpsCoeffs,
  tpsY: TpsCoeffs,
  src: Point2
): Point2 {
  const dx = evaluateTPS1D(tpsX, src);
  const dy = evaluateTPS1D(tpsY, src);
  return { x: src.x + dx, y: src.y + dy };
}
