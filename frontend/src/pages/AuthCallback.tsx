/**
 * CONFIT — Auth Callback Page
 * ============================
 * Handles OAuth callback redirects from the Next.js auth authority.
 * Processes tokens on success or displays error messages on failure.
 */

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Loader2, AlertTriangle, CheckCircle, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { EASE_LUXURY } from '@/motion';

const ERROR_MESSAGES: Record<string, { title: string; description: string }> = {
  PROVIDER_UNAVAILABLE: {
    title: 'Provider Unavailable',
    description:
      'The authentication provider is not currently available. Please try again later or use email sign-in.',
  },
  UPSTREAM_UNAVAILABLE: {
    title: 'Auth Service Unavailable',
    description:
      'The authentication service is temporarily unreachable. Please try again in a moment.',
  },
  TOKEN_FAILED: {
    title: 'Authentication Failed',
    description:
      'We could not complete the sign-in process. Please try again.',
  },
  INVALID_STATE: {
    title: 'Session Expired',
    description:
      'Your authentication session has expired. Please try signing in again.',
  },
};

const DEFAULT_ERROR = {
  title: 'Sign-In Error',
  description: 'An unexpected error occurred during sign-in. Please try again.',
};

export default function AuthCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<'loading' | 'error' | 'success'>('loading');
  const [errorInfo, setErrorInfo] = useState(DEFAULT_ERROR);

  useEffect(() => {
    const error = searchParams?.get('error');
    const token = searchParams?.get('token') || searchParams?.get('access_token');

    if (error) {
      setErrorInfo(ERROR_MESSAGES[error] || DEFAULT_ERROR);
      setStatus('error');
      return;
    }

    if (token) {
      // Store token and refresh user state
      localStorage.setItem('confit_token', token);
      const refreshToken = searchParams?.get('refresh_token');
      if (refreshToken) {
        localStorage.setItem('confit_refresh_token', refreshToken);
      }
      refreshUser()
        .then(() => {
          setStatus('success');
          setTimeout(() => router.replace('/'), 1200);
        })
        .catch(() => {
          setErrorInfo({
            title: 'Profile Load Failed',
            description:
              'Signed in successfully, but we could not load your profile. Redirecting home...',
          });
          setStatus('error');
          setTimeout(() => router.replace('/'), 3000);
        });
      return;
    }

    // No error and no token — try refreshing user (cookies may have been set)
    refreshUser()
      .then(() => {
        setStatus('success');
        setTimeout(() => router.replace('/'), 1200);
      })
      .catch(() => {
        setErrorInfo({
          title: 'Sign-In Incomplete',
          description:
            'No authentication credentials were received. Please try signing in again.',
        });
        setStatus('error');
      });
  }, [searchParams, router, refreshUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: EASE_LUXURY }}
        className="text-center max-w-md"
      >
        {status === 'loading' && (
          <>
            <div className="h-16 w-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-6">
              <Loader2 className="h-8 w-8 animate-spin text-accent" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-3 font-sans">
              Completing Sign-In
            </h2>
            <p className="text-muted-foreground">
              Please wait while we verify your credentials…
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="h-16 w-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-8 w-8 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-3 font-sans">
              Welcome Back!
            </h2>
            <p className="text-muted-foreground">
              Signed in successfully. Redirecting…
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="h-16 w-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="h-8 w-8 text-amber-400" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-3 font-sans">
              {errorInfo.title}
            </h2>
            <p className="text-muted-foreground mb-8">{errorInfo.description}</p>
            <div className="flex gap-3 justify-center">
              <Button
                variant="outline"
                onClick={() => router.replace('/login')}
                className="gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Sign In
              </Button>
              <Button
                onClick={() => router.replace('/')}
                className="bg-accent text-accent-foreground hover:bg-accent/90"
              >
                Go Home
              </Button>
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
}
