import { NextResponse, type NextRequest } from "next/server";

function decodeRoleFromAccessToken(token: string | undefined): string | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    const payload = JSON.parse(atob(padded)) as { role?: string };
    return typeof payload.role === "string" ? payload.role : null;
  } catch {
    return null;
  }
}

function isRoleAllowed(pathname: string, role: string | null) {
  if (pathname.startsWith("/app/super-admin")) return role === "super_admin";
  if (pathname.startsWith("/app/admin")) return role === "admin" || role === "super_admin";
  return true;
}

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (!pathname.startsWith("/app")) return NextResponse.next();

  const hasAccess = req.cookies.has("access_token");
  const hasRefresh = req.cookies.has("refresh_token");
  if (!hasAccess && !hasRefresh) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  const role = decodeRoleFromAccessToken(req.cookies.get("access_token")?.value);
  if (!isRoleAllowed(pathname, role)) {
    return NextResponse.json({ error: "FORBIDDEN" }, { status: 403 });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*"]
};
