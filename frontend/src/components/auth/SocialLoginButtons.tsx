'use client';

import { useState } from 'react';
import { signIn } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const hasGoogle = !!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

const providers = [
  ...(hasGoogle ? [{ id: 'google', label: 'Continue with Google', icon: GoogleIcon }] : []),
] as const;

function GoogleIcon() {
  return (
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
  );
}

export function SocialLoginButtons() {
  const [isLoading, setIsLoading] = useState<string | null>(null);

  if (providers.length === 0) {
    return null;
  }

  const handleOAuthLogin = async (providerId: string) => {
    setIsLoading(providerId);
    try {
      const result = await signIn(providerId, {
        callbackUrl: '/',
        redirect: false,
      });
      
      if (result?.error) {
        toast.error(`${providerId.charAt(0).toUpperCase() + providerId.slice(1)} login failed`, {
          description: result.error,
        });
      } else if (result?.ok) {
        toast.success('Welcome!', {
          description: 'Successfully signed in with ' + providerId,
        });
        // Redirect to home
        window.location.href = '/';
      }
    } catch (error) {
      toast.error('Login failed', {
        description: 'An unexpected error occurred',
      });
    } finally {
      setIsLoading(null);
    }
  };

  return (
    <div className="grid gap-2">
      {providers.map((provider) => (
        <Button
          key={provider.id}
          variant="outline"
          size="lg"
          className="w-full"
          onClick={() => handleOAuthLogin(provider.id)}
          disabled={isLoading !== null}
        >
          {isLoading === provider.id ? (
            <span className="animate-spin mr-2"> CircularProgress </span>
          ) : (
            <provider.icon />
          )}
          {isLoading === provider.id ? 'Connecting...' : provider.label}
        </Button>
      ))}
    </div>
  );
}
