/**
 * Checkout status illustrations (loading / success / error).
 * Uses lottie-react with embedded animations for payment status feedback.
 * Falls back to framer-motion icons if Lottie fails to load.
 */

import { lazy, Suspense, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Loader2, X } from 'lucide-react';

export type LottieStatusVariant = 'loading' | 'success' | 'error';

export interface LottieStatusProps {
    variant: LottieStatusVariant;
    className?: string;
    loop?: boolean;
}

// Lazy load Lottie to avoid blocking initial render
const Lottie = lazy(() => import('lottie-react'));

// Animation data imports
import successAnimation from '@/assets/lottie/payment-success.json';
import errorAnimation from '@/assets/lottie/payment-error.json';
import loadingAnimation from '@/assets/lottie/payment-loading.json';

const animations = {
    success: successAnimation,
    error: errorAnimation,
    loading: loadingAnimation,
} as const;

// Fallback component using framer-motion
function FallbackStatus({ variant, className }: { variant: LottieStatusVariant; className?: string }) {
    const base = className ?? 'h-28 w-28 mx-auto';

    if (variant === 'loading') {
        return (
            <div className={`flex items-center justify-center ${base}`} aria-busy="true" aria-label="Loading">
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                >
                    <Loader2 className="h-16 w-16 text-accent" strokeWidth={2.25} />
                </motion.div>
            </div>
        );
    }

    if (variant === 'success') {
        return (
            <motion.div
                className={`flex items-center justify-center rounded-full bg-accent/10 ${base}`}
                initial={{ scale: 0.6, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 260, damping: 18 }}
                aria-hidden
            >
                <Check className="h-14 w-14 text-accent" strokeWidth={2.5} />
            </motion.div>
        );
    }

    return (
        <motion.div
            className={`flex items-center justify-center rounded-full bg-destructive/10 ${base}`}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            aria-hidden
        >
            <X className="h-14 w-14 text-destructive" strokeWidth={2.5} />
        </motion.div>
    );
}

// Lottie-based status component
function LottieStatusInner({ variant, className, loop }: LottieStatusProps) {
    const base = className ?? 'h-28 w-28 mx-auto';

    return (
        <div className={base} aria-hidden>
            <Suspense fallback={<FallbackStatus variant={variant} className={className} />}>
                <Lottie
                    animationData={animations[variant]}
                    loop={loop !== false}
                    autoplay
                    style={{ width: '100%', height: '100%' }}
                />
            </Suspense>
        </div>
    );
}

export function LottieStatus(props: LottieStatusProps) {
    const [lottieAvailable, setLottieAvailable] = useState(false);
    const { variant, className, loop } = props;

    // Check if Lottie can load (handles SSR and import failures)
    useEffect(() => {
        import('lottie-react')
            .then(() => setLottieAvailable(true))
            .catch(() => setLottieAvailable(false));
    }, []);

    if (!lottieAvailable) {
        return <FallbackStatus variant={variant} className={className} />;
    }

    return <LottieStatusInner variant={variant} className={className} loop={loop} />;
}
