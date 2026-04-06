/**
 * Smoke checks against running local services (start API, Next, Vite, Python backend manually).
 * Usage: node scripts/e2e-smoke.mjs
 * Env: E2E_PYTHON_API (default http://localhost:8001), E2E_FASTIFY_API (http://localhost:4000), E2E_NEXT (http://localhost:3000)
 */

const PY = process.env.E2E_PYTHON_API ?? "http://localhost:8001";
const FASTIFY = process.env.E2E_FASTIFY_API ?? "http://localhost:4000";
const NEXT = process.env.E2E_NEXT ?? "http://localhost:3000";

async function getJson(url) {
  const r = await fetch(url, { redirect: "manual" });
  const text = await r.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { ok: r.ok, status: r.status, body };
}

function fail(msg) {
  console.error("E2E smoke FAILED:", msg);
  process.exit(1);
}

async function main() {
  console.log("E2E smoke: Python catalog", PY);

  const list = await getJson(`${PY}/api/products?limit=5`);
  if (!list.ok || !Array.isArray(list.body)) {
    fail(`GET /api/products expected 200 JSON array, got ${list.status} ${typeof list.body}`);
  }
  if (list.body.length < 1) {
    fail("Expected at least one product from catalog");
  }
  const id = list.body[0].id;
  const detail = await getJson(`${PY}/api/products/${encodeURIComponent(id)}`);
  if (!detail.ok || !detail.body || detail.body.id !== id) {
    fail(`GET /api/products/:id failed for ${id}: ${detail.status}`);
  }
  console.log("  OK catalog + product detail:", id);

  console.log("E2E smoke: Fastify auth", FASTIFY);
  const me = await getJson(`${FASTIFY}/api/auth/me`);
  if (me.status !== 401) {
    fail(`Fastify /api/auth/me expected 401 without cookies, got ${me.status}`);
  }
  console.log("  OK /api/auth/me unauthenticated");

  console.log("E2E smoke: Next /me", NEXT);
  const nme = await getJson(`${NEXT}/me`);
  if (nme.status !== 401 && nme.status !== 302) {
    console.warn("  WARN: Next /me expected 401 or 302, got", nme.status);
  } else {
    console.log("  OK Next /me without session");
  }

  console.log("E2E smoke: passed (start full OAuth + cart flows in browser manually).");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
