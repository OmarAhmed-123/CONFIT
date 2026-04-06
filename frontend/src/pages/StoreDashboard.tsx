/**
 * CONFIT — Store Owner Dashboard Page
 * ======================================
 * Protected B2B analytics dashboard for store/factory owners.
 * Integrates KPI strip, advanced filters, sales table, export, and notifications.
 */

import { useEffect, useMemo, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { LayoutDashboard, Store, Bell, ShieldAlert, Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useOwnerNotifications } from '@/hooks/useOwnerNotifications';
import { useDashboardFilters } from '@/hooks/useDashboardFilters';
import { useDashboardKPIs } from '@/hooks/useDashboardKPIs';
import { MOCK_SALES } from '@/services/dashboardMockData';
import { KPIStrip } from '@/components/dashboard/KPIStrip';
import { DashboardFilterBar } from '@/components/dashboard/DashboardFilterBar';
import { SoldProductsTable } from '@/components/dashboard/SoldProductsTable';
import { ExportButton } from '@/components/dashboard/ExportButton';
import { SalesInsightsWidget, type DrillDownFilters } from '@/components/dashboard/SalesInsightsWidget';
import { Button } from '@/components/ui/button';
import { EASE_LUXURY } from '@/motion';
import { isStoreOwner } from '@/lib/auth/roles';

// ─── Page Component ─────────────────────────────────────────────

export default function StoreDashboard() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const highlightId = searchParams.get('highlight');

  // Notification integration
  const { items: notifications } = useOwnerNotifications();

  // Data & filters
  const {
    filters,
    filteredData,
    activeChips,
    availableProductTypes,
    toggleCategory,
    setDateRange,
    setCustomDates,
    setProductType,
    setPriceRange,
    setCustomerSegment,
    setProductName,
    setMarginRange,
    setReturnStatuses,
    clearAll,
  } = useDashboardFilters(MOCK_SALES);

  const kpis = useDashboardKPIs(filteredData, MOCK_SALES);

  // ─── Drill-Down Handler ─────────────────────────────────────
  const handleDrillDown = useCallback((drillFilters: DrillDownFilters) => {
    if (drillFilters.productName) {
      setProductName(drillFilters.productName);
    }
    if (drillFilters.category) {
      toggleCategory(drillFilters.category);
    }
    if (drillFilters.dateSegment) {
      const start = drillFilters.dateSegment.start.split('T')[0];
      const end = drillFilters.dateSegment.end.split('T')[0];
      setCustomDates(start, end);
    }
    if (drillFilters.marginRange) {
      setMarginRange(drillFilters.marginRange);
    }
    if (drillFilters.returnStatus && drillFilters.returnStatus.length > 0) {
      setReturnStatuses(drillFilters.returnStatus);
    }
  }, [setProductName, toggleCategory, setCustomDates, setMarginRange, setReturnStatuses]);

  // Active filter labels for PDF export
  const activeFilterLabels = useMemo(
    () => activeChips.map(c => c.label),
    [activeChips]
  );

  // IDs of recently-sold items (last 24 hours) for gold badge
  const recentSaleIds = useMemo(() => {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    const ids = new Set<string>();
    filteredData.forEach(r => {
      if (new Date(r.saleDate).getTime() >= cutoff) ids.add(r.id);
    });
    return ids;
  }, [filteredData]);

  // Filter key for KPI re-animation
  const filterKey = useMemo(
    () => JSON.stringify(filters),
    [filters]
  );

  // ─── Auth Guard ─────────────────────────────────────────────
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    setIsAuthorized(isStoreOwner(user));
  }, [authLoading, isAuthenticated, router, user]);

  // ─── Loading State ──────────────────────────────────────────
  if (authLoading || isAuthorized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center gap-4"
        >
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
          <span className="text-sm text-muted-foreground">Loading dashboard…</span>
        </motion.div>
      </div>
    );
  }

  // ─── Unauthorized State ─────────────────────────────────────
  if (!isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
          className="text-center max-w-md"
        >
          <div className="h-16 w-16 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-6">
            <ShieldAlert className="h-8 w-8 text-red-400" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-3 font-sans">
            Access Restricted
          </h2>
          <p className="text-muted-foreground mb-6">
            This dashboard is exclusively for store and factory owners.
            If you believe this is an error, please contact support.
          </p>
          <Button
            onClick={() => router.push('/')}
            className="bg-accent text-accent-foreground hover:bg-accent/90"
          >
            Return to Home
          </Button>
        </motion.div>
      </div>
    );
  }

  // ─── Main Dashboard ─────────────────────────────────────────
  const storeName = 'CONFIT Cairo Flagship';
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE_LUXURY }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
        >
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="h-10 w-10 rounded-xl bg-accent/10 flex items-center justify-center">
                <LayoutDashboard className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold text-foreground font-sans tracking-tight">
                  Store Dashboard
                </h1>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Store className="h-3.5 w-3.5" />
                  <span>{storeName}</span>
                  <span className="text-muted-foreground/40">•</span>
                  <span>{today}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <ExportButton data={filteredData} kpis={kpis} storeName={storeName} activeFilterLabels={activeFilterLabels} />
          </div>
        </motion.div>

        {/* KPI Strip */}
        <div className="mb-8">
          <KPIStrip data={kpis} filterKey={filterKey} />
        </div>

        {/* Sales Insights Widget */}
        <div className="mb-8">
          <SalesInsightsWidget
            data={filteredData}
            onDrillDown={handleDrillDown}
          />
        </div>

        {/* Filter Bar */}
        <div className="mb-6">
          <DashboardFilterBar
            filters={filters}
            activeChips={activeChips}
            availableProductTypes={availableProductTypes}
            onToggleCategory={toggleCategory}
            onSetDateRange={setDateRange}
            onSetCustomDates={setCustomDates}
            onSetProductType={setProductType}
            onSetPriceRange={setPriceRange}
            onSetCustomerSegment={setCustomerSegment}
            onClearAll={clearAll}
          />
        </div>

        {/* Sales Table */}
        <SoldProductsTable
          data={filteredData}
          highlightedRowId={highlightId}
          recentSaleIds={recentSaleIds}
          onClearFilters={clearAll}
        />
      </div>
    </div>
  );
}
