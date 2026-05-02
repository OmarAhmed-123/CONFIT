/**
 * Global Providers Wrapper
 * Combines all context providers for the application
 */

'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from 'next-auth/react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Toaster } from '@/components/ui/sonner';
import { CartProvider } from '@/context/CartContext';
import { WishlistProvider } from '@/context/WishlistContext';
import { AuthProvider } from '@/context/AuthContext';
import { GenderProvider } from '@/context/GenderContext';
import { LoadingManagerProvider } from '@/components/loading';
import { RouteSplashController } from '@/components/loading/RouteSplashController';
import { useState, type ReactNode } from 'react';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
            retry: 1,
            gcTime: 5 * 60 * 1000, // 5 minutes cache
          },
        },
      })
  );

  return (
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <LoadingManagerProvider>
            <RouteSplashController />
            <CartProvider>
              <WishlistProvider>
                <GenderProvider>
                  <TooltipProvider>
                    {children}
                    <Toaster position="top-right" richColors />
                  </TooltipProvider>
                </GenderProvider>
              </WishlistProvider>
            </CartProvider>
          </LoadingManagerProvider>
        </AuthProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}
