import { OAuthProviderSchema } from "@confit/contracts";
import { NextRequest } from "next/server";
import { redirectViaUpstream } from "@/server/auth/upstream";

function isSafeReturnTo(value: string) {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    const host = url.hostname.toLowerCase();
    if (host === "localhost" || host === "127.0.0.1") return true;
    return host.startsWith("192.168.") || host.startsWith("10.") || host.endsWith(".local");
  } catch {
    return false;
  }
}

export async function GET(req: NextRequest, context: { params: Promise<{ provider: string }> }) {
  const params = await context.params;
  const provider = OAuthProviderSchema.parse(params.provider);
  const response = await redirectViaUpstream(req, `/auth/${provider}`);
  const returnTo = req.nextUrl.searchParams.get("return_to");
  if (returnTo && isSafeReturnTo(returnTo)) {
    response.cookies.set("confit_return_to", returnTo, {
      path: "/",
      sameSite: "lax",
      httpOnly: false,
      secure: req.nextUrl.protocol === "https:",
      maxAge: 60 * 10
    });
  }
  return response;
}
