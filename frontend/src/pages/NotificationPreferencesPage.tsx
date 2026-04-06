/**
 * CONFIT — Notification Preferences Page
 * ========================================
 * Standalone page at /notification-preferences.
 * Renders the NotificationPreferences component inside MainLayout.
 * Detects customer vs. store_owner from auth context.
 */

import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Bell, Settings } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { NotificationPreferences } from '@/components/notifications/NotificationPreferences';
import type { RecipientType } from '@/stores/notificationPreferencesStore';

export default function NotificationPreferencesPage() {
  const { user } = useAuth();
  const router = useRouter();

  const userId = user?.id || 'guest';

  // Determine recipient type — in a real app this comes from user roles.
  // For now, we check URL/query or default to 'customer'. 
  // Users can switch view via a tab in the page header.
  const urlParams = new URLSearchParams(window.location.search);
  const viewParam = urlParams.get('view');
  const initialView: RecipientType =
    viewParam === 'owner' ? 'store_owner' : 'customer';

  return (
    <MainLayout>
      <div className="container py-8 max-w-2xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-8"
        >
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.back()}
              className="hover:bg-muted/50"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500/20 to-yellow-500/10 flex items-center justify-center">
                  <Settings className="h-4.5 w-4.5 text-accent" />
                </div>
                <div>
                  <h1 className="text-xl font-display font-semibold">
                    Notification Preferences
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    Manage how and when you receive notifications
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => router.push('/notifications')}
          >
            <Bell className="h-4 w-4" />
            View Notifications
          </Button>
        </motion.div>

        {/* View switcher (for users with dual roles) */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="flex gap-2 mb-6"
        >
          {(['customer', 'store_owner'] as RecipientType[]).map((type) => {
            const isActive = type === initialView;
            const label = type === 'customer' ? 'Customer' : 'Store Owner';
            return (
              <button
                key={type}
                onClick={() => {
                  const url = new URL(window.location.href);
                  url.searchParams.set(
                    'view',
                    type === 'store_owner' ? 'owner' : 'customer'
                  );
                  window.history.replaceState({}, '', url.toString());
                  // Force re-render by navigating
                  router.replace(`/notification-preferences?view=${type === 'store_owner' ? 'owner' : 'customer'}`);
                }}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-accent/15 text-accent'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                }`}
              >
                {label}
              </button>
            );
          })}
        </motion.div>

        {/* Preferences */}
        <NotificationPreferences
          recipientId={userId}
          recipientType={initialView}
        />
      </div>
    </MainLayout>
  );
}
