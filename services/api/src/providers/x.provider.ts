import type { Env } from "../config/env.js";
import { OAuth2BasicProvider } from "./oauth2-basic.provider.js";

export function createXProvider(env: Env) {
  // Note: X/Twitter OAuth 2.0 user profile access depends on app permissions and endpoint availability.
  // This adapter keeps the same PKCE/state framework; replace userInfoUrl/mapProfile as needed for your app tier.
  return new OAuth2BasicProvider({
    id: "x",
    authorizeUrl: "https://twitter.com/i/oauth2/authorize",
    tokenUrl: "https://api.twitter.com/2/oauth2/token",
    userInfoUrl: "https://api.twitter.com/2/users/me?user.fields=profile_image_url,name,username",
    clientId: env.OAUTH_X_CLIENT_ID,
    clientSecret: env.OAUTH_X_CLIENT_SECRET,
    redirectUri: env.OAUTH_X_REDIRECT_URI,
    scope: "tweet.read users.read offline.access",
    mapProfile: (raw: any) => ({
      provider: "x",
      providerAccountId: String(raw?.data?.id ?? ""),
      name: typeof raw?.data?.name === "string" ? raw.data.name : undefined,
      pictureUrl: typeof raw?.data?.profile_image_url === "string" ? raw.data.profile_image_url : undefined
    })
  });
}

