/**
 * Login Page
 * Email/password and OAuth authentication
 */

'use client';

import { useMemo, useState, type ComponentType, type FormEvent } from 'react';
import { signIn as nextAuthSignIn } from 'next-auth/react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Shield,
  ShoppingBag,
  Sparkles,
  Store,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/lib/utils';
import { getDefaultRouteForRoles, hasRole, normalizeRole } from '@/lib/auth/roles';
import { toast } from 'sonner';

type LoginIntent = 'shopper' | 'brand_partner' | 'stylist' | 'admin';

const LOGIN_INTENTS: Array<{
  id: LoginIntent;
  label: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  accentClass: string;
}> = [
  {
    id: 'shopper',
    label: 'Shopper',
    description: 'Personal style, orders, and wardrobe',
    icon: ShoppingBag,
    accentClass: 'border-amber-400/40 bg-amber-400/10 text-amber-100',
  },
  {
    id: 'brand_partner',
    label: 'Brand Partner',
    description: 'Products, orders, and analytics',
    icon: Store,
    accentClass: 'border-orange-400/40 bg-orange-400/10 text-orange-100',
  },
  {
    id: 'stylist',
    label: 'Stylist',
    description: 'Clients, outfits, and sessions',
    icon: Sparkles,
    accentClass: 'border-pink-400/40 bg-pink-400/10 text-pink-100',
  },
  {
    id: 'admin',
    label: 'Admin',
    description: 'Platform operations and oversight',
    icon: Shield,
    accentClass: 'border-slate-300/30 bg-slate-200/10 text-slate-100',
  },
];

function getIntentDestination(intent: LoginIntent): string {
  switch (intent) {
    case 'brand_partner':
      return '/brand-dashboard';
    case 'stylist':
      return '/stylist-dashboard';
    case 'admin':
      return '/admin';
    default:
      return '/';
  }
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signIn: authSignIn, refreshUser } = useAuth();

  const redirectParam = searchParams?.get('redirect')?.trim() || '';
  const intentParam = (searchParams?.get('intent')?.trim() || '') as LoginIntent;
  const initialIntent = LOGIN_INTENTS.some((intent) => intent.id === intentParam)
    ? intentParam
    : 'shopper';

  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginIntent, setLoginIntent] = useState<LoginIntent>(initialIntent);

  const oauthCallbackUrl = useMemo(
    () => redirectParam || getIntentDestination(loginIntent),
    [loginIntent, redirectParam]
  );

  const handleEmailLogin = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await authSignIn(email, password);

      if (result.error) {
        toast.error(result.error);
        return;
      }

      const normalizedTargetRole = normalizeRole(loginIntent);
      const userRoles = result.user?.roles;
      let destination = redirectParam || getDefaultRouteForRoles(userRoles);

      if (!redirectParam) {
        if (normalizedTargetRole === 'user') {
          destination = '/';
        } else if (hasRole(userRoles, normalizedTargetRole)) {
          destination = getIntentDestination(loginIntent);
        }
      }

      sessionStorage.setItem('confit_auth_success', JSON.stringify({
        type: 'login',
        userName: result.user?.name || result.user?.email?.split('@')[0] || 'there',
        timestamp: Date.now(),
      }));

      await refreshUser();
      toast.success('Welcome back!');
      router.push(destination);
      router.refresh();
    } catch (error) {
      console.error('Login page email sign-in failed:', error);
      toast.error(error instanceof Error ? error.message : 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    try {
      const loginHint = (searchParams?.get('email') || email || '').trim();
      await nextAuthSignIn(
        'google',
        { callbackUrl: oauthCallbackUrl },
        {
          prompt: 'select_account',
          ...(loginHint ? { login_hint: loginHint } : {}),
        }
      );
    } catch (error) {
      console.error('Google login failed:', error);
      toast.error('Google login failed');
      setIsLoading(false);
    }
  };

  const handleAppleLogin = async () => {
    setIsLoading(true);
    try {
      await nextAuthSignIn('apple', { callbackUrl: oauthCallbackUrl });
    } catch (error) {
      console.error('Apple login failed:', error);
      toast.error('Apple login failed');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-5xl grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="relative overflow-hidden rounded-[28px] border border-[var(--color-beige-200)] bg-[radial-gradient(circle_at_top_left,_rgba(212,175,55,0.18),_transparent_38%),linear-gradient(145deg,#111827,#1f2937_55%,#2b3442)] p-8 text-white shadow-[0_24px_80px_rgba(17,24,39,0.28)]">
          <div className="absolute inset-0 bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.05)_35%,transparent_70%)]" />
          <div className="relative">
            <p className="text-sm uppercase tracking-[0.22em] text-white/60">Role-aware access</p>
            <h1 className="mt-4 text-4xl font-display font-semibold leading-tight">
              Sign in once and land in the right workspace.
            </h1>
            <p className="mt-4 max-w-xl text-sm text-white/72 md:text-base">
              CONFIT now routes shoppers, brand partners, stylists, and admins through one secure
              authentication flow with role-aware navigation and dashboards.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {LOGIN_INTENTS.map((intent) => {
                const Icon = intent.icon;
                const isActive = loginIntent === intent.id;
                return (
                  <button
                    key={intent.id}
                    type="button"
                    onClick={() => setLoginIntent(intent.id)}
                    className={cn(
                      'rounded-2xl border p-4 text-left transition-all',
                      isActive
                        ? `${intent.accentClass} shadow-[0_18px_50px_rgba(0,0,0,0.18)]`
                        : 'border-white/12 bg-white/6 text-white/88 hover:border-white/28 hover:bg-white/10'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'flex h-11 w-11 items-center justify-center rounded-2xl',
                        isActive ? 'bg-white/85 text-slate-900' : 'bg-white/10 text-white'
                      )}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="font-semibold">{intent.label}</div>
                        <div className={cn(
                          'text-xs',
                          isActive ? 'opacity-80' : 'text-white/60'
                        )}>
                          {intent.description}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="mt-6 rounded-2xl border border-white/12 bg-white/6 p-4 text-sm text-white/72">
              {redirectParam
                ? `After sign-in you will return to ${redirectParam}.`
                : `Selected workspace: ${LOGIN_INTENTS.find((intent) => intent.id === loginIntent)?.label}.`}
            </div>
          </div>
        </section>

        <section className="rounded-[28px] border border-[var(--color-beige-200)] bg-white p-8 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
          <div className="mb-8">
            <h2 className="text-3xl font-display font-semibold">Welcome Back</h2>
            <p className="mt-2 text-[var(--color-gray-600)]">
              Continue with your preferred sign-in method.
            </p>
          </div>

          <div className="space-y-3 mb-6">
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleGoogleLogin}
              disabled={isLoading}
            >
              <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Continue with Google
            </Button>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleAppleLogin}
              disabled={isLoading}
            >
              <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.4c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.24-.69.89-1.84 1.41-2.97 1.34-.15-1.15.41-2.35 1.07-3.08z" />
              </svg>
              Continue with Apple
            </Button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--color-beige-200)]" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-[var(--color-gray-500)]">
                Or continue with email
              </span>
            </div>
          </div>

          <form onSubmit={handleEmailLogin} className="space-y-4">
            <div>
              <label htmlFor="email" className="label">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" />
                Remember me
              </label>
              <Link
                href="/forgot-password"
                className="text-[var(--color-gold-400)] hover:underline"
              >
                Forgot password?
              </Link>
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--color-gray-600)]">
            Don&apos;t have an account?{' '}
            <Link
              href="/register"
              className="text-[var(--color-gold-400)] hover:underline font-medium"
            >
              Sign up
            </Link>
          </p>
        </section>
      </div>
    </div>
  );
}
