// CONFIT — Virtual Try-On Edge Function
// Proxies to the CONFIT FastAPI backend so image logic lives in one place (Python).
// Set secret: TRYON_BACKEND_URL = https://your-api.example.com  (no trailing slash on path segment)

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

interface TryOnRequest {
  userImageBase64: string;
  garmentImageUrl: string;
  garmentName: string;
  garmentCategory?: string;
  skinUndertone?: string;
  environment?: string;
}

Deno.serve(async (req: Request): Promise<Response> => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const base = Deno.env.get("TRYON_BACKEND_URL")?.replace(/\/$/, "");
  if (!base) {
    return new Response(
      JSON.stringify({
        error:
          "TRYON_BACKEND_URL is not set. Point it to your CONFIT FastAPI origin (e.g. https://api.example.com). " +
          "Virtual try-on runs on the backend using GEMINI_API_KEY or LOVABLE_API_KEY.",
        code: "BACKEND_NOT_CONFIGURED",
      }),
      { status: 503, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  }

  try {
    const body: TryOnRequest = await req.json();
    if (!body.userImageBase64) {
      return new Response(JSON.stringify({ error: "User image is required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    if (!body.garmentImageUrl) {
      return new Response(JSON.stringify({ error: "Garment image URL is required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const r = await fetch(`${base}/api/virtual-tryon/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        userImageBase64: body.userImageBase64,
        garmentImageUrl: body.garmentImageUrl,
        garmentName: body.garmentName || "garment",
        options: undefined,
      }),
    });

    const data = await r.json().catch(() => ({}));
    const success = Boolean(data?.success);
    const payload = {
      success,
      resultImage: data?.resultImage ?? null,
      message: data?.message ?? (success ? "Virtual try-on completed." : data?.error ?? "Request failed"),
      error: data?.error,
    };

    return new Response(JSON.stringify(payload), {
      status: r.ok && success ? 200 : r.status || 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error occurred";
    console.error("Virtual try-on proxy error:", message);
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
