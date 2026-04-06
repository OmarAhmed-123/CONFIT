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
    products, // raw products (for count)
    sortedProducts, // filtered & sorted
    // isLoading,
    fetchError,
    searchQuery,
    setSearchQuery,
    isDebouncing,
    // filters
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
          <AnimatedSection className="mb-6">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">Active filters:</span>
            {selectedCategories.map((cat) => (
              <FilterPill
                key={cat}
                label={cat}
                onRemove={() => setSelectedCategories(prev => prev.filter(c => c !== cat))}
              />
            ))}
            {selectedBrands.map((brand) => (
              <FilterPill
                key={brand}
                label={brand}
                onRemove={() => setSelectedBrands(prev => prev.filter(b => b !== brand))}
              />
            ))}
            {selectedColors.map((color) => (
              <FilterPill
                key={color}
                label={color}
                onRemove={() => setSelectedColors(prev => prev.filter(c => c !== color))}
              />
            ))}
            {(priceRange.min > 0 || priceRange.max < 1000) && (
              <FilterPill
                label={`$${priceRange.min} - $${priceRange.max}`}
                onRemove={() => setPriceRange({ min: 0, max: 1000 })}
              />
            )}
            {inStockOnly && (
              <FilterPill
                label="In Stock Only"
                onRemove={() => setInStockOnly(false)}
              />
            )}
            <button
              onClick={clearAllFilters}
              className="text-sm text-accent hover:underline"
            >
              Clear all
            </button>
          </div>
          </AnimatedSection>
        )}

        {/* Main Content */}
        <div className="flex gap-8">
          {/* Filter Panel */}
          {showFilters && (
            <motion.aside
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="hidden md:block w-64 shrink-0"
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
            {/* Results Count */}
            <p className="text-sm text-muted-foreground mb-6">
              {fetchError ? (
                <span className="text-destructive">{fetchError}</span>
              ) : (
                <>
                  Showing {sortedProducts.length} of {products.length} products
                  {searchQuery && ` for "${searchQuery}"`}
                </>
              )}
            </p>

            {sortedProducts.length > 0 ? (
              <ProductGrid products={sortedProducts} viewMode={viewMode} />
            ) : (
              <div className="text-center py-16">
                <p className="text-lg text-muted-foreground mb-4">
                  No products found matching your criteria
                </p>
                <Button variant="outline" onClick={clearAllFilters}>
                  Clear filters
                </Button>
              </div>
            )}

            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} className="h-1" />
            {isLoadingMore && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
                className="py-6 text-center"
              >
                <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="inline-block w-2.5 h-2.5 rounded-full bg-accent animate-pulse" />
                  Loading more…
                </div>
              </motion.div>
            )}
            {!hasMore && sortedProducts.length > 0 && (
              <div className="py-10 text-center text-sm text-muted-foreground">That&apos;s everything.</div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

// FilterPill extracted into shared component.
