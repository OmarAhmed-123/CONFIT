import type { FastifyInstance } from "fastify";
import { z } from "zod";

const DEFAULT_TIMEOUT_MS = 10_000;

type RequestInitWithTimeout = RequestInit & { timeoutMs?: number };

class HttpError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = "HttpError";
  }
}

async function fetchJson<T>(
  url: string,
  init?: RequestInitWithTimeout
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), init?.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      ...init,
      signal: controller.signal
    });
    if (!res.ok) {
      const text = await res.text();
      throw new HttpError("Upstream request failed", res.status, text);
    }
    return (await res.json()) as T;
  } catch (error) {
    if (error instanceof HttpError) throw error;
    throw new HttpError("Upstream request failed", 502, String(error));
  } finally {
    clearTimeout(timeout);
  }
}

function buildQrImageUrl(data: string, size: number) {
  const encodedData = encodeURIComponent(data);
  return `https://api.qrserver.com/v1/create-qr-code/?data=${encodedData}&size=${size}x${size}&format=png`;
}

const NameQuerySchema = z.object({
  name: z.string().trim().min(1).max(80)
});

const RandomUserQuerySchema = z.object({
  results: z.coerce.number().int().min(1).max(25).default(1)
});

const DictionaryQuerySchema = z.object({
  word: z.string().trim().min(1).max(80)
});

const QrCreateQuerySchema = z.object({
  data: z.string().trim().min(1).max(900),
  size: z.coerce.number().int().min(64).max(1000).default(256)
});

const QrReadBodySchema = z.object({
  fileUrl: z.string().url().max(2000)
});

const EvStationsQuerySchema = z.object({
  lat: z.coerce.number().min(-90).max(90),
  lng: z.coerce.number().min(-180).max(180),
  distanceKm: z.coerce.number().min(1).max(100).default(10),
  maxResults: z.coerce.number().int().min(1).max(50).default(20)
});

const ChatBodySchema = z.object({
  message: z.string().trim().min(1).max(4000),
  provider: z.enum(["groq", "huggingface"]).default("groq"),
  model: z.string().trim().min(1).max(120).optional(),
  systemPrompt: z.string().trim().min(1).max(1000).optional()
});

const GroqChatResponseSchema = z.object({
  choices: z.array(
    z.object({
      message: z.object({
        content: z.string().nullable().optional()
      })
    })
  ),
  usage: z
    .object({
      prompt_tokens: z.number().optional(),
      completion_tokens: z.number().optional(),
      total_tokens: z.number().optional()
    })
    .optional()
});

export async function registerIntegrationsRoutes(app: FastifyInstance) {
  const { env } = app.ctx;

  app.get("/api/integrations/identity/insights", async (req, reply) => {
    const { name } = NameQuerySchema.parse(req.query ?? {});

    const [agify, genderize, nationalize] = await Promise.allSettled([
      fetchJson<{ age: number | null; count: number; name: string }>(
        `https://api.agify.io/?name=${encodeURIComponent(name)}`
      ),
      fetchJson<{ gender: string | null; probability: number; count: number; name: string }>(
        `https://api.genderize.io/?name=${encodeURIComponent(name)}`
      ),
      fetchJson<{ country: Array<{ country_id: string; probability: number }>; name: string }>(
        `https://api.nationalize.io/?name=${encodeURIComponent(name)}`
      )
    ]);

    return {
      name,
      age: agify.status === "fulfilled" ? agify.value : null,
      gender: genderize.status === "fulfilled" ? genderize.value : null,
      nationality: nationalize.status === "fulfilled" ? nationalize.value : null
    };
  });

  app.get("/api/integrations/identity/random-user", async (req) => {
    const { results } = RandomUserQuerySchema.parse(req.query ?? {});
    return await fetchJson(`https://randomuser.me/api/?results=${results}`);
  });

  app.get("/api/integrations/utilities/ip", async () => {
    return await fetchJson<{ ip: string }>("https://api.ipify.org/?format=json");
  });

  app.get("/api/integrations/utilities/dictionary", async (req, reply) => {
    const { word } = DictionaryQuerySchema.parse(req.query ?? {});
    try {
      return await fetchJson(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(word)}`);
    } catch (error) {
      if (error instanceof HttpError && error.statusCode === 404) {
        return reply.code(404).send({ error: "WORD_NOT_FOUND" });
      }
      throw error;
    }
  });

  app.get("/api/integrations/utilities/uuid", async () => {
    return await fetchJson<{ uuid: string }>("https://httpbin.org/uuid");
  });

  app.get("/api/integrations/utilities/qr/create", async (req) => {
    const { data, size } = QrCreateQuerySchema.parse(req.query ?? {});
    return {
      imageUrl: buildQrImageUrl(data, size),
      metadata: { size, format: "png" }
    };
  });

  app.post("/api/integrations/utilities/qr/read", async (req) => {
    const { fileUrl } = QrReadBodySchema.parse(req.body ?? {});
    const encodedFileUrl = encodeURIComponent(fileUrl);
    return await fetchJson(
      `https://api.qrserver.com/v1/read-qr-code/?fileurl=${encodedFileUrl}&outputformat=json`
    );
  });

  app.get("/api/integrations/transport/ev-stations", async (req) => {
    const { lat, lng, distanceKm, maxResults } = EvStationsQuerySchema.parse(req.query ?? {});
    const url =
      `https://api.openchargemap.io/v3/poi/?output=json` +
      `&latitude=${lat}&longitude=${lng}&distance=${distanceKm}&distanceunit=KM` +
      `&maxresults=${maxResults}&compact=true&verbose=false`;
    return await fetchJson(url);
  });

  app.get("/api/integrations/ai/transformers-js/info", async () => {
    return {
      package: "@huggingface/transformers",
      runtime: "browser (WASM/WebGPU)",
      authRequired: false,
      docs: "https://huggingface.co/docs/transformers.js/index"
    };
  });

  app.post("/api/integrations/ai/chat", async (req, reply) => {
    const body = ChatBodySchema.parse(req.body ?? {});
    const messages = [
      ...(body.systemPrompt ? [{ role: "system", content: body.systemPrompt }] : []),
      { role: "user", content: body.message }
    ];

    if (body.provider === "groq") {
      if (!env.GROQ_API_KEY) {
        return reply.code(503).send({ error: "GROQ_NOT_CONFIGURED" });
      }
      const response = await fetchJson<z.infer<typeof GroqChatResponseSchema>>(
        "https://api.groq.com/openai/v1/chat/completions",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${env.GROQ_API_KEY}`
          },
          body: JSON.stringify({
            model: body.model ?? "llama-3.1-8b-instant",
            messages
          })
        }
      );

      const parsed = GroqChatResponseSchema.parse(response);
      return {
        provider: "groq",
        model: body.model ?? "llama-3.1-8b-instant",
        text: parsed.choices[0]?.message?.content ?? "",
        usage: parsed.usage ?? null
      };
    }

    if (!env.HUGGINGFACE_API_KEY) {
      return reply.code(503).send({ error: "HUGGINGFACE_NOT_CONFIGURED" });
    }

    const response = await fetchJson<z.infer<typeof GroqChatResponseSchema>>(
      "https://router.huggingface.co/v1/chat/completions",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${env.HUGGINGFACE_API_KEY}`
        },
        body: JSON.stringify({
          model: body.model ?? env.HUGGINGFACE_DEFAULT_MODEL ?? "meta-llama/Llama-3.1-8B-Instruct",
          messages
        })
      }
    );

    const parsed = GroqChatResponseSchema.parse(response);
    return {
      provider: "huggingface",
      model: body.model ?? env.HUGGINGFACE_DEFAULT_MODEL ?? "meta-llama/Llama-3.1-8B-Instruct",
      text: parsed.choices[0]?.message?.content ?? "",
      usage: parsed.usage ?? null
    };
  });
}
