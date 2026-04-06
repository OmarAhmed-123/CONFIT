import type { Env } from "../config/env.js";
import { OAuth2BasicProvider } from "./oauth2-basic.provider.js";

export function createFacebookProvider(env: Env) {
  return new OAuth2BasicProvider({
    id: "facebook",
    authorizeUrl: "https://www.facebook.com/v20.0/dialog/oauth",
    tokenUrl: "https://graph.facebook.com/v20.0/oauth/access_token",
    userInfoUrl: "https://graph.facebook.com/me?fields=id,name,email,picture",
    clientId: env.OAUTH_FACEBOOK_CLIENT_ID,
    clientSecret: env.OAUTH_FACEBOOK_CLIENT_SECRET,
    redirectUri: env.OAUTH_FACEBOOK_REDIRECT_URI,
    scope: "public_profile email",
    mapProfile: (raw: any) => ({
      provider: "facebook",
      providerAccountId: String(raw.id),
      email: typeof raw.email === "string" ? raw.email : undefined,
      name: typeof raw.name === "string" ? raw.name : undefined,
      pictureUrl: raw?.picture?.data?.url ? String(raw.picture.data.url) : undefined
    })
  });
}

