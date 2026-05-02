/**
 * Home Page
 * Landing page for CONFIT - converted from Vite Index.tsx
 */

'use client';

import { useCallback, useEffect, useState, lazy, Suspense, memo } from 'react';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/layout';
import { Hero, Actions, CTA, Occasions } from '@/components/sections';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { SectionSkeleton } from '@/components/loading/SectionSkeleton';

// Lazy load heavy below-the-fold sections to reduce initial bundle
const TodaysStylePicks = lazy(() => import('@/components/sections/TodaysStylePicks').then(m => ({ default: m.TodaysStylePicks })));
const Picks = lazy(() => import('@/components/sections/Picks').then(m => ({ default: m.Picks })));
const AIExperience = lazy(() => import('@/components/sections/AIExperience').then(m => ({ default: m.AIExperience })));
const Trending = lazy(() => import('@/components/sections/Trending').then(m => ({ default: m.Trending })));

function LazySection({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<SectionSkeleton />}>
      {children}
    </Suspense>
  );
}

const MemoizedHero = memo(Hero);

export default function HomePage() {
  const router = useRouter();
  const { user } = useAuth();

  const [prefillNonce, setPrefillNonce] = useState(0);
  const [prefillPrompt, setPrefillPrompt] = useState<string | null>(null);

  // Check for auth success notification on mount - show non-intrusive side toast
  useEffect(() => {
    const authSuccessRaw = sessionStorage.getItem('confit_auth_success');
    if (authSuccessRaw) {
      try {
        const authSuccess = JSON.parse(authSuccessRaw);
        // Only show if recent (within 30 seconds)
        if (Date.now() - authSuccess.timestamp < 30000) {
          // Use stored userName first (immediately available), fallback to context
          const userName = authSuccess.userName || user?.name || user?.email?.split('@')[0] || 'there';
          if (authSuccess.type === 'login') {
            toast.success(`Welcome back, ${userName}!`, {
              description: "You're now signed in. Enjoy your personalized experience.",
            });
          } else if (authSuccess.type === 'registration') {
            toast.success(`Welcome to CONFIT, ${userName}!`, {
              description: "Your account is ready. Start exploring your personalized style.",
            });
          }
        }
      } catch {
        // Ignore parse errors
      }
      sessionStorage.removeItem('confit_auth_success');
    }
  }, [user]);

  const scrollToAI = useCallback(() => {
    const el = document.getElementById("confit-ai-experience");
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const triggerAI = useCallback(
    (prompt: string) => {
      setPrefillPrompt(prompt);
      setPrefillNonce((n) => n + 1);
      scrollToAI();
    },
    [scrollToAI]
  );

  return (
    <MainLayout fullWidth>
      <MemoizedHero
        onStartStyling={() => triggerAI("I need an outfit for a wedding under $150")}
        onTryItOn={() => router.push("/try-on")}
      />
      <LazySection>
        <TodaysStylePicks />
      </LazySection>
      <Actions onFindMyStyle={() => triggerAI("Find my style: modern, minimal, and premium")} />
      <LazySection>
        <Picks />
      </LazySection>
      <Occasions onSelectOccasion={(_, prompt) => triggerAI(prompt)} />
      <LazySection>
        <AIExperience prefillNonce={prefillNonce} prefillPrompt={prefillPrompt} />
      </LazySection>
      <LazySection>
        <Trending />
      </LazySection>
      <CTA onStartStyling={() => triggerAI("I need an outfit for a wedding under $150")} onTryItOn={() => router.push("/try-on")} />
    </MainLayout>
  );
}
