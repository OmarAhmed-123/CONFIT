import { nanoid } from "nanoid";
import type { OAuthProviderId, NormalizedProfile } from "./types.js";
import type { OAuthProvider } from "../../providers/provider.js";

export type OAuthStart = {
  provider: OAuthProviderId;
  authorizeUrl: string;
  state: string;
  nonce: string;
  codeVerifier: string;
};

export class OAuthService {
  constructor(private providers: Record<OAuthProviderId, OAuthProvider>) {}

  start(providerId: OAuthProviderId, appOrigin: string): OAuthStart {
    const provider = this.providers[providerId];
    const state = nanoid(24);
    const nonce = nanoid(24);
    const codeVerifier = nanoid(64);
    const authorizeUrl = provider.buildAuthorizeUrl({
      state,
      nonce,
      codeVerifier,
      appOrigin
    });
    return { provider: providerId, authorizeUrl, state, nonce, codeVerifier };
  }

  async exchangeAndNormalize(providerId: OAuthProviderId, input: { code: string; codeVerifier: string; nonce: string }): Promise<NormalizedProfile> {
    const provider = this.providers[providerId];
    return await provider.exchangeAndNormalize(input);
  }
}

