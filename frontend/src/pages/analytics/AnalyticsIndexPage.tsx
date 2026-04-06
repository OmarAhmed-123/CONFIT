/**
 * CONFIT Analytics Index Page
 * ===========================
 * Landing page for analytics dashboards with role-based navigation.
 */

import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Store, Building2, User, BarChart3, ArrowRight,
  Shield, TrendingUp, Package, Users
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { isAdmin, isBrandManager, isStoreOwner } from '@/lib/auth/roles';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EASE_LUXURY } from '@/motion';
import { cn } from '@/lib/utils';

// ===========================================
// Analytics Card Component
// ===========================================

interface AnalyticsCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  badge?: string;
  stats?: Array<{ label: string; value: string }>;
  disabled?: boolean;
  comingSoon?: boolean;
}

function AnalyticsCard({
  title,
  description,
  icon,
  href,
  badge,
  stats,
  disabled = false,
  comingSoon = false,
}: AnalyticsCardProps) {
  const router = useRouter();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE_LUXURY }}
    >
      <Card
        className={cn(
          "bg-card/50 backdrop-blur-sm border-border/50 transition-all duration-300",
          !disabled && "hover:border-accent/30 hover:shadow-lg cursor-pointer",
          disabled && "opacity-60"
        )}
        onClick={() => !disabled && router.push(href)}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center">
                {icon}
              </div>
              <div>
                <CardTitle className="text-lg font-semibold">{title}</CardTitle>
                {badge && (
                  <Badge variant="secondary" className="mt-1 text-xs">
                    {badge}
                  </Badge>
                )}
              </div>
            </div>
            {!disabled && !comingSoon && (
              <ArrowRight className="h-5 w-5 text-muted-foreground" />
            )}
            {comingSoon && (
              <Badge variant="outline" className="text-xs">Coming Soon</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">{description}</p>
          {stats && (
            <div className="grid grid-cols-2 gap-2">
              {stats.map((stat) => (
                <div key={stat.label} className="p-2 bg-muted/30 rounded-lg">
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-sm font-semibold">{stat.value}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ===========================================
// Analytics Index Page Component
// ===========================================

export default function AnalyticsIndexPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // Role checks
  const userIsAdmin = isAdmin(user);
  const userIsBrandManager = isBrandManager(user);
  const userIsStoreOwner = isStoreOwner(user);

  // Define available dashboards
  const dashboards = [
    {
      title: 'My Analytics',
      description: 'View your personal shopping analytics, wardrobe stats, and sustainability impact.',
      icon: <User className="h-5 w-5 text-accent" />,
      href: '/analytics/me',
      badge: 'Personal',
      stats: [
        { label: 'Outfits Saved', value: 'View' },
        { label: 'Try-Ons', value: 'History' },
      ],
      show: true,
    },
    {
      title: 'Store Analytics',
      description: 'Store performance metrics including visitors, conversion rates, and top products.',
      icon: <Store className="h-5 w-5 text-accent" />,
      href: '/analytics/store/default',
      badge: 'Store Manager',
      stats: [
        { label: 'Visitors', value: 'Real-time' },
        { label: 'Heatmap', value: 'Peak hours' },
      ],
      show: userIsStoreOwner || userIsAdmin,
    },
    {
      title: 'Brand Analytics',
      description: 'Brand-level insights including sales, quality control, and regional distribution.',
      icon: <Building2 className="h-5 w-5 text-accent" />,
      href: '/analytics/brand/default',
      badge: 'Brand Manager',
      stats: [
        { label: 'Products Sold', value: 'By SKU' },
        { label: 'Rejections', value: 'QC Issues' },
      ],
      show: userIsBrandManager || userIsAdmin,
    },
    {
      title: 'Platform Analytics',
      description: 'Platform-wide metrics including DAU/MAU, revenue, retention cohorts, and conversion funnels.',
      icon: <BarChart3 className="h-5 w-5 text-accent" />,
      href: '/analytics/admin',
      badge: 'Admin Only',
      badgeVariant: 'destructive' as const,
      stats: [
        { label: 'DAU/MAU', value: 'Users' },
        { label: 'Revenue', value: 'Trends' },
      ],
      show: userIsAdmin,
    },
  ];

  const visibleDashboards = dashboards.filter(d => d.show);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center">
              <BarChart3 className="h-5 w-5 text-accent" />
            </div>
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-foreground font-sans tracking-tight">
                Analytics Hub
              </h1>
              <p className="text-sm text-muted-foreground">
                Access your analytics dashboards
              </p>
            </div>
          </div>
        </motion.div>

        {/* Quick Stats Banner */}
        {userIsAdmin && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="mb-8"
          >
            <Card className="bg-gradient-to-r from-accent/10 to-accent/5 border-accent/20">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-accent" />
                  <div>
                    <p className="text-sm font-medium">Admin Access</p>
                    <p className="text-xs text-muted-foreground">
                      You have access to all analytics dashboards
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Dashboard Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {visibleDashboards.map((dashboard, index) => (
            <motion.div
              key={dashboard.href}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 + index * 0.05 }}
            >
              <AnalyticsCard
                title={dashboard.title}
                description={dashboard.description}
                icon={dashboard.icon}
                href={dashboard.href}
                badge={dashboard.badge}
                stats={dashboard.stats}
              />
            </motion.div>
          ))}
        </div>

        {/* Info Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="mt-12"
        >
          <Card className="bg-muted/30 border-border/50">
            <CardContent className="p-6">
              <h3 className="font-semibold mb-4">About Analytics</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-muted-foreground">
                <div className="flex items-start gap-2">
                  <TrendingUp className="h-4 w-4 text-accent mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Real-Time Data</p>
                    <p>Most metrics update in real-time using Redis counters</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Package className="h-4 w-4 text-accent mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Nightly Aggregation</p>
                    <p>Daily summaries are computed at midnight UTC</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Users className="h-4 w-4 text-accent mt-0.5" />
                  <div>
                    <p className="font-medium text-foreground">Role-Based Access</p>
                    <p>Each dashboard is tailored to your access level</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
