/**
 * CONFIT MCP Gateway — Cloudflare Workers + Agents MCP.
 * Exposes tools that map to the CONFIT FastAPI surface (main.py routers + /style-dna, /planner, /sustainability).
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { McpAgent } from "agents/mcp";
import { z } from "zod";

const MAX_BODY_CHARS = 512_000;

function normalizeBase(url: string): string {
  return url.replace(/\/+$/, "");
}

/** Paths allowed to proxy (matches backend mounted in main.py + top-level api modules). */
function isAllowedPath(path: string): boolean {
  if (!path.startsWith("/") || path.includes("..")) return false;
  return (
    /^\/api(\/|$)/.test(path) ||
    /^\/style-dna(\/|$)/.test(path) ||
    /^\/planner(\/|$)/.test(path) ||
    /^\/sustainability(\/|$)/.test(path)
  );
}

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"] as const;

const CAPABILITIES_TEXT = `CONFIT backend domains (FastAPI main.py + modules):

Core API prefix /api/:
- /api/health — health check
- /api/tryon — alias for virtual try-on POST body
- /api/virtual-tryon — try-on pipeline (Model Control Pipeline / try-on)
- /api/stylist — virtual stylist + /api/stylist (AI stylist chat)
- /api/rotation — 360° product rotation
- /api/auth — JWT / sessions
- /api/products — catalog
- /api/orders — orders
- /api/commerce — cart / commerce
- /api/fashion-os — Fashion OS
- /api/newsletter — newsletter & contact (under /api)
- /api/wardrobe — wardrobe
- /api/brands — brands
- /api/stores — stores
- /api/promo — promo codes
- /api/visual-search — visual search
- /api/wishlist — wishlist
- /api/outfits — outfit builder
- /api/payments — Stripe payments
- /api/analytics — analytics
- /api/digital-twin — digital twin
- /api/social — social
- /api/resale — resale
- /api/omni — omni-channel
- /api/challenges — challenges
- /api/chatbot — chatbot
- /api/profile — profile
- /api/onboarding — onboarding
- /api/signals — behavior signals
- /api/privacy — privacy
- /api/identity — identity intelligence
- /api/outfit-ratings — outfit ratings
- /api/influencers — influencer marketplace
- /api/security — PentAGI-backed scans (scan, status, report, targets/discover, health)
- /api/growth — growth / referrals

Top-level (no /api prefix):
- /style-dna — Style DNA API
- /planner — closet planner
- /sustainability — sustainability ratings

Use confit_backend_request for any of these paths. For discovery of exact routes and schemas, use confit_openapi (GET /openapi.json).
WebSocket endpoints cannot be used through this HTTP proxy tool.
`;

export class ConfitMCP extends McpAgent<Env> {
  server = new McpServer({
    name: "confit-gateway",
    version: "1.0.0",
  });

  async init() {
    this.server.tool("confit_capabilities", {}, async () => ({
      content: [{ type: "text", text: CAPABILITIES_TEXT }],
    }));

    this.server.tool(
      "confit_health",
      {},
      async () => {
        const base = this.env.CONFIT_API_BASE_URL;
        if (!base) {
          return {
            content: [
              {
                type: "text",
                text: "CONFIT_API_BASE_URL is not set on the Worker. Set it in wrangler vars or .dev.vars.",
              },
            ],
          };
        }
        const url = `${normalizeBase(base)}/api/health`;
        const res = await fetch(url, { headers: { Accept: "application/json" } });
        const text = await res.text();
        return {
          content: [{ type: "text", text: `HTTP ${res.status}\n${text.slice(0, MAX_BODY_CHARS)}` }],
        };
      },
    );

    this.server.tool(
      "confit_openapi",
      {
        stripLargeSchemas: z
          .boolean()
          .optional()
          .describe("If true, return only paths + methods (smaller payload)."),
      },
      async ({ stripLargeSchemas }) => {
        const base = this.env.CONFIT_API_BASE_URL;
        if (!base) {
          return {
            content: [
              {
                type: "text",
                text: "CONFIT_API_BASE_URL is not set on the Worker.",
              },
            ],
          };
        }
        const url = `${normalizeBase(base)}/openapi.json`;
        const res = await fetch(url, { headers: { Accept: "application/json" } });
        if (!res.ok) {
          return {
            content: [{ type: "text", text: `HTTP ${res.status} fetching openapi.json` }],
          };
        }
        const data = (await res.json()) as {
          paths?: Record<string, unknown>;
          info?: unknown;
        };
        if (stripLargeSchemas) {
          const slim = {
            info: data.info,
            paths: data.paths
              ? Object.fromEntries(
                  Object.entries(data.paths).map(([p, methods]) => [
                    p,
                    methods && typeof methods === "object"
                      ? Object.keys(methods as object)
                      : methods,
                  ]),
                )
              : {},
          };
          return {
            content: [{ type: "text", text: JSON.stringify(slim, null, 2).slice(0, MAX_BODY_CHARS) }],
          };
        }
        const full = JSON.stringify(data, null, 2);
        return {
          content: [{ type: "text", text: full.slice(0, MAX_BODY_CHARS) }],
        };
      },
    );

    this.server.tool(
      "confit_backend_request",
      {
        method: z.enum(METHODS).describe("HTTP method"),
        path: z
          .string()
          .describe(
            "Path starting with /api/, /style-dna/, /planner/, or /sustainability/ — e.g. /api/products or /api/security/health",
          ),
        query: z
          .record(z.string(), z.string())
          .optional()
          .describe("Optional query string parameters"),
        body: z
          .union([z.string(), z.record(z.string(), z.unknown())])
          .optional()
          .describe("JSON body for POST/PUT/PATCH (object or JSON string)"),
        authorization: z
          .string()
          .optional()
          .describe("Optional Bearer token (with or without 'Bearer ' prefix)"),
      },
      async ({ method, path, query, body, authorization }) => {
        const base = this.env.CONFIT_API_BASE_URL;
        if (!base) {
          return {
            content: [
              {
                type: "text",
                text: "CONFIT_API_BASE_URL is not set. Configure the Worker secret/var pointing to your CONFIT FastAPI base URL.",
              },
            ],
          };
        }
        if (!isAllowedPath(path)) {
          return {
            content: [
              {
                type: "text",
                text: `Rejected path: only /api/*, /style-dna/*, /planner/*, /sustainability/* are allowed. Got: ${path}`,
              },
            ],
          };
        }

        const url = new URL(path, `${normalizeBase(base)}/`);
        if (query) {
          for (const [k, v] of Object.entries(query)) {
            url.searchParams.set(k, String(v));
          }
        }

        const headers: Record<string, string> = {
          Accept: "application/json, text/plain, */*",
        };
        if (authorization) {
          headers.Authorization = authorization.startsWith("Bearer ")
            ? authorization
            : `Bearer ${authorization}`;
        }

        const init: RequestInit = { method, headers };

        if (body !== undefined && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
          headers["Content-Type"] = "application/json";
          init.body = typeof body === "string" ? body : JSON.stringify(body);
        }

        const res = await fetch(url.toString(), init);
        const text = await res.text();
        const truncated = text.length > MAX_BODY_CHARS ? text.slice(0, MAX_BODY_CHARS) + "\n…[truncated]" : text;
        return {
          content: [
            {
              type: "text",
              text: `Request: ${method} ${url.pathname}${url.search}\nHTTP ${res.status} ${res.statusText}\n\n${truncated}`,
            },
          ],
        };
      },
    );
  }
}

export default {
  fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const url = new URL(request.url);
    if (url.pathname === "/mcp") {
      return ConfitMCP.serve("/mcp").fetch(request, env, ctx);
    }
    if (url.pathname === "/" || url.pathname === "") {
      return new Response(
        JSON.stringify({
          service: "confit-mcp-gateway",
          mcp: "/mcp",
          docs: "Set CONFIT_API_BASE_URL to your FastAPI base (e.g. http://127.0.0.1:8000).",
        }),
        { headers: { "content-type": "application/json; charset=utf-8" } },
      );
    }
    return new Response("Not found", { status: 404 });
  },
};
