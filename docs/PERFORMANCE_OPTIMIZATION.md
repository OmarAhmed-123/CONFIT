# CONFIT Performance Optimization Guide

**Target:** Lighthouse 95+ scores across all categories

---

## Implemented Optimizations

### 1. Frontend Bundle Optimization

#### Code Splitting & Lazy Loading
- **Location:** `@/src/App.tsx`, `@/src/components/lazy/LazyPage.tsx`
- All page components lazy-loaded with React.lazy()
- Suspense boundaries with loading skeletons
- Route-based chunk splitting

#### Vite Build Configuration
- **Location:** `@/vite.config.ts`
- Manual chunk splitting for vendor libraries
- Tree shaking enabled
- CSS code splitting
- Minification with esbuild
- Bundle analysis with rollup-plugin-visualizer

#### Chunk Strategy
```
vendor-react    → React, ReactDOM, Router
vendor-ui       → Radix UI components
vendor-query    → TanStack Query
vendor-motion   → Framer Motion
vendor-charts   → Recharts
vendor-utils    → Utility libraries
```

### 2. Image Optimization

#### OptimizedImage Component
- **Location:** `@/src/components/lazy/ImageOptimized.tsx`
- Intersection Observer for lazy loading
- Blur placeholder support
- Responsive images with srcset
- Priority loading for above-fold images

#### Image Best Practices
- WebP format with fallbacks
- Aspect ratio preservation (prevents CLS)
- Lazy loading with 200px root margin
- Async decoding for non-critical images

### 3. Server Caching

#### Redis Cache Layer
- **Location:** `@/backend/app/core/cache.py`
- Redis primary with in-memory fallback
- Compression for large payloads
- TTL management per data type
- Cache invalidation helpers

#### Cache Decorator
```python
@cached(ttl=CacheTTL.PRODUCTS_LIST, key_prefix="products")
async def get_products(category_id: str):
    ...
```

#### HTTP Caching
- **Location:** `@/backend/nginx/nginx.conf`
- Aggressive caching for static assets (1 year, immutable)
- API response caching for safe endpoints
- Cache-Control headers per content type

### 4. Database Optimization

#### Performance Indexes
- **Location:** `@/supabase/migrations/20260307_performance_indexes.sql`
- Composite indexes for common queries
- Partial indexes excluding soft-deleted rows
- Covering indexes to avoid table lookups
- Full-text search indexes

#### Key Indexes
```sql
-- Product listing optimization
idx_products_listing (category_id, brand_id, price_cents DESC)

-- User orders optimization
idx_orders_user_recent (user_id, created_at DESC)

-- Full-text search
idx_products_search USING gin(to_tsvector(...))
```

### 5. CDN Configuration

#### Nginx CDN-Like Behavior
- **Location:** `@/backend/nginx/nginx.conf`
- HTTP/2 enabled
- Gzip/Brotli compression
- Cache zones for API responses
- Open file cache for static assets

#### Recommended CDN Setup
```yaml
# CloudFront / Cloudflare / Fastly
Origin: https://api.confit.app
Edge Caching:
  - /assets/*     → 1 year, immutable
  - /api/products → 5 minutes
  - /api/search   → 2 minutes
  - /images/*     → 1 year, immutable
```

### 6. SEO Optimization

#### Meta Tags
- **Location:** `@/index.html`
- Open Graph tags
- Twitter Card tags
- Structured data (JSON-LD)
- Canonical URLs

#### Sitemap & Robots
- **Location:** `@/sitemap.xml`, `@/robots.txt`
- XML sitemap with all routes
- Robots.txt with crawl directives
- Dynamic sitemap generation for products

### 7. Accessibility

#### Accessibility Utilities
- **Location:** `@/src/utils/accessibility.ts`
- Focus trap for modals
- Skip links for keyboard navigation
- Screen reader announcements
- ARIA attribute helpers
- Reduced motion detection

#### WCAG 2.1 AA Compliance
- Color contrast ratios ≥ 4.5:1
- Focus indicators visible
- Keyboard navigation support
- Screen reader announcements
- Reduced motion respect

### 8. Performance Monitoring

#### Lighthouse CI
- **Location:** `@/.lighthouserc.yml`
- Automated performance testing
- Budget enforcement
- CI/CD integration

#### Performance Budgets
```yaml
Performance Score: ≥ 95
Accessibility Score: ≥ 95
SEO Score: ≥ 95
Best Practices Score: ≥ 95

Core Web Vitals:
  FCP: ≤ 1.5s
  LCP: ≤ 2.5s
  CLS: ≤ 0.1
  TBT: ≤ 200ms
  SI: ≤ 3.0s
```

---

## Running Performance Tests

### Build & Analyze
```bash
npm run build
npm run build:analyze  # Opens bundle analyzer
```

### Lighthouse CI
```bash
npm run lighthouse      # Full Lighthouse run
npm run lighthouse:collect
npm run lighthouse:assert
```

### Manual Lighthouse
```bash
# Chrome DevTools
1. Open DevTools (F12)
2. Go to Lighthouse tab
3. Select all categories
4. Run audit

# CLI
npx lighthouse http://localhost:8080 --view
```

---

## Performance Checklist

### Critical (Must Have)
- [x] Code splitting & lazy loading
- [x] Image optimization & lazy loading
- [x] Gzip/Brotli compression
- [x] Browser caching headers
- [x] Database indexes
- [x] Redis caching

### Important (Should Have)
- [x] CDN configuration
- [x] HTTP/2 enabled
- [x] Preconnect hints
- [x] Font optimization
- [x] CSS code splitting

### Nice to Have
- [ ] Service Worker (PWA)
- [ ] Critical CSS inlining
- [ ] Image CDN (Cloudinary/imgix)
- [ ] Server-side rendering

---

## Expected Scores

| Category | Target | Current |
|----------|--------|---------|
| Performance | 95+ | TBD |
| Accessibility | 95+ | TBD |
| SEO | 95+ | TBD |
| Best Practices | 95+ | TBD |

---

## Troubleshooting

### Low Performance Score
1. Check bundle size: `npm run build:analyze`
2. Review lazy loading: Ensure images use `ImageOptimized`
3. Check caching: Verify Redis connection
4. Review database: Run `EXPLAIN ANALYZE` on slow queries

### Low Accessibility Score
1. Run accessibility audit in DevTools
2. Check color contrast ratios
3. Verify ARIA attributes
4. Test keyboard navigation

### Low SEO Score
1. Verify meta tags in `index.html`
2. Check sitemap accessibility
3. Validate structured data
4. Review robots.txt

---

## Next Steps

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Run database migrations:**
   ```bash
   supabase db push
   ```

3. **Build and test:**
   ```bash
   npm run build
   npm run lighthouse
   ```

4. **Deploy with CDN:**
   - Configure CloudFront/Cloudflare
   - Set up SSL certificates
   - Enable HTTP/2

---

## Files Modified/Created

### Frontend
- `vite.config.ts` - Build optimization
- `src/App.tsx` - Lazy loading
- `src/components/lazy/LazyPage.tsx` - Lazy components
- `src/utils/accessibility.ts` - A11y utilities
- `index.html` - SEO & performance hints
- `sitemap.xml` - SEO sitemap
- `robots.txt` - Crawl directives
- `.lighthouserc.yml` - Lighthouse CI config

### Backend
- `backend/app/core/cache.py` - Redis caching
- `backend/nginx/nginx.conf` - CDN & caching
- `supabase/migrations/20260307_performance_indexes.sql` - DB indexes

---

**Last Updated:** March 2026
**Version:** 1.0.0
