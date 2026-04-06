/**
 * Run Alembic migrations from repo root without requiring `alembic` on PATH.
 * Uses backend/.venv or backend/venv when present (Windows + Unix).
 *
 * Usage: node scripts/run-backend-migrations.mjs
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backend = path.resolve(__dirname, "..", "backend");

const candidates = [
  path.join(backend, ".venv", "Scripts", "python.exe"),
  path.join(backend, "venv", "Scripts", "python.exe"),
  path.join(backend, ".venv", "bin", "python"),
  path.join(backend, "venv", "bin", "python"),
  path.join(backend, ".venv", "bin", "python3"),
  path.join(backend, "venv", "bin", "python3"),
];

let python = process.env.PYTHON ?? "python";
for (const c of candidates) {
  if (existsSync(c)) {
    python = c;
    break;
  }
}

const r = spawnSync(python, ["-m", "pip", "show", "alembic"], {
  cwd: backend,
  encoding: "utf8",
  shell: false,
});
if (r.status !== 0) {
  console.error(
    "Alembic is not installed for this Python. From the backend folder run:\n" +
      "  pip install -r requirements.txt\n" +
      "or create a venv first:\n" +
      "  python -m venv .venv\n" +
      "  .\\.venv\\Scripts\\activate   (PowerShell)\n" +
      "  pip install -r requirements.txt",
  );
  process.exit(1);
}

const migrate = spawnSync(python, ["-m", "alembic", "upgrade", "head"], {
  cwd: backend,
  stdio: "inherit",
  shell: false,
});
process.exit(migrate.status ?? 1);
