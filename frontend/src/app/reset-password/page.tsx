'use client';

import { FormEvent, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, ArrowRight, Lock } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/context/AuthContext';

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = useMemo(() => searchParams?.get('token') || '', [searchParams]);
  const { confirmPasswordReset } = useAuth();

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (!token) {
      toast.error('Invalid reset link', {
        description: 'Please request a new password reset email.',
      });
      return;
    }

    if (password.length < 12) {
      toast.error('Password is too short', {
        description: 'Use at least 12 characters.',
      });
      return;
    }

    if (!/[A-Z]/.test(password) || !/\d/.test(password)) {
      toast.error('Password is not strong enough', {
        description: 'Use at least one uppercase letter and one number.',
      });
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setIsSubmitting(true);
    const { error, user } = await confirmPasswordReset(token, password);
    setIsSubmitting(false);

    if (error) {
      toast.error('Reset failed', { description: error });
      return;
    }

    sessionStorage.setItem('confit_auth_success', JSON.stringify({
      type: 'password-reset',
      timestamp: Date.now(),
      userName: user?.name || user?.email?.split('@')[0] || 'there',
    }));

    toast.success('Password updated', {
      description: 'You are signed in now.',
    });
    router.replace('/');
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <Link href="/" className="inline-block mb-10">
          <span className="font-display text-3xl font-semibold tracking-tight">CONFIT</span>
        </Link>

        <h1 className="heading-section mb-2 text-foreground">Create New Password</h1>
        <p className="text-muted-foreground mb-8 text-base leading-relaxed">
          Enter a strong new password. After it is saved, you will be signed in automatically.
        </p>

        {!token && (
          <div className="mb-6 rounded-2xl border border-destructive/30 bg-destructive/8 p-4 text-sm text-destructive">
            This reset link is missing or invalid. Please request a new email.
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label htmlFor="password">New Password</Label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="password"
                name="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="pl-10 bg-background border-border text-foreground"
                autoComplete="new-password"
                maxLength={128}
                required
              />
            </div>
          </div>

          <div>
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="pl-10 bg-background border-border text-foreground"
                autoComplete="new-password"
                maxLength={128}
                required
              />
            </div>
          </div>

          <Button
            variant="hero"
            size="lg"
            className="w-full shadow-lg hover:shadow-xl transition-all duration-300"
            type="submit"
            disabled={isSubmitting || !token}
          >
            {isSubmitting ? 'Updating...' : 'Update Password'}
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </form>

        <p className="mt-8 text-center text-sm text-muted-foreground">
          <Link href="/forgot-password" className="inline-flex items-center gap-1 text-accent font-medium hover:underline">
            <ArrowLeft className="h-3 w-3" />
            Request a new link
          </Link>
        </p>
      </div>
    </div>
  );
}
