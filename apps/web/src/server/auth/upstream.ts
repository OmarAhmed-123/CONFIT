import { NextRequest, NextResponse } from "next/server";

function getUpstreamOrigin() {
  const origin = process.env.AUTH_UPSTREAM_ORIGIN ?? process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:4000";
  return origin.replace(/\/$/, "");
}

export async function proxyToAuthUpstream(
  req: NextRequest,
  upstreamPath: string,
  init?: { method?: "GET" | "POST"; body?: unknown }
) {
  const method = init?.method ?? req.method;
  const hasBody = method !== "GET" && init?.body !== undefined;
  const headers: Record<string, string> = {
    cookie: req.headers.get("cookie") ?? ""
  };
  if (hasBody) {
    headers["content-type"] = "application/json";
  } else {
    const incomingContentType = req.headers.get("content-type");
    if (incomingContentType) headers["content-type"] = incomingContentType;
  }
  const csrf = req.headers.get("x-csrf-token");
  if (csrf) headers["x-csrf-token"] = csrf;

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(`${getUpstreamOrigin()}${upstreamPath}`, {
      method,
      headers,
      body: hasBody ? JSON.stringify(init?.body) : undefined,
      redirect: "manual"
    });
  } catch (err) {
    const cause = err && typeof err === "object" && "cause" in err ? (err as { cause?: unknown }).cause : undefined;
    let code: string | undefined;
    if (cause && typeof cause === "object") {
      const c = cause as { code?: string; errors?: { code?: string }[] };
      code = c.code;
      if (!code && Array.isArray(c.errors) && c.errors[0]?.code) code = c.errors[0].code;
    }
    const isRefused = code === "ECONNREFUSED" || code === "ENOTFOUND";
    const payload = {
      error: isRefused ? "UPSTREAM_UNAVAILABLE" : "UPSTREAM_FETCH_FAILED",
      message: isRefused
        ? `Auth API unreachable at ${getUpstreamOrigin()}. Start services/api (e.g. npm --prefix services/api run dev).`
        : err instanceof Error
          ? err.message
          : "Upstream request failed"
    };
    return NextResponse.json(payload, { status: 503 });
  }

  const text = await upstreamRes.text();
  const response = new NextResponse(text, {
    status: upstreamRes.status,
    headers: {
      "content-type": upstreamRes.headers.get("content-type") ?? "application/json"
    }
  });
  const setCookie = upstreamRes.headers.get("set-cookie");
  if (setCookie) response.headers.set("set-cookie", setCookie);
  return response;
}

export async function redirectViaUpstream(req: NextRequest, upstreamPath: string) {
  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(`${getUpstreamOrigin()}${upstreamPath}`, {
      method: "GET",
      headers: { cookie: req.headers.get("cookie") ?? "" },
      redirect: "manual"
    });
  } catch {
    const login = new URL("/login", req.url);
    login.searchParams.set("error", "UPSTREAM_UNAVAILABLE");
    return NextResponse.redirect(login);
  }

  const location = upstreamRes.headers.get("location");
  const response = NextResponse.redirect(location ?? "/login");
  const setCookie = upstreamRes.headers.get("set-cookie");
  if (setCookie) response.headers.set("set-cookie", setCookie);
  return response;
}
