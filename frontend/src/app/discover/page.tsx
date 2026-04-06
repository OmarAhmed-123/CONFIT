/**
 * Discover Page
 * Product discovery and filtering
 */

'use client';

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { X } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { FilterPanel } from '@/components/product/FilterPanel';
import { AnimatedSection, InteractiveCard, ScrollReveal } from '@/components/experience/interactive';
import { FilterBar, ProductGrid, FilterPill } from '@/components/shared';
import type { SortOption } from '@/types';
import { useDiscoverViewModel } from '@/viewmodels/useDiscoverViewModel';

export default function DiscoverPage() {
  const {
    products,
    sortedProducts,
    fetchError,
    searchQuery,
    setSearchQuery,
    isDebouncing,
    showFilters,
    setShowFilters,
    selectedCategories,
    setSelectedCategories,
    priceRange,
    setPriceRange,
    selectedBrands,
    setSelectedBrands,
    selectedColors,
    setSelectedColors,
    inStockOnly,
    setInStockOnly,
    sortBy,
    setSortBy,
    viewMode,
    setViewMode,
    activeFiltersCount,
    clearAllFilters,
    loadMore,
    isLoadingMore,
    hasMore,
  } = useDiscoverViewModel();

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!sentinelRef.current) return;

    const el = sentinelRef.current;
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry?.isIntersecting) return;
        loadMore().catch(() => undefined);
      },
      { root: null, rootMargin: "500px", threshold: 0.01 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [loadMore]);

  return (
    <MainLayout>
      <div className="container py-8">
        {/* Page Header */}
        <ScrollReveal className="mb-8">
          <h1 className="heading-hero mb-2">Discover</h1>
          <p className="text-muted-foreground">
            Explore {products.length} curated pieces from the world's best brands
          </p>
        </ScrollReveal>

        <ScrollReveal className="mb-8">
          <div className="rounded-2xl border border-accent/30 bg-gradient-to-r from-accent/15 via-primary/10 to-transparent p-5 md:p-6 shadow-lg">
            <p className="text-xs uppercase tracking-[0.22em] text-accent/80 mb-2">AI Suggestions</p>
            <p className="text-sm md:text-base text-foreground/90">
              Try curated look flows: <span className="font-medium">"Weekend minimal under $120"</span>,{" "}
              <span className="font-medium">"Date night monochrome"</span>,{" "}
              <span className="font-medium">"Power workwear capsule"</span>.
            </p>
          </div>
        </ScrollReveal>

        <FilterBar
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          isDebouncing={isDebouncing}
          showFilters={showFilters}
          setShowFilters={setShowFilters}
          activeFiltersCount={activeFiltersCount}
          sortBy={sortBy}
          setSortBy={setSortBy as (v: SortOption) => void}
          viewMode={viewMode}
          setViewMode={setViewMode}
        />

        {/* Active Filters Pills */}
        {activeFiltersCount > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-wrap gap-2 mb-6"
          >
            {selectedCategories.map((cat) => (
              <FilterPill
                key={cat}
                label={cat}
                onRemove={() => setSelectedCategories(selectedCategories.filter((c) => c !== cat))}
              />
            ))}
            {selectedBrands.map((brand) => (
              <FilterPill
                key={brand}
                label={brand}
                onRemove={() => setSelectedBrands(selectedBrands.filter((b) => b !== brand))}
              />
            ))}
            {selectedColors.map((color) => (
              <FilterPill
                key={color}
                label={color}
                onRemove={() => setSelectedColors(selectedColors.filter((c) => c !== color))}
              />
            ))}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Clear all
            </Button>
          </motion.div>
        )}

        {/* Main Content */}
        <div className="flex gap-8">
          {/* Filter Panel - Desktop */}
          {showFilters && (
            <motion.aside
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="hidden lg:block w-72 flex-shrink-0"
            >
              <FilterPanel
                selectedCategories={selectedCategories}
                setSelectedCategories={setSelectedCategories}
                priceRange={priceRange}
                setPriceRange={setPriceRange}
                selectedBrands={selectedBrands}
                setSelectedBrands={setSelectedBrands}
                selectedColors={selectedColors}
                setSelectedColors={setSelectedColors}
                inStockOnly={inStockOnly}
                setInStockOnly={setInStockOnly}
              />
            </motion.aside>
          )}

          {/* Product Grid */}
          <div className="flex-1">
            {fetchError && (
              <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive">
                <p>{fetchError}</p>
              </div>
            )}

            <ProductGrid products={sortedProducts} viewMode={viewMode} />

            {/* Load More Sentinel */}
            {hasMore && (
              <div ref={sentinelRef} className="flex justify-center py-8">
                {isLoadingMore && (
                  <div className="animate-spin h-6 w-6 border-2 border-accent border-t-transparent rounded-full" />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
