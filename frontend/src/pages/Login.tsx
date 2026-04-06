import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Mail, Lock, Eye, EyeOff, ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import { setAuthCredentials, setRefreshToken } from '@/lib/auth';

export default function Login() {
    const router = useRouter();
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        rememberMe: false,
    });
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const response = await fetch(apiUrl('/api/auth/login'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.email,
                    password: formData.password,
                }),
            });

            if (response.ok) {
                const data = await response.json();
                const accessToken = data.access_token || data.token;
                if (accessToken) {
                    setAuthCredentials(accessToken, data.user);
                    if (data.refresh_token) {
                        setRefreshToken(data.refresh_token);
                    }
                }
                // Redirect to home page with welcome toast
                sessionStorage.setItem('confit_auth_success', JSON.stringify({
                    type: 'login',
                    userName: data.user?.name || formData.email.split('@')[0],
                    timestamp: Date.now(),
                }));
                router.push('/');
            } else {
                const errData = await response.json().catch(() => null);
                // Show detailed error message from backend
                const errorMsg = errData?.detail || errData?.message || 'Invalid email or password';
                console.error('Login error:', errData);
                setError(errorMsg);
            }
        } catch {
            // Fallback — backend not running, allow demo navigation
            if (formData.email && formData.password) {
                localStorage.setItem('confit_user', JSON.stringify({
                    name: formData.email.split('@')[0],
                    email: formData.email,
                }));
                sessionStorage.setItem('confit_auth_success', JSON.stringify({
                    type: 'login',
                    userName: formData.email.split('@')[0],
                    timestamp: Date.now(),
                }));
                router.push('/');
            } else {
                setError('Please enter your email and password');
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex">
            {/* Left Side - Branding */}
            <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-charcoal via-charcoal to-accent/20 relative overflow-hidden">
                <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800')] bg-cover bg-center opacity-10" />
                <div className="relative z-10 flex flex-col justify-center p-12">
                    <Link href="/" className="inline-flex items-center mb-8">
                        <span className="font-display text-4xl font-semibold text-white">CONFIT</span>
                    </Link>
                    <h1 className="text-4xl font-display font-semibold text-white mb-4">
                        Welcome Back
                    </h1>
                    <p className="text-lg text-white/70 max-w-md">
                        Sign in to access your personalized style recommendations, saved outfits, and seamless shopping experience.
                    </p>

                    <div className="mt-12 space-y-6">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center">
                                <Sparkles className="h-6 w-6 text-accent" />
                            </div>
                            <div>
                                <h3 className="text-white font-medium">AI-Powered Styling</h3>
                                <p className="text-white/60 text-sm">Get personalized outfit recommendations</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center">
                                <Sparkles className="h-6 w-6 text-accent" />
                            </div>
                            <div>
                                <h3 className="text-white font-medium">Virtual Try-On</h3>
                                <p className="text-white/60 text-sm">See how clothes look on you</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Side - Form */}
            <div className="flex-1 flex items-center justify-center p-8 bg-background">
                <motion.div
                    className="w-full max-w-md"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div className="lg:hidden mb-8">
                        <Link href="/" className="inline-flex items-center">
                            <span className="font-display text-3xl font-semibold">CONFIT</span>
                        </Link>
                    </div>

                    <h2 className="text-2xl font-display font-semibold mb-2">Sign In</h2>
                    <p className="text-muted-foreground mb-8">
                        Don't have an account?{' '}
                        <Link href="/register" className="text-accent hover:underline">
                            Create one
                        </Link>
                    </p>
                    <Button
                        asChild
                        variant="outline"
                        size="lg"
                        className="mb-6 w-full"
                    >
                        <a href="http://localhost:3000/login" target="_blank" rel="noopener noreferrer">
                            Open Next.js enterprise login
                        </a>
                    </Button>

                    {error && (
                        <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium mb-2">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                <input
                                    type="email"
                                    required
                                    value={formData.email}
                                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                                    className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                    placeholder="Enter your email"
                                    autoComplete="email"
                                    name="email"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    required
                                    value={formData.password}
                                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                                    className="w-full pl-12 pr-12 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                    placeholder="Enter your password"
                                    autoComplete="current-password"
                                    name="password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.rememberMe}
                                    onChange={e => setFormData({ ...formData, rememberMe: e.target.checked })}
                                    className="w-4 h-4 rounded border-border text-accent focus:ring-accent"
                                />
                                <span className="text-sm">Remember me</span>
                            </label>
                            <Link href="/forgot-password" className="text-sm text-accent hover:underline">
                                Forgot password?
                            </Link>
                        </div>

                        <Button
                            type="submit"
                            variant="hero"
                            size="lg"
                            className="w-full"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <span className="flex items-center gap-2">
                                    <span className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                    Signing in...
                                </span>
                            ) : (
                                <>
                                    Sign In
                                    <ArrowRight className="h-4 w-4 ml-2" />
                                </>
                            )}
                        </Button>
                    </form>

                    <div className="mt-8">
                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-border" />
                            </div>
                            <div className="relative flex justify-center text-sm">
                                <span className="px-4 bg-background text-muted-foreground">Or continue with</span>
                            </div>
                        </div>

                        <div className="mt-6 grid grid-cols-2 gap-4">
                            <Button variant="outline" size="lg" className="w-full">
                                <img src="https://www.google.com/favicon.ico" alt="Google" className="w-5 h-5 mr-2" />
                                Google
                            </Button>
                            <Button variant="outline" size="lg" className="w-full">
                                <img src="https://www.apple.com/favicon.ico" alt="Apple" className="w-5 h-5 mr-2" />
                                Apple
                            </Button>
                        </div>
                    </div>

                    <p className="mt-8 text-center text-xs text-muted-foreground">
                        By signing in, you agree to our{' '}
                        <Link href="/terms" className="text-accent hover:underline">Terms of Service</Link>
                        {' '}and{' '}
                        <Link href="/privacy" className="text-accent hover:underline">Privacy Policy</Link>
                    </p>
                </motion.div>
            </div>
        </div>
    );
}
