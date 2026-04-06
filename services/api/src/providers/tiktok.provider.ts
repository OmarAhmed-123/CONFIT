import type { Env } from "../config/env.js";
import { OAuth2BasicProvider } from "./oauth2-basic.provider.js";

export function createTikTokProvider(env: Env) {
  // TikTok Login Kit OAuth2 endpoints differ by product/region; wire actual endpoints per your TikTok app settings.
  return new OAuth2BasicProvider({
    id: "tiktok",
    authorizeUrl: "https://www.tiktok.com/v2/auth/authorize/",
    tokenUrl: "https://open.tiktokapis.com/v2/oauth/token/",
    userInfoUrl: "https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,display_name,avatar_url",
    clientId: env.OAUTH_TIKTOK_CLIENT_ID,
    clientSecret: env.OAUTH_TIKTOK_CLIENT_SECRET,
    redirectUri: env.OAUTH_TIKTOK_REDIRECT_URI,
    scope: "user.info.basic",
    mapProfile: (raw: any) => ({
      provider: "tiktok",
      providerAccountId: String(raw?.data?.user?.open_id ?? raw?.data?.open_id ?? ""),
      name: typeof raw?.data?.user?.display_name === "string" ? raw.data.user.display_name : undefined,
      pictureUrl: typeof raw?.data?.user?.avatar_url === "string" ? raw.data.user.avatar_url : undefined
    })
  });
}

