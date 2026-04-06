import { lazy, Suspense, ComponentType } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

// Lazy page loader factory
function PageFallback({ message }: { message?: string }) {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <div className="text-center">
        <Skeleton className="mx-auto h-8 w-32" />
        <p className="mt-4 text-sm text-muted-foreground">{message || 'Loading...'}</p>
      </div>
    </div>
  );
}

export function createLazyPage<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  loadingMessage?: string
) {
  const LazyComponent = lazy(importFn);

  return function LazyPage(props: React.ComponentProps<T>) {
    return (
      <Suspense fallback={<PageFallback message={loadingMessage} />}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}

// Preload function for route prefetching
export function preloadComponent(importFn: () => Promise<any>) {
  return () => importFn();
}

// Lazy loaded pages with custom loading messages
export const LazyLanding = createLazyPage(
  () => import('@/pages/Index'),
  'Loading landing page...'
);

export const LazyDiscover = createLazyPage(
  () => import('@/pages/Discover'),
  'Loading discover...'
);

export const LazyVirtualStylist = createLazyPage(
  () => import('@/pages/VirtualStylist'),
  'Loading virtual stylist...'
);

export const LazyVirtualTryOn = createLazyPage(
  () => import('@/pages/VirtualTryOn'),
  'Loading virtual try-on...'
);

export const LazyTryOnLive = createLazyPage(
  () => import('@/pages/TryOnLive'),
  'Loading live AR try-on...'
);

export const LazyOutfitBuilder = createLazyPage(
  () => import('@/pages/OutfitBuilder'),
  'Loading outfit builder...'
);

export const LazyWardrobe = createLazyPage(
  () => import('@/pages/Wardrobe'),
  'Loading wardrobe...'
);

export const LazyVisualSearch = createLazyPage(
  () => import('@/pages/VisualSearch'),
  'Loading visual search...'
);

export const LazyProfile = createLazyPage(
  () => import('@/pages/Profile'),
  'Loading profile...'
);

export const LazyProductDetail = createLazyPage(
  () => import('@/pages/ProductDetail'),
  'Loading product...'
);

export const LazyCart = createLazyPage(
  () => import('@/pages/Cart'),
  'Loading cart...'
);

export const LazyCheckout = createLazyPage(
  () => import('@/pages/Checkout'),
  'Loading checkout...'
);

export const LazyOrderHistory = createLazyPage(
  () => import('@/pages/OrderHistory'),
  'Loading orders...'
);

export const LazyBrandDashboard = createLazyPage(
  () => import('@/pages/BrandDashboard'),
  'Loading brand dashboard...'
);

export const LazyAdminPanel = createLazyPage(
  () => import('@/pages/AdminPanel'),
  'Loading admin panel...'
);

export const LazyAuthPage = createLazyPage(
  () => import('@/pages/AuthPage'),
  'Loading authentication...'
);

// Wrapper for AuthPage with props support
export function LazyAuthPageWrapper({ initialMode }: { initialMode: 'login' | 'signup' }) {
  return <LazyAuthPage initialMode={initialMode} />;
}

export const LazyWishlist = createLazyPage(
  () => import('@/pages/Wishlist'),
  'Loading wishlist...'
);

export const LazyBrands = createLazyPage(
  () => import('@/pages/BrandsPage'),
  'Loading brands...'
);

export const LazyNotFound = createLazyPage(
  () => import('@/pages/NotFound'),
  'Loading...'
);

export const LazyAIStylistChat = createLazyPage(
  () => import('@/pages/AIStylistChat'),
  'Loading AI stylist...'
);

export const LazyInfluencerMarketplace = createLazyPage(
  () => import('@/pages/InfluencerMarketplace'),
  'Loading creator marketplace...'
);

export const LazyInfluencerStorefront = createLazyPage(
  () => import('@/pages/InfluencerStorefront'),
  'Loading creator storefront...'
);

export const LazyOutfitDetail = createLazyPage(
  () => import('@/pages/OutfitDetailPage'),
  'Loading outfit...'
);

export const LazyFashionOS = createLazyPage(
  () => import('@/pages/FashionOS'),
  'Loading Fashion OS...'
);

export const LazyGrowthFeed = createLazyPage(
  () => import('@/pages/GrowthFeed'),
  'Loading growth feed...'
);

export const LazyJoinReferral = createLazyPage(
  () => import('@/pages/JoinReferral'),
  'Loading...'
);

export const LazyInvestorLanding = createLazyPage(
  () => import('@/pages/InvestorLanding'),
  "Loading investor landing..."
);

export const LazyInvestorPitchDeck = createLazyPage(
  () => import('@/pages/InvestorPitchDeck'),
  "Loading investor pitch deck..."
);

export const LazySOSTACDashboard = createLazyPage(
  () => import('@/pages/SOSTACDashboard'),
  'Loading SOSTAC analytics...'
);

export const LazyStoreDashboard = createLazyPage(
  () => import('@/pages/StoreDashboard'),
  'Loading store dashboard...'
);

export const LazyNotifications = createLazyPage(
  () => import('@/pages/NotificationsPage'),
  'Loading notifications...'
);

export const LazyNotificationPreferences = createLazyPage(
  () => import('@/pages/NotificationPreferencesPage'),
  'Loading notification preferences...'
);

export const LazyNotificationAnalytics = createLazyPage(
  () => import('@/pages/NotificationAnalyticsDashboard'),
  'Loading notification analytics...'
);

export const LazyAuthCallback = createLazyPage(
  () => import('@/pages/AuthCallback'),
  'Completing sign-in...'
);

export const LazyAlertRulesConfig = createLazyPage(
  () => import('@/pages/AlertRulesConfigPage'),
  'Loading alert configuration...'
);

export const LazyAlertHistory = createLazyPage(
  () => import('@/pages/AlertHistoryPage'),
  'Loading alert history...'
);
