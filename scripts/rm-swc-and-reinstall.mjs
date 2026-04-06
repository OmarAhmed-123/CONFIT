/**
 * Windows/npm sometimes leaves @swc native binaries half-deleted (ENOTEMPTY).
 * Removes root node_modules/@swc and runs npm install to restore bindings for Vite/SWC.
 */
import { rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const swcDir = join(root, "node_modules", "@swc");
if (existsSync(swcDir)) {
  rmSync(swcDir, { recursive: true, force: true });
  console.log("Removed:", swcDir);
} else {
  console.log("No node_modules/@swc — running npm install anyway.");
}
execSync("npm install", { cwd: root, stdio: "inherit", env: process.env });
