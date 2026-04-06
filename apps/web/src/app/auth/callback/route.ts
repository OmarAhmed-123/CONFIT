import { OAuthProviderSchema } from "@confit/contracts";
import { NextRequest, NextResponse } from "next/server";
import { redirectViaUpstream } from "@/server/auth/upstream";

export async function GET(req: NextRequest) {
  const providerRaw = req.nextUrl.searchParams.get("provider");
  const code = req.nextUrl.searchParams.get("code");
  const state = req.nextUrl.searchParams.get("state");
  if (!providerRaw || !code || !state) {
    return NextResponse.redirect(new URL("/callback?error=TOKEN_FAILED", req.url));
  }
  const provider = OAuthProviderSchema.parse(providerRaw);
  const query = new URLSearchParams({ code, state }).toString();
  return redirectViaUpstream(req, `/auth/callback/${provider}?${query}`);
}
