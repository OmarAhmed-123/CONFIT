import type { NormalizedProfile, OAuthProviderId } from "../modules/auth/types.js";

export type BuildAuthorizeUrlInput = {
  state: string;
  nonce: string;
  codeVerifier: string;
  appOrigin: string;
};

export type ExchangeInput = {
  code: string;
  codeVerifier: string;
  nonce: string;
};

export interface OAuthProvider {
  id: OAuthProviderId;
  buildAuthorizeUrl(input: BuildAuthorizeUrlInput): string;
  exchangeAndNormalize(input: ExchangeInput): Promise<NormalizedProfile>;
}

