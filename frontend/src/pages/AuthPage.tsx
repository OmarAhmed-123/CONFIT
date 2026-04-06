import { useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Mail, Lock, User, Eye, EyeOff, ArrowRight, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { SocialLoginButtons } from '@/components/auth/SocialLoginButtons';
import { useAuthViewModel } from '@/viewmodels/useAuthViewModel';
import { createTransition } from '@/motion';

interface AuthPageProps {
    initialMode?: 'login' | 'signup' | 'forgot-password';
}

export default function AuthPage({ initialMode = 'login' }: AuthPageProps) {
    const {
        mode,
        form,
        errors,
        isSubmitting,
        showPassword,
        setField,
        setMode,
        submit,
        togglePasswordVisibility,
    } = useAuthViewModel(initialMode);

    // Update mode if prop changes
    useEffect(() => {
        setMode(initialMode);
    }, [initialMode, setMode]);

    // Prefill email from query string (?email=...)
    useEffect(() => {
        try {
            const params = new URLSearchParams(window.location.search);
            const e = params.get('email');
            if (e) setField('email', e);
        } catch {
            // ignore
        }
    }, [setField]);

    const headings: Record<string, { title: string; subtitle: string }> = {
        login: {
            title: 'Welcome Back',
            subtitle: 'Sign in to access your personalized style experience.',
        },
        signup: {
            title: 'Create Account',
            subtitle: 'Join CONFIT and discover your confidence.',
        },
        'forgot-password': {
            title: 'Reset Password',
            subtitle: "Enter your email and we'll send you reset instructions.",
        },
    };

    const { title, subtitle } = headings[mode] || headings.login;

    return (
        <div className="min-h-screen flex">
            {/* Left: Form */}
            <div className="flex-1 flex items-center justify-center p-8">
                <motion.div
                    key={mode}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="w-full max-w-md"
                >
                    <Link href="/" className="inline-block mb-10">
                        <span className="font-display text-3xl font-semibold tracking-tight">CONFIT</span>
                    </Link>

                    <motion.h1
                        className="heading-section mb-2 text-foreground"
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={createTransition({ delay: 0.1 })}
                    >
                        {title}
                    </motion.h1>
                    <motion.p
                        className="text-muted-foreground mb-8 text-base leading-relaxed"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={createTransition({ delay: 0.2 })}
                    >
                        {subtitle}
                    </motion.p>

                    {mode === 'login' && (
                        <div className="mb-6 space-y-3">
                            <SocialLoginButtons />
                            <p className="text-xs text-muted-foreground text-center">Use secure social sign-in powered by the Next.js auth authority.</p>
                        </div>
                    )}

                    <form onSubmit={submit} className="space-y-5" autoComplete="on">
                        {/* Hidden username field for browser autocomplete detection */}
                        <input
                            type="text"
                            name="username"
                            autoComplete="username email"
                            defaultValue={form.email}
                            className="hidden"
                            tabIndex={-1}
                            aria-hidden="true"
                        />

                        {mode === 'signup' && (
                            <div>
                                <Label htmlFor="fullName">Full Name</Label>
                                <div className="relative mt-1">
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <motion.div
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={createTransition({ delay: 0.3 })}
                                    >
                                        <Input
                                            id="fullName"
                                            value={form.fullName}
                                            onChange={e => setField('fullName', e.target.value)}
                                            placeholder="Your name"
                                            className={cn("pl-10 bg-background border-border text-foreground placeholder:text-muted-foreground/60", errors.fullName && "border-destructive")}
                                            maxLength={100}
                                            autoComplete="name"
                                            name="fullName"
                                        />
                                    </motion.div>
                                </div>
                                {errors.fullName && <p className="text-xs text-destructive mt-1">{errors.fullName}</p>}
                            </div>
                        )}

                        <div>
                            <Label htmlFor="email">Email</Label>
                            <div className="relative mt-1">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="email"
                                    type="email"
                                    value={form.email}
                                    onChange={e => setField('email', e.target.value)}
                                    placeholder="you@example.com"
                                    className={cn("pl-10 bg-background border-border text-foreground placeholder:text-muted-foreground/60", errors.email && "border-destructive")}
                                    maxLength={255}
                                    autoComplete={mode === 'login' ? 'username email' : 'email'}
                                    name="email"
                                    inputMode="email"
                                />
                            </div>
                            {errors.email && <p className="text-xs text-destructive mt-1">{errors.email}</p>}
                        </div>

                        {mode !== 'forgot-password' && (
                            <div>
                                <Label htmlFor="password">Password</Label>
                                <div className="relative mt-1">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        value={form.password}
                                        onChange={e => setField('password', e.target.value)}
                                        placeholder="••••••••"
                                        className={cn("pl-10 pr-10 bg-background border-border text-foreground placeholder:text-muted-foreground/60", errors.password && "border-destructive")}
                                        maxLength={128}
                                        autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                                        name="password"
                                    />
                                    <button
                                        type="button"
                                        onClick={togglePasswordVisibility}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                                {errors.password && <p className="text-xs text-destructive mt-1">{errors.password}</p>}
                            </div>
                        )}

                        {mode === 'signup' && (
                            <div>
                                <Label htmlFor="confirmPassword">Confirm Password</Label>
                                <div className="relative mt-1">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="confirmPassword"
                                        type="password"
                                        value={form.confirmPassword}
                                        onChange={e => setField('confirmPassword', e.target.value)}
                                        placeholder="••••••••"
                                        className={cn("pl-10 bg-background border-border text-foreground placeholder:text-muted-foreground/60", errors.confirmPassword && "border-destructive")}
                                        maxLength={128}
                                        autoComplete="new-password"
                                        name="confirmPassword"
                                    />
                                </div>
                                {errors.confirmPassword && <p className="text-xs text-destructive mt-1">{errors.confirmPassword}</p>}
                            </div>
                        )}

                        {/* Forgot Password link - only in login mode */}
                        {mode === 'login' && (
                            <div className="flex justify-end">
                                <button
                                    type="button"
                                    onClick={() => setMode('forgot-password')}
                                    className="text-sm text-accent hover:underline font-medium"
                                >
                                    Forgot password?
                                </button>
                            </div>
                        )}

                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={createTransition({ delay: 0.4 })}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            <Button
                                variant="hero"
                                size="lg"
                                className="w-full shadow-lg hover:shadow-xl transition-all duration-300"
                                type="submit"
                                disabled={isSubmitting}
                            >
                                {isSubmitting
                                    ? 'Processing...'
                                    : mode === 'login'
                                        ? 'Sign In'
                                        : mode === 'signup'
                                            ? 'Create Account'
                                            : 'Send Reset Link'}
                                <ArrowRight className="h-4 w-4 ml-2" />
                            </Button>
                        </motion.div>
                    </form>

                    {/* Mode switching links */}
                    {mode === 'forgot-password' ? (
                        <p className="text-sm text-muted-foreground text-center mt-8">
                            <button
                                onClick={() => setMode('login')}
                                className="text-accent font-medium hover:underline inline-flex items-center gap-1"
                            >
                                <ArrowLeft className="h-3 w-3" />
                                Back to Sign In
                            </button>
                        </p>
                    ) : (
                        <p className="text-sm text-muted-foreground text-center mt-8">
                            {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
                            <button
                                onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
                                className="text-accent font-medium hover:underline"
                            >
                                {mode === 'login' ? 'Sign Up' : 'Sign In'}
                            </button>
                        </p>
                    )}
                </motion.div>
            </div>

            {/* Right: Brand Visual */}
            <div className="hidden lg:flex flex-1 bg-gradient-hero items-center justify-center p-12">
                <div className="max-w-lg text-center text-primary-foreground">
                    <h2 className="heading-hero mb-6">
                        Wear Your <span className="text-gradient-gold">Confidence</span>
                    </h2>
                    <p className="text-lg text-primary-foreground/70 mb-8">
                        AI-powered styling, virtual try-on, and personalized outfit recommendations — all in one platform.
                    </p>
                    <div className="flex justify-center gap-6 text-sm text-primary-foreground/50">
                        <span>AI Stylist</span>
                        <span>•</span>
                        <span>Virtual Try-On</span>
                        <span>•</span>
                        <span>Smart Wardrobe</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
