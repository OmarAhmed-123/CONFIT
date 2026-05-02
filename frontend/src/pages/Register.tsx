import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Mail, Lock, Eye, EyeOff, ArrowRight, User, Sparkles, Check, Calendar,
    ShoppingBag, Store, Palette, Shield, ArrowLeft, Globe, Briefcase,
    Instagram, Camera, Clock
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import { setAuthCredentials, setRefreshToken } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';

// User types available for selection
const USER_TYPES = [
    {
        id: 'shopper',
        label: 'Shopper',
        labelAr: ' shopper',
        description: 'Discover & buy fashion with AI styling',
        descriptionAr: 'discover and buy fashion with AI styling',
        icon: ShoppingBag,
        color: 'from-violet-500 to-purple-600',
        bgColor: 'bg-violet-500/10',
        borderColor: 'border-violet-500',
    },
    {
        id: 'brand_partner',
        label: 'Brand Partner',
        labelAr: 'brand partner',
        description: 'Manage your brand and view analytics',
        descriptionAr: 'manage your brand and view analytics',
        icon: Store,
        color: 'from-amber-500 to-orange-600',
        bgColor: 'bg-amber-500/10',
        borderColor: 'border-amber-500',
    },
    {
        id: 'stylist',
        label: 'Stylist',
        labelAr: 'stylist',
        description: 'Create looks for clients',
        descriptionAr: 'create looks for clients',
        icon: Palette,
        color: 'from-pink-500 to-rose-600',
        bgColor: 'bg-pink-500/10',
        borderColor: 'border-pink-500',
    },
    {
        id: 'admin',
        label: 'Admin',
        labelAr: 'admin',
        description: 'Platform management',
        descriptionAr: 'platform management',
        icon: Shield,
        color: 'from-slate-500 to-gray-600',
        bgColor: 'bg-slate-500/10',
        borderColor: 'border-slate-500',
    },
] as const;

type UserType = typeof USER_TYPES[number]['id'];

export default function Register() {
    const router = useRouter();
    const { refreshUser } = useAuth();
    const [step, setStep] = useState<'select-type' | 'fill-form'>('select-type');
    const [selectedType, setSelectedType] = useState<UserType | null>(null);
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        // Common fields
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        dateOfBirth: '',
        phone: '',
        acceptTerms: false,
        newsletter: true,
        // Brand partner fields
        brand_name: '',
        brand_description: '',
        brand_website: '',
        brand_logo_url: '',
        // Stylist fields
        stylist_bio: '',
        stylist_specialties: [] as string[],
        stylist_portfolio_url: '',
        stylist_experience_years: '',
    });
    const [error, setError] = useState('');

    const passwordRequirements = [
        { label: 'At least 8 characters', met: formData.password.length >= 8 },
        { label: 'Contains uppercase letter', met: /[A-Z]/.test(formData.password) },
        { label: 'Contains lowercase letter', met: /[a-z]/.test(formData.password) },
        { label: 'Contains number', met: /[0-9]/.test(formData.password) },
        { label: 'Contains special character (!@#$%^&*)', met: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(formData.password) },
    ];

    const allRequirementsMet = passwordRequirements.every(r => r.met);
    const passwordsMatch = formData.password === formData.confirmPassword && formData.confirmPassword.length > 0;

    const handleTypeSelect = (type: UserType) => {
        setSelectedType(type);
        setStep('fill-form');
    };

    const handleBack = () => {
        setStep('select-type');
        setSelectedType(null);
        setError('');
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!selectedType) {
            setError('Please select a user type');
            return;
        }

        if (!allRequirementsMet) {
            setError('Please meet all password requirements');
            return;
        }

        if (!passwordsMatch) {
            setError('Passwords do not match');
            return;
        }

        if (!formData.acceptTerms) {
            setError('Please accept the terms and conditions');
            return;
        }

        const normalizedEmail = formData.email.trim().toLowerCase();
        if (!normalizedEmail) {
            setError('Please enter a valid email address');
            return;
        }

        setIsLoading(true);

        try {
            const existsResponse = await fetch(
                apiUrl(`/api/auth/exists?email=${encodeURIComponent(normalizedEmail)}`)
            );
            if (existsResponse.ok) {
                const existsData = await existsResponse.json();
                if (existsData?.exists) {
                    setError('This email is already registered. Please login directly.');
                    router.push(`/login?email=${encodeURIComponent(normalizedEmail)}`);
                    return;
                }
            }

            const payload: Record<string, unknown> = {
                name: formData.name,
                email: normalizedEmail,
                password: formData.password,
                user_type: selectedType,
                date_of_birth: formData.dateOfBirth || undefined,
                phone: formData.phone || undefined,
                marketing_consent: formData.newsletter,
            };

            // Add role-specific fields
            if (selectedType === 'brand_partner') {
                payload.brand_name = formData.brand_name || undefined;
                payload.brand_description = formData.brand_description || undefined;
                payload.brand_website = formData.brand_website || undefined;
                payload.brand_logo_url = formData.brand_logo_url || undefined;
            }

            if (selectedType === 'stylist') {
                payload.stylist_bio = formData.stylist_bio || undefined;
                payload.stylist_specialties = formData.stylist_specialties.length > 0 ? formData.stylist_specialties : undefined;
                payload.stylist_portfolio_url = formData.stylist_portfolio_url || undefined;
                payload.stylist_experience_years = formData.stylist_experience_years ? parseInt(formData.stylist_experience_years) : undefined;
            }

            const response = await fetch(apiUrl('/api/auth/register'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                const data = await response.json();
                const accessToken = data.access_token || data.token;
                if (accessToken) {
                    setAuthCredentials(accessToken, data.user);
                    if (data.refresh_token) {
                        setRefreshToken(data.refresh_token);
                    }
                    // Refresh AuthContext state to update UI immediately
                    await refreshUser();
                }
                // Redirect to home page with welcome toast
                sessionStorage.setItem('confit_auth_success', JSON.stringify({
                    type: 'registration',
                    userName: data.user?.name || formData.name,
                    timestamp: Date.now(),
                }));
                router.push('/');
            } else {
                const errData = await response.json().catch(() => null);
                setError(errData?.detail || 'Registration failed. Please try again.');
            }
        } catch {
            setError('Unable to complete registration right now. Please try again in a moment.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex">
            {/* Left Side - Branding */}
            <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-charcoal via-charcoal to-accent/20 relative overflow-hidden">
                <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800')] bg-cover bg-center opacity-10" />
                <div className="relative z-10 flex flex-col justify-center p-12">
                    <Link href="/" className="inline-flex items-center mb-8">
                        <span className="font-display text-4xl font-semibold text-white">CONFIT</span>
                    </Link>
                    <h1 className="text-4xl font-display font-semibold text-white mb-4">
                        Join CONFIT
                    </h1>
                    <p className="text-lg text-white/70 max-w-md">
                        Create your account to unlock personalized styling, exclusive offers, and a seamless fashion experience.
                    </p>

                    <div className="mt-12 space-y-6">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center">
                                <Sparkles className="h-6 w-6 text-accent" />
                            </div>
                            <div>
                                <h3 className="text-white font-medium">Personalized Recommendations</h3>
                                <p className="text-white/60 text-sm">Styles curated just for you</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center">
                                <Sparkles className="h-6 w-6 text-accent" />
                            </div>
                            <div>
                                <h3 className="text-white font-medium">Exclusive Member Perks</h3>
                                <p className="text-white/60 text-sm">Early access to sales and new arrivals</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center">
                                <Sparkles className="h-6 w-6 text-accent" />
                            </div>
                            <div>
                                <h3 className="text-white font-medium">Digital Wardrobe</h3>
                                <p className="text-white/60 text-sm">Organize and build outfits with ease</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Side - Form */}
            <div className="flex-1 flex items-center justify-center p-8 bg-background overflow-y-auto">
                <motion.div
                    className="w-full max-w-lg py-8"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div className="lg:hidden mb-8">
                        <Link href="/" className="inline-flex items-center">
                            <span className="font-display text-3xl font-semibold">CONFIT</span>
                        </Link>
                    </div>

                    <AnimatePresence mode="wait">
                        {/* Step 1: User Type Selection */}
                        {step === 'select-type' && (
                            <motion.div
                                key="select-type"
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 20 }}
                            >
                                <h2 className="text-2xl font-display font-semibold mb-2">Welcome to CONFIT</h2>
                                <p className="text-muted-foreground mb-8">
                                    How would you like to use CONFIT?{' '}
                                    <Link href="/login" className="text-accent hover:underline">
                                        Already have an account?
                                    </Link>
                                </p>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                                    {USER_TYPES.map((type) => {
                                        const Icon = type.icon;
                                        return (
                                            <motion.button
                                                key={type.id}
                                                type="button"
                                                onClick={() => handleTypeSelect(type.id)}
                                                className={cn(
                                                    "relative p-6 rounded-2xl border-2 transition-all duration-200",
                                                    "hover:shadow-lg hover:scale-[1.02]",
                                                    "focus:outline-none focus:ring-2 focus:ring-accent/50",
                                                    "text-left group",
                                                    type.bgColor,
                                                    type.borderColor,
                                                    "hover:border-opacity-100"
                                                )}
                                                whileHover={{ y: -2 }}
                                                whileTap={{ scale: 0.98 }}
                                            >
                                                <div className={cn(
                                                    "w-12 h-12 rounded-xl mb-4 flex items-center justify-center",
                                                    "bg-gradient-to-br",
                                                    type.color
                                                )}>
                                                    <Icon className="h-6 w-6 text-white" />
                                                </div>
                                                <h3 className="font-semibold text-lg mb-1">{type.label}</h3>
                                                <p className="text-sm text-muted-foreground">{type.description}</p>
                                                <ArrowRight className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity text-accent" />
                                            </motion.button>
                                        );
                                    })}
                                </div>
                            </motion.div>
                        )}

                        {/* Step 2: Registration Form */}
                        {step === 'fill-form' && selectedType && (
                            <motion.div
                                key="fill-form"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                            >
                                <button
                                    type="button"
                                    onClick={handleBack}
                                    className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6 transition-colors"
                                >
                                    <ArrowLeft className="h-4 w-4" />
                                    Back to user type selection
                                </button>

                                <div className="flex items-center gap-3 mb-6">
                                    {(() => {
                                        const type = USER_TYPES.find(t => t.id === selectedType);
                                        if (!type) return null;
                                        const Icon = type.icon;
                                        return (
                                            <>
                                                <div className={cn(
                                                    "w-10 h-10 rounded-lg flex items-center justify-center",
                                                    "bg-gradient-to-br",
                                                    type.color
                                                )}>
                                                    <Icon className="h-5 w-5 text-white" />
                                                </div>
                                                <div>
                                                    <h2 className="text-2xl font-display font-semibold">
                                                        {type.label} Registration
                                                    </h2>
                                                    <p className="text-sm text-muted-foreground">{type.description}</p>
                                                </div>
                                            </>
                                        );
                                    })()}
                                </div>

                                {error && (
                                    <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm">
                                        {error}
                                    </div>
                                )}

                                <form onSubmit={handleSubmit} className="space-y-5">
                                    {/* Common Fields */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div>
                                            <label htmlFor="name" className="block text-sm font-medium mb-2">Full Name *</label>
                                            <div className="relative">
                                                <User className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                <input
                                                    id="name"
                                                    type="text"
                                                    required
                                                    value={formData.name}
                                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                                    className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                    placeholder="Enter your name"
                                                    autoComplete="name"
                                                />
                                            </div>
                                        </div>

                                        <div>
                                            <label htmlFor="email" className="block text-sm font-medium mb-2">Email *</label>
                                            <div className="relative">
                                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                <input
                                                    id="email"
                                                    type="email"
                                                    required
                                                    value={formData.email}
                                                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                                                    className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                    placeholder="Enter your email"
                                                    autoComplete="email"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div>
                                            <label htmlFor="phone" className="block text-sm font-medium mb-2">Phone</label>
                                            <div className="relative">
                                                <User className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                <input
                                                    id="phone"
                                                    type="tel"
                                                    value={formData.phone}
                                                    onChange={e => setFormData({ ...formData, phone: e.target.value })}
                                                    className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                    placeholder="+20 xxx xxx xxxx"
                                                    autoComplete="tel"
                                                />
                                            </div>
                                        </div>

                                        <div>
                                            <label htmlFor="dateOfBirth" className="block text-sm font-medium mb-2">Date of Birth</label>
                                            <div className="relative">
                                                <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                <input
                                                    id="dateOfBirth"
                                                    type="date"
                                                    value={formData.dateOfBirth}
                                                    onChange={e => setFormData({ ...formData, dateOfBirth: e.target.value })}
                                                    className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                    max={new Date().toISOString().split('T')[0]}
                                                    title="Date of Birth"
                                                    name="dateOfBirth"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Brand Partner Specific Fields */}
                                    {selectedType === 'brand_partner' && (
                                        <div className="space-y-4 p-4 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                                            <h3 className="font-semibold text-amber-600 flex items-center gap-2">
                                                <Store className="h-4 w-4" />
                                                Brand Information
                                            </h3>
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                <div className="sm:col-span-2">
                                                    <label htmlFor="brand_name" className="block text-sm font-medium mb-2">Brand Name *</label>
                                                    <input
                                                        id="brand_name"
                                                        type="text"
                                                        required
                                                        value={formData.brand_name}
                                                        onChange={e => setFormData({ ...formData, brand_name: e.target.value })}
                                                        className="w-full px-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                        placeholder="Your brand name"
                                                    />
                                                </div>
                                                <div className="sm:col-span-2">
                                                    <label htmlFor="brand_description" className="block text-sm font-medium mb-2">Brand Description</label>
                                                    <textarea
                                                        id="brand_description"
                                                        value={formData.brand_description}
                                                        onChange={e => setFormData({ ...formData, brand_description: e.target.value })}
                                                        className="w-full px-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all min-h-[80px]"
                                                        placeholder="Tell us about your brand"
                                                        rows={3}
                                                    />
                                                </div>
                                                <div>
                                                    <label htmlFor="brand_website" className="block text-sm font-medium mb-2">Website</label>
                                                    <div className="relative">
                                                        <Globe className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                        <input
                                                            id="brand_website"
                                                            type="url"
                                                            value={formData.brand_website}
                                                            onChange={e => setFormData({ ...formData, brand_website: e.target.value })}
                                                            className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                            placeholder="https://yourbrand.com"
                                                        />
                                                    </div>
                                                </div>
                                                <div>
                                                    <label htmlFor="brand_logo_url" className="block text-sm font-medium mb-2">Logo URL</label>
                                                    <div className="relative">
                                                        <Camera className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                        <input
                                                            id="brand_logo_url"
                                                            type="url"
                                                            value={formData.brand_logo_url}
                                                            onChange={e => setFormData({ ...formData, brand_logo_url: e.target.value })}
                                                            className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                            placeholder="https://...logo.png"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Stylist Specific Fields */}
                                    {selectedType === 'stylist' && (
                                        <div className="space-y-4 p-4 bg-pink-500/5 border border-pink-500/20 rounded-xl">
                                            <h3 className="font-semibold text-pink-600 flex items-center gap-2">
                                                <Palette className="h-4 w-4" />
                                                Stylist Profile
                                            </h3>
                                            <div className="space-y-4">
                                                <div>
                                                    <label htmlFor="stylist_bio" className="block text-sm font-medium mb-2">Bio</label>
                                                    <textarea
                                                        id="stylist_bio"
                                                        value={formData.stylist_bio}
                                                        onChange={e => setFormData({ ...formData, stylist_bio: e.target.value })}
                                                        className="w-full px-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all min-h-[80px]"
                                                        placeholder="Tell clients about your styling experience and approach"
                                                        rows={3}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                    <div>
                                                        <label htmlFor="stylist_experience_years" className="block text-sm font-medium mb-2">Experience (years)</label>
                                                        <div className="relative">
                                                            <Clock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                            <input
                                                                id="stylist_experience_years"
                                                                type="number"
                                                                min="0"
                                                                max="50"
                                                                value={formData.stylist_experience_years}
                                                                onChange={e => setFormData({ ...formData, stylist_experience_years: e.target.value })}
                                                                className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                                placeholder="5"
                                                            />
                                                        </div>
                                                    </div>
                                                    <div>
                                                        <label htmlFor="stylist_portfolio_url" className="block text-sm font-medium mb-2">Portfolio URL</label>
                                                        <div className="relative">
                                                            <Briefcase className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                            <input
                                                                id="stylist_portfolio_url"
                                                                type="url"
                                                                value={formData.stylist_portfolio_url}
                                                                onChange={e => setFormData({ ...formData, stylist_portfolio_url: e.target.value })}
                                                                className="w-full pl-12 pr-4 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                                placeholder="https://portfolio.com"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium mb-2">Specialties</label>
                                                    <div className="flex flex-wrap gap-2">
                                                        {['Casual', 'Formal', 'Streetwear', 'Luxury', 'Bridal', 'Corporate'].map((specialty) => (
                                                            <button
                                                                key={specialty}
                                                                type="button"
                                                                onClick={() => {
                                                                    const current = formData.stylist_specialties;
                                                                    const updated = current.includes(specialty)
                                                                        ? current.filter(s => s !== specialty)
                                                                        : [...current, specialty];
                                                                    setFormData({ ...formData, stylist_specialties: updated });
                                                                }}
                                                                className={cn(
                                                                    "px-3 py-1.5 rounded-full text-sm border transition-all",
                                                                    formData.stylist_specialties.includes(specialty)
                                                                        ? "bg-pink-500/20 border-pink-500 text-pink-600"
                                                                        : "bg-muted border-border text-muted-foreground hover:border-pink-500/50"
                                                                )}
                                                            >
                                                                {specialty}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Password Fields */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div>
                                            <label htmlFor="password" className="block text-sm font-medium mb-2">Password *</label>
                                            <div className="relative">
                                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                <input
                                                    id="password"
                                                    type={showPassword ? 'text' : 'password'}
                                                    required
                                                    value={formData.password}
                                                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                                                    className="w-full pl-12 pr-12 py-3 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-all"
                                                    placeholder="Create a password"
                                                    autoComplete="new-password"
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => setShowPassword(!showPassword)}
                                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                                >
                                                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                                </button>
                                            </div>
                                            {formData.password.length > 0 && (
                                                <div className="mt-2 space-y-1">
                                                    {passwordRequirements.map((req, i) => (
                                                        <div key={i} className={cn("flex items-center gap-2 text-xs", req.met ? 'text-accent' : 'text-muted-foreground')}>
                                                            <Check className={cn("h-3 w-3", req.met ? 'opacity-100' : 'opacity-30')} />
                                                            {req.label}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>

                                        <div>
                                            <label htmlFor="confirmPassword" className="block text-sm font-medium mb-2">Confirm Password *</label>
                                            <div className="relative">
                                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                                <input
                                                    id="confirmPassword"
                                                    type={showPassword ? 'text' : 'password'}
                                                    required
                                                    value={formData.confirmPassword}
                                                    onChange={e => setFormData({ ...formData, confirmPassword: e.target.value })}
                                                    className={cn(
                                                        "w-full pl-12 pr-4 py-3 bg-muted border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all",
                                                        formData.confirmPassword.length > 0
                                                            ? passwordsMatch ? 'border-accent' : 'border-destructive'
                                                            : 'border-border'
                                                    )}
                                                    placeholder="Confirm your password"
                                                    autoComplete="new-password"
                                                />
                                            </div>
                                            {formData.confirmPassword.length > 0 && !passwordsMatch && (
                                                <p className="mt-1 text-xs text-destructive">Passwords do not match</p>
                                            )}
                                        </div>
                                    </div>

                                    {/* Terms and Newsletter */}
                                    <div className="space-y-3">
                                        <label className="flex items-start gap-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.acceptTerms}
                                                onChange={e => setFormData({ ...formData, acceptTerms: e.target.checked })}
                                                className="w-4 h-4 mt-0.5 rounded border-border text-accent focus:ring-accent"
                                            />
                                            <span className="text-sm text-muted-foreground">
                                                I agree to the{' '}
                                                <Link href="/terms" className="text-accent hover:underline">Terms of Service</Link>
                                                {' '}and{' '}
                                                <Link href="/privacy" className="text-accent hover:underline">Privacy Policy</Link>
                                            </span>
                                        </label>

                                        <label className="flex items-start gap-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={formData.newsletter}
                                                onChange={e => setFormData({ ...formData, newsletter: e.target.checked })}
                                                className="w-4 h-4 mt-0.5 rounded border-border text-accent focus:ring-accent"
                                            />
                                            <span className="text-sm text-muted-foreground">
                                                Send me style tips, exclusive offers, and updates
                                            </span>
                                        </label>
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
                                                Creating account...
                                            </span>
                                        ) : (
                                            <>
                                                Create {USER_TYPES.find(t => t.id === selectedType)?.label || ''} Account
                                                <ArrowRight className="h-4 w-4 ml-2" />
                                            </>
                                        )}
                                    </Button>
                                </form>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            </div>
        </div>
    );
}
