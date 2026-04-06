/**
 * CONFIT — useAuthViewModel
 * Encapsulates all auth form state and API interactions.
 * Supports login, signup (with auto-login), and forgot-password flows.
 * Used by: AuthPage
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { z } from 'zod';
import { toast } from 'sonner';
import { apiUrl } from '@/lib/api';

export type AuthMode = 'login' | 'signup' | 'forgot-password';

const loginSchema = z.object({
    email: z.string().trim().email('Please enter a valid email address'),
    password: z.string().min(6, 'Password must be at least 6 characters'),
});

const signupSchema = loginSchema.extend({
    fullName: z.string().trim().min(2, 'Name must be at least 2 characters').max(100),
    confirmPassword: z.string(),
}).refine(d => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
});

const forgotPasswordSchema = z.object({
    email: z.string().trim().email('Please enter a valid email address'),
});

interface FormState {
    fullName: string;
    email: string;
    password: string;
    confirmPassword: string;
}

const initialForm: FormState = {
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
};

export function useAuthViewModel(initialMode: AuthMode = 'login') {
    const router = useRouter();
    const { signIn, signUp, resetPassword } = useAuth();

    const [mode, setMode] = useState<AuthMode>(initialMode);
    const [form, setForm] = useState<FormState>(initialForm);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    const setField = useCallback(<K extends keyof FormState>(key: K, value: FormState[K]) => {
        setForm((prev) => ({ ...prev, [key]: value }));
        if (errors[key]) {
            setErrors((prev) => ({ ...prev, [key]: '' }));
        }
    }, [errors]);

    const switchMode = useCallback((nextMode: AuthMode) => {
        setMode(nextMode);
        setErrors({});
    }, []);

    const submit = useCallback(async (e?: React.FormEvent) => {
        e?.preventDefault();
        setErrors({});

        // ─── Forgot Password ───
        if (mode === 'forgot-password') {
            const result = forgotPasswordSchema.safeParse({ email: form.email });
            if (!result.success) {
                const fieldErrors: Record<string, string> = {};
                result.error.errors.forEach(err => { fieldErrors[err.path[0] as string] = err.message; });
                setErrors(fieldErrors);
                return;
            }
            setIsSubmitting(true);
            const { error } = await resetPassword(form.email);
            setIsSubmitting(false);
            if (error) {
                toast.error('Reset Failed', { description: error });
            } else {
                toast.success('Reset Email Sent', {
                    description: 'Check your inbox for password reset instructions.',
                });
                setMode('login');
            }
            return;
        }

        // ─── Login ───
        if (mode === 'login') {
            const result = loginSchema.safeParse({ email: form.email, password: form.password });
            if (!result.success) {
                const fieldErrors: Record<string, string> = {};
                result.error.errors.forEach(err => { fieldErrors[err.path[0] as string] = err.message; });
                setErrors(fieldErrors);
                return;
            }

            setIsSubmitting(true);

            // Check if user exists before attempting login
            try {
                const existsRes = await fetch(`${apiUrl('/api/auth/exists')}?email=${encodeURIComponent(form.email)}`);
                if (existsRes.ok) {
                    const data = await existsRes.json().catch(() => null);
                    if (data && data.exists === false) {
                        setIsSubmitting(false);
                        toast.error('Account not found', { description: 'Please register first.' });
                        setMode('signup');
                        router.replace(`/register?email=${encodeURIComponent(form.email)}`);
                        return;
                    }
                }
            } catch {
                // Ignore, proceed to normal sign in
            }

            const { error, user } = await signIn(form.email, form.password);
            setIsSubmitting(false);
            if (error) {
                toast.error('Sign In Failed', { description: error });
            } else {
                // Set success notification for homepage with user name
                sessionStorage.setItem('confit_auth_success', JSON.stringify({
                    type: 'login',
                    timestamp: Date.now(),
                    userName: user?.name || form.email.split('@')[0],
                }));
                router.replace('/');
            }
            return;
        }

        // ─── Signup with Auto-Login ───
        const result = signupSchema.safeParse(form);
        if (!result.success) {
            const fieldErrors: Record<string, string> = {};
            result.error.errors.forEach(err => { fieldErrors[err.path[0] as string] = err.message; });
            setErrors(fieldErrors);
            return;
        }

        setIsSubmitting(true);
        const { error: signUpError } = await signUp(form.email, form.password, form.fullName);

        if (signUpError) {
            setIsSubmitting(false);
            toast.error('Sign Up Failed', { description: signUpError });
            return;
        }

        // Auto-login after successful registration
        const { error: loginError, user } = await signIn(form.email, form.password);
        setIsSubmitting(false);

        if (loginError) {
            // Registration succeeded but auto-login failed — tell user to login manually
            toast.success('Account Created', {
                description: 'Your account is ready. Please sign in.',
            });
            setMode('login');
            setForm(prev => ({ ...prev, password: '', confirmPassword: '' }));
            return;
        }

        // Both registration and auto-login succeeded
        sessionStorage.setItem('confit_auth_success', JSON.stringify({
            type: 'registration',
            timestamp: Date.now(),
            userName: user?.name || form.fullName,
        }));
        router.replace('/');
    }, [mode, form, signIn, signUp, resetPassword, router]);

    return {
        mode,
        form,
        errors,
        isSubmitting,
        showPassword,
        setField,
        setMode: switchMode,
        submit,
        togglePasswordVisibility: () => setShowPassword((v) => !v),
    };
}
