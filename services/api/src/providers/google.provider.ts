import { createHash } from "node:crypto";
import { jwtVerify, createRemoteJWKSet } from "jose";
import { request } from "undici";
import type { Env } from "../config/env.js";
import type { OAuthProvider, BuildAuthorizeUrlInput, ExchangeInput } from "./provider.js";
import type { NormalizedProfile } from "../modules/auth/types.js";

function base64Url(input: Buffer) {
  return input
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function pkceChallenge(verifier: string) {
  const hash = createHash("sha256").update(verifier).digest();
  return base64Url(hash);
}

export class GoogleProvider implements OAuthProvider {
  id = "google" as const;
  constructor(private env: Env) {}

  buildAuthorizeUrl(input: BuildAuthorizeUrlInput): string {
    if (!this.env.OAUTH_GOOGLE_CLIENT_ID || !this.env.OAUTH_GOOGLE_REDIRECT_URI) {
      throw new Error("Google OAuth not configured");
    }
    const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
    url.searchParams.set("client_id", this.env.OAUTH_GOOGLE_CLIENT_ID);
    url.searchParams.set("redirect_uri", this.env.OAUTH_GOOGLE_REDIRECT_URI);
    url.searchParams.set("response_type", "code");
    url.searchParams.set("scope", "openid email profile");
    url.searchParams.set("state", input.state);
    url.searchParams.set("nonce", input.nonce);
    url.searchParams.set("code_challenge", pkceChallenge(input.codeVerifier));
    url.searchParams.set("code_challenge_method", "S256");
    url.searchParams.set("access_type", "offline");
    // Forces Google account chooser so users can pick among signed-in accounts.
    url.searchParams.set("prompt", "select_account consent");
    return url.toString();
  }

  async exchangeAndNormalize(input: ExchangeInput): Promise<NormalizedProfile> {
    if (!this.env.OAUTH_GOOGLE_CLIENT_ID || !this.env.OAUTH_GOOGLE_CLIENT_SECRET || !this.env.OAUTH_GOOGLE_REDIRECT_URI) {
      throw new Error("Google OAuth not configured");
    }

    const tokenResp = await request("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: this.env.OAUTH_GOOGLE_CLIENT_ID,
        client_secret: this.env.OAUTH_GOOGLE_CLIENT_SECRET,
        redirect_uri: this.env.OAUTH_GOOGLE_REDIRECT_URI,
        code: input.code,
        code_verifier: input.codeVerifier
      }).toString()
    });

    if (tokenResp.statusCode < 200 || tokenResp.statusCode >= 300) {
      const body = await tokenResp.body.text();
      throw new Error(`TOKEN_EXCHANGE_FAILED ${tokenResp.statusCode} ${body}`);
    }

    const tokenJson = (await tokenResp.body.json()) as {
      access_token: string;
      id_token: string;
      expires_in: number;
      token_type: string;
      scope?: string;
    };

    const jwks = createRemoteJWKSet(new URL("https://www.googleapis.com/oauth2/v3/certs"));
    const { payload } = await jwtVerify(tokenJson.id_token, jwks, {
      issuer: ["https://accounts.google.com", "accounts.google.com"],
      audience: this.env.OAUTH_GOOGLE_CLIENT_ID
    });
    if (payload.nonce !== input.nonce) throw new Error("NONCE_MISMATCH");

    const providerAccountId = payload.sub;
    if (typeof providerAccountId !== "string") throw new Error("INVALID_SUB");

    return {
      provider: "google",
      providerAccountId,
      email: typeof payload.email === "string" ? payload.email : undefined,
      emailVerified: typeof payload.email_verified === "boolean" ? payload.email_verified : undefined,
      name: typeof payload.name === "string" ? payload.name : undefined,
      pictureUrl: typeof payload.picture === "string" ? payload.picture : undefined
    };
  }
}

