"use client";

import { Suspense, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authErrors } from "@/lib/api";
import { useSession } from "@/components/session/SessionProvider";

const ERROR_HELP: Record<string, string> = {
  PROVIDER_UNAVAILABLE:
    "OAuth is not configured for this provider. In services/api set DEV_OAUTH_MOCK_ENABLED=true for local mock login, or set OAUTH_* client ID/secret and redirect URIs for real Google/Facebook login (see README).",
  PROVIDER_DENIED: "The provider denied access. Try again or use another account.",
  INVALID_STATE: "Session state mismatch. Start sign-in again from the login page.",
  TOKEN_FAILED: "Could not complete sign-in. Check API logs and OAuth redirect URIs.",
  SESSION_EXPIRED: "Your session expired. Sign in again.",
};

function CallbackContent() {
  const params = useSearchParams();
  const router = useRouter();
  const { reload } = useSession();

  const error = useMemo(() => {
    const e = params.get("error");
    if (!e) return null;
    const parsed = authErrors.safeParse(e);
    return parsed.success ? parsed.data : "TOKEN_FAILED";
  }, [params]);

  const errorDetail = error ? ERROR_HELP[error] ?? "Sign-in could not be completed." : null;

  useEffect(() => {
    if (error) return;
    void (async () => {
      await reload();
      const cookieMatch = document.cookie.match(/(?:^|; )confit_return_to=([^;]+)/);
      const returnTo = cookieMatch ? decodeURIComponent(cookieMatch[1]) : "";
      if (cookieMatch) {
        document.cookie = "confit_return_to=; Max-Age=0; path=/; SameSite=Lax";
      }
      if (returnTo) {
        window.location.href = returnTo;
        return;
      }
      const clientAppOrigin = process.env.NEXT_PUBLIC_CLIENT_APP_ORIGIN;
      if (clientAppOrigin) {
        window.location.href = `${clientAppOrigin.replace(/\/$/, "")}/`;
        return;
      }
      router.replace("/app");
    })();
  }, [error, reload, router]);

  return (
    <div className="flex flex-1 items-center justify-center bg-neutral-950 px-6 py-16 text-white">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur">
        {error ? (
          <>
            <h1 className="text-xl font-semibold">Authentication failed</h1>
            <p className="mt-2 font-mono text-xs text-white/50">{error}</p>
            <p className="mt-3 text-sm text-white/80">{errorDetail}</p>
            <a className="mt-6 inline-flex rounded-xl bg-white px-4 py-2 text-sm font-medium text-black" href="/login">
              Back to login
            </a>
          </>
        ) : (
          <>
            <h1 className="text-xl font-semibold">Signing you in…</h1>
            <p className="mt-2 text-sm text-white/70">Validating session and securing cookies.</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-1 items-center justify-center bg-neutral-950 px-6 py-16 text-white">
          <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur">
            <h1 className="text-xl font-semibold">Signing you in...</h1>
            <p className="mt-2 text-sm text-white/70">Loading callback state.</p>
          </div>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}

