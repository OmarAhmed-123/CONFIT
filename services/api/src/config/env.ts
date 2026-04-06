import { z } from "zod";
import { generateKeyPairSync, randomBytes } from "node:crypto";

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().positive().default(4000),
  // Vite frontend (main CONFIT app) - OAuth redirects here after login
  PUBLIC_APP_ORIGIN: z.string().url().default("http://localhost:8080"),
  REDIS_URL: z.string().default("redis://localhost:6379"),
  COOKIE_SECRET: z.string().min(32).optional(),

  JWT_ISSUER: z.string().default("confit"),
  JWT_AUDIENCE: z.string().default("confit-web"),
  JWT_PRIVATE_KEY_PEM: z.string().min(32).optional(),
  JWT_PUBLIC_KEY_PEM: z.string().min(32).optional(),

  OAUTH_GOOGLE_CLIENT_ID: z.string().optional(),
  OAUTH_GOOGLE_CLIENT_SECRET: z.string().optional(),
  OAUTH_GOOGLE_REDIRECT_URI: z.string().url().optional(),

  OAUTH_FACEBOOK_CLIENT_ID: z.string().optional(),
  OAUTH_FACEBOOK_CLIENT_SECRET: z.string().optional(),
  OAUTH_FACEBOOK_REDIRECT_URI: z.string().url().optional(),

  OAUTH_INSTAGRAM_CLIENT_ID: z.string().optional(),
  OAUTH_INSTAGRAM_CLIENT_SECRET: z.string().optional(),
  OAUTH_INSTAGRAM_REDIRECT_URI: z.string().url().optional(),

  OAUTH_X_CLIENT_ID: z.string().optional(),
  OAUTH_X_CLIENT_SECRET: z.string().optional(),
  OAUTH_X_REDIRECT_URI: z.string().url().optional(),

  OAUTH_TIKTOK_CLIENT_ID: z.string().optional(),
  OAUTH_TIKTOK_CLIENT_SECRET: z.string().optional(),
  OAUTH_TIKTOK_REDIRECT_URI: z.string().url().optional(),

  STRIPE_SECRET_KEY: z.string().optional(),
  STRIPE_PUBLISHABLE_KEY: z.string().optional(),
  STRIPE_WEBHOOK_SECRET: z.string().optional(),
  GROQ_API_KEY: z.string().optional(),
  HUGGINGFACE_API_KEY: z.string().optional(),
  HUGGINGFACE_DEFAULT_MODEL: z.string().default("meta-llama/Llama-3.1-8B-Instruct"),
  // When true and provider env is missing, dev login still works (mock profile).
  // Set true explicitly for local dev without real OAuth credentials.
  // Production ALWAYS uses real OAuth (forced false in production).
  DEV_OAUTH_MOCK_ENABLED: z.coerce.boolean().default(false)
});

export type Env = z.infer<typeof envSchema>;

export function loadEnv(processEnv: NodeJS.ProcessEnv): Env {
  const parsed = envSchema.safeParse(processEnv);
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("\n");
    throw new Error(`Invalid environment:\n${msg}`);
  }

  const env = parsed.data;
  if (env.NODE_ENV === "production") {
    env.DEV_OAUTH_MOCK_ENABLED = false;
    if (!env.COOKIE_SECRET) throw new Error("Invalid environment:\nCOOKIE_SECRET: Required");
    if (!env.JWT_PRIVATE_KEY_PEM) throw new Error("Invalid environment:\nJWT_PRIVATE_KEY_PEM: Required");
    if (!env.JWT_PUBLIC_KEY_PEM) throw new Error("Invalid environment:\nJWT_PUBLIC_KEY_PEM: Required");
    return env as Required<Env>;
  }

  if (!env.COOKIE_SECRET) {
    env.COOKIE_SECRET = randomBytes(32).toString("hex");
  }
  if (!env.JWT_PRIVATE_KEY_PEM || !env.JWT_PUBLIC_KEY_PEM) {
    const kp = generateKeyPairSync("rsa", { modulusLength: 2048 });
    env.JWT_PRIVATE_KEY_PEM = kp.privateKey.export({ type: "pkcs8", format: "pem" }).toString();
    env.JWT_PUBLIC_KEY_PEM = kp.publicKey.export({ type: "spki", format: "pem" }).toString();
  }
  return env as Required<Env>;
}

