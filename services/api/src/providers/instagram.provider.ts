import type { Env } from "../config/env.js";
import { OAuth2BasicProvider } from "./oauth2-basic.provider.js";

export function createInstagramProvider(env: Env) {
  return new OAuth2BasicProvider({
    id: "instagram",
    authorizeUrl: "https://api.instagram.com/oauth/authorize",
    tokenUrl: "https://api.instagram.com/oauth/access_token",
    userInfoUrl: "https://graph.instagram.com/me?fields=id,username,account_type",
    clientId: env.OAUTH_INSTAGRAM_CLIENT_ID,
    clientSecret: env.OAUTH_INSTAGRAM_CLIENT_SECRET,
    redirectUri: env.OAUTH_INSTAGRAM_REDIRECT_URI,
    scope: "user_profile",
    mapProfile: (raw: any) => ({
      provider: "instagram",
      providerAccountId: String(raw.id),
      name: typeof raw.username === "string" ? raw.username : undefined
    })
  });
}

