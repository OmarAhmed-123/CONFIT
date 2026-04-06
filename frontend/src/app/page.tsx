/**
 * Home Page
 * Landing page for CONFIT - converted from Vite Index.tsx
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MainLayout } from '@/components/layout';
import { AIExperience, Actions, CTA, Hero, Occasions, Picks, Trending, TodaysStylePicks } from '@/components/sections';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';

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
      <Hero
        onStartStyling={() => triggerAI("I need an outfit for a wedding under $150")}
        onTryItOn={() => router.push("/try-on")}
      />
      <TodaysStylePicks />
      <Actions onFindMyStyle={() => triggerAI("Find my style: modern, minimal, and premium")} />
      <Picks />
      <Occasions onSelectOccasion={(_, prompt) => triggerAI(prompt)} />
      <AIExperience prefillNonce={prefillNonce} prefillPrompt={prefillPrompt} />
      <Trending />
      <CTA onStartStyling={() => triggerAI("I need an outfit for a wedding under $150")} onTryItOn={() => router.push("/try-on")} />
    </MainLayout>
  );
}
