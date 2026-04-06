import { request } from "undici";
import { createHash } from "node:crypto";
import type { OAuthProvider, BuildAuthorizeUrlInput, ExchangeInput } from "./provider.js";
import type { NormalizedProfile, OAuthProviderId } from "../modules/auth/types.js";

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

export type OAuth2BasicConfig = {
  id: OAuthProviderId;
  authorizeUrl: string;
  tokenUrl: string;
  userInfoUrl: string;
  clientId?: string;
  clientSecret?: string;
  redirectUri?: string;
  scope: string;
  mapProfile: (raw: any) => NormalizedProfile;
};

export class OAuth2BasicProvider implements OAuthProvider {
  id: OAuthProviderId;
  constructor(private cfg: OAuth2BasicConfig) {
    this.id = cfg.id;
  }

  buildAuthorizeUrl(input: BuildAuthorizeUrlInput): string {
    if (!this.cfg.clientId || !this.cfg.redirectUri) throw new Error(`${this.cfg.id} OAuth not configured`);
    const url = new URL(this.cfg.authorizeUrl);
    url.searchParams.set("client_id", this.cfg.clientId);
    url.searchParams.set("redirect_uri", this.cfg.redirectUri);
    url.searchParams.set("response_type", "code");
    url.searchParams.set("scope", this.cfg.scope);
    url.searchParams.set("state", input.state);
    url.searchParams.set("nonce", input.nonce);
    url.searchParams.set("code_challenge", pkceChallenge(input.codeVerifier));
    url.searchParams.set("code_challenge_method", "S256");
    return url.toString();
  }

  async exchangeAndNormalize(input: ExchangeInput): Promise<NormalizedProfile> {
    if (!this.cfg.clientId || !this.cfg.clientSecret || !this.cfg.redirectUri) throw new Error(`${this.cfg.id} OAuth not configured`);

    const tokenResp = await request(this.cfg.tokenUrl, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: this.cfg.clientId,
        client_secret: this.cfg.clientSecret,
        redirect_uri: this.cfg.redirectUri,
        code: input.code,
        code_verifier: input.codeVerifier
      }).toString()
    });

    if (tokenResp.statusCode < 200 || tokenResp.statusCode >= 300) {
      const body = await tokenResp.body.text();
      throw new Error(`TOKEN_EXCHANGE_FAILED ${tokenResp.statusCode} ${body}`);
    }
    const tokenJson = (await tokenResp.body.json()) as { access_token: string; token_type?: string };
    if (!tokenJson.access_token) throw new Error("NO_ACCESS_TOKEN");

    const profileResp = await request(this.cfg.userInfoUrl, {
      method: "GET",
      headers: { authorization: `Bearer ${tokenJson.access_token}` }
    });
    if (profileResp.statusCode < 200 || profileResp.statusCode >= 300) {
      const body = await profileResp.body.text();
      throw new Error(`PROFILE_FETCH_FAILED ${profileResp.statusCode} ${body}`);
    }
    const raw = await profileResp.body.json();
    const normalized = this.cfg.mapProfile(raw);
    if (normalized.provider !== this.cfg.id) normalized.provider = this.cfg.id;
    return normalized;
  }
}

