'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/layout';
import { api, APIError } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { ProductCard } from '@/components/product/ProductCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, SlidersHorizontal, X } from 'lucide-react';
import type { Product } from '@/types';

export default function ProductsPage() {
  const searchParams = useSearchParams();
  const gender = searchParams?.get('gender') || null;
  const category = searchParams?.get('category') || null;
  const brand = searchParams?.get('brand') || null;
  const q = searchParams?.get('q') || null;

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState(q || '');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (gender) params.append('gender', gender);
        if (category) params.append('category', category);
        if (brand) params.append('brand', brand);
        if (q) params.append('q', q);

        const queryString = params.toString();
        const endpoint = queryString 
          ? `${API_ENDPOINTS.PRODUCTS.LIST}?${queryString}`
          : API_ENDPOINTS.PRODUCTS.LIST;

        const data = await api.get<Product[]>(endpoint);
        // Transform products to match ProductCard expected format
        const transformedProducts = (Array.isArray(data) ? data : []).map((p): Product => ({
          ...p,
          originalPrice: p.originalPrice,
          inStock: p.inStock ?? true,
          styleCompatibility: p.styleCompatibility || p.style_compatibility || 75,
          currency: p.currency || 'USD',
        }));
        setProducts(transformedProducts);
      } catch (err) {
        if (err instanceof APIError) {
          setError(err.detail || err.message);
        } else {
          setError('Failed to load products');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, [gender, category, brand, q]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      const params = new URLSearchParams();
      if (gender) params.append('gender', gender);
      if (searchQuery.trim()) params.append('q', searchQuery.trim());
      window.location.href = `/products?${params.toString()}`;
    }
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
        </div>
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>Try Again</Button>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-display font-bold">
              {gender ? `${gender.charAt(0).toUpperCase() + gender.slice(1)}'s Products` : 'All Products'}
            </h1>
            <p className="text-muted-foreground mt-1">
              {products.length} {products.length === 1 ? 'product' : 'products'} found
            </p>
          </div>

          {/* Search & Filter */}
          <div className="flex items-center gap-3">
            <form onSubmit={handleSearch} className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search products..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 w-64"
              />
            </form>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setShowFilters(!showFilters)}
            >
              <SlidersHorizontal className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Active Filters */}
        {(gender || category || brand || q) && (
          <div className="flex flex-wrap gap-2 mb-6">
            {gender && (
              <Button variant="secondary" size="sm" className="gap-1">
                Gender: {gender}
                <X className="h-3 w-3" onClick={() => window.location.href = '/products'} />
              </Button>
            )}
            {category && (
              <Button variant="secondary" size="sm" className="gap-1">
                Category: {category}
                <X className="h-3 w-3" onClick={() => window.location.href = '/products'} />
              </Button>
            )}
            {brand && (
              <Button variant="secondary" size="sm" className="gap-1">
                Brand: {brand}
                <X className="h-3 w-3" onClick={() => window.location.href = '/products'} />
              </Button>
            )}
            {q && (
              <Button variant="secondary" size="sm" className="gap-1">
                Search: {q}
                <X className="h-3 w-3" onClick={() => window.location.href = '/products'} />
              </Button>
            )}
          </div>
        )}

        {/* Products Grid */}
        {products.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No products found</p>
            <Button variant="link" onClick={() => window.location.href = '/products'}>
              Clear filters
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
