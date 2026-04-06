import { SocialLoginButtons } from "@/components/auth/SocialLoginButtons";

export default function LoginPage() {
  return (
    <div className="flex flex-1 items-center justify-center bg-neutral-950 px-6 py-16 text-white">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-white/70">Secure OAuth (PKCE + rotating refresh) with enterprise protections.</p>
        <div className="mt-6">
          <SocialLoginButtons />
        </div>
      </div>
    </div>
  );
}

