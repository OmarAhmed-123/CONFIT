/**
 * VirtualTryOn — Try-on studio
 *
 * "Photo ready" state matches Lovable: solid dark stage, large center image, minimal chrome.
 * Processing: TryOnViewModel → FastAPI; optional local session thumbnails.
 */

import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { Camera, RotateCcw, ChevronLeft, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { MainLayout } from '@/components/layout';
import { PhotoUploadArea } from '@/components/try-on/PhotoUploadArea';
import { ProductSelector } from '@/components/try-on/ProductSelector';
import { TryOnResultPanel } from '@/components/try-on/TryOnResultPanel';
import { RotationViewer } from '@/components/try-on/RotationViewer';
import { GarmentSwitcher } from '@/components/try-on/GarmentSwitcher';
import { TryOnAmbientBackground } from '@/components/try-on/TryOnAmbientBackground';
import { TryOnStepRail } from '@/components/try-on/TryOnStepRail';
import { TryOnRecentSessions } from '@/components/try-on/TryOnRecentSessions';
import { useTryOnViewModel } from '@/viewmodels/TryOnViewModel';
import { useRotationViewModel } from '@/viewmodels/RotationViewModel';
import { useRouter } from 'next/navigation';
import { useCart } from '@/context/CartContext';
import { apiUrl } from '@/lib/api';
import { unwrapApiData } from '@/lib/api/envelope';
import { resolveImageUrl } from '@/lib/imageUrl';
import { listTryOnSessions } from '@/lib/tryOnLocalSessions';
import type { TryOnLocalSessionEntry } from '@/lib/tryOnLocalSessions';
import type { Product } from '@/types';
import { useGender } from '@/context/GenderContext';
import { getFeaturedProducts } from '@/services/mockData';
import { cn } from '@/lib/utils';
import { CATEGORY_IMAGE_FALLBACK } from '@/lib/productImages';

type ViewMode = 'upload' | 'result' | 'rotation';

type TryOnDiagnosticsPayload = {
  preview_available?: boolean;
  final_render_available?: boolean;
  active_backend?: string;
  backend_priority?: string[];
  failure_reason?: string | null;
  details?: Record<string, unknown>;
};

function normalizeProductGender(value: unknown): Product['gender'] {
  const normalized = String(value ?? '').toLowerCase().trim();
  if (['men', 'male', 'man', 'boys'].includes(normalized)) return 'men';
  if (['women', 'female', 'woman', 'girls', 'ladies'].includes(normalized)) return 'women';
  if (['unisex', 'all', 'any'].includes(normalized)) return 'unisex';
  return 'unisex';
}

function toProduct(p: Record<string, unknown>): Product {
  const cat = (p.category as Product['category']) ?? 'tops';
  let images: string[] = Array.isArray(p.images)
    ? (p.images as unknown[]).map(resolveImageUrl).filter(Boolean)
    : p.image_url
      ? [resolveImageUrl(p.image_url)]
      : [];
  if (images.length === 0) {
    const fb = CATEGORY_IMAGE_FALLBACK[cat] ?? CATEGORY_IMAGE_FALLBACK.tops;
    images = [fb];
  }
  return {
    id: String(p.id ?? ''),
    name: String(p.name ?? ''),
    brand: String(p.brand ?? ''),
    brandId: String(p.brandId ?? p.brand_id ?? ''),
    price: Number(p.price ?? 0),
    originalPrice: p.originalPrice != null ? Number(p.originalPrice) : undefined,
    currency: String(p.currency ?? 'USD'),
    category: cat,
    subcategory: String(p.subcategory ?? ''),
    images,
    colors: Array.isArray(p.colors) ? (p.colors as string[]) : [],
    sizes: Array.isArray(p.sizes) ? (p.sizes as string[]) : ['S', 'M', 'L'],
    description: String(p.description ?? ''),
    styleCompatibility: Number(p.styleCompatibility ?? p.style_compatibility ?? 85),
    inStock: p.inStock !== false,
    tags: Array.isArray(p.tags) ? (p.tags as string[]) : [],
    gender: normalizeProductGender(p.gender ?? p.target_gender),
  };
}

export default function VirtualTryOn() {
  const router = useRouter();
  const { selectedGender } = useGender();
  const { addToCart } = useCart();

  const tryOn = useTryOnViewModel();
  const rotation = useRotationViewModel();

  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);

  const [localSessions, setLocalSessions] = useState<TryOnLocalSessionEntry[]>(() =>
    listTryOnSessions()
  );
  const [diagnostics, setDiagnostics] = useState<TryOnDiagnosticsPayload | null>(null);
  const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false);
  const [adminTokenInput, setAdminTokenInput] = useState('');
  const [fashnKeyInput, setFashnKeyInput] = useState('');
  const [persistKey, setPersistKey] = useState(false);
  const [isSavingFashnKey, setIsSavingFashnKey] = useState(false);
  const [fashnConfigMessage, setFashnConfigMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort('FEATURED_PRODUCTS_TIMEOUT'), 20000);
    setProductsLoading(true);
    setApiError(null);

    const url = apiUrl(`/api/products/featured?limit=12&gender=${selectedGender || ''}`);

    fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      signal: controller.signal,
    })
      .then(async (res) => {
        if (res.status === 307) {
          const redirectUrl = res.headers.get('Location');
          if (redirectUrl) {
            return fetch(redirectUrl, {
              method: 'GET',
              headers: { Accept: 'application/json' },
            });
          }
        }
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res;
      })
      .then((res) => res?.json())
      .then((payload: unknown) => {
        if (cancelled) return;
        const data = unwrapApiData<unknown>(payload);
        const list = Array.isArray(data)
          ? data.map((p) => toProduct(p as Record<string, unknown>))
          : [];
        if (list.length > 0) {
          setProducts(list);
        } else {
          setProducts(getFeaturedProducts(12));
        }
      })
      .catch((error) => {
        if (!cancelled) {
          if (error instanceof DOMException && error.name === 'AbortError') {
            setApiError('Loading products took too long. Showing curated fallback list.');
          } else {
            setApiError(error instanceof Error ? error.message : 'Failed to load products');
          }
          setProducts(getFeaturedProducts(12));
        }
      })
      .finally(() => {
        clearTimeout(timeoutId);
        if (!cancelled) setProductsLoading(false);
      });
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      controller.abort('COMPONENT_UNMOUNT');
    };
  }, [selectedGender]);

  useEffect(() => {
    setLocalSessions(listTryOnSessions());
  }, [tryOn.resultImage]);

  useEffect(() => {
    let cancelled = false;
    const fetchDiagnostics = async () => {
      try {
        setDiagnosticsError(null);
        const res = await fetch(apiUrl('/api/virtual-tryon/diagnostics'));
        if (!res.ok) return;
        const payload = await res.json();
        const data = unwrapApiData<TryOnDiagnosticsPayload>(payload);
        if (!cancelled) setDiagnostics(data);
      } catch {
        // Keep UI non-blocking; diagnostics are optional.
        if (!cancelled) setDiagnosticsError('Could not refresh diagnostics right now.');
      }
    };
    void fetchDiagnostics();
    return () => {
      cancelled = true;
    };
  }, []);

  const [userImage, setUserImage] = useState<string | null>(null);
  const [userImageFile, setUserImageFile] = useState<File | null>(null);
  const [selectedProductIndex, setSelectedProductIndex] = useState(0);
  const [selectedSize, setSelectedSize] = useState('M');
  const [viewMode, setViewMode] = useState<ViewMode>('upload');

  const filteredProducts = products.filter(
    (p) => p.gender === 'unisex' || p.gender === selectedGender
  );
  const selectedProduct =
    filteredProducts[selectedProductIndex] ??
    filteredProducts[0] ??
    getFeaturedProducts(1)[0];

  useEffect(() => {
    const first = selectedProduct?.sizes?.[0];
    if (first) setSelectedSize(first);
  }, [selectedProduct?.id, selectedProduct?.sizes]);

  /** Lovable-style: photo loaded, choosing garment / waiting for preview */
  const immersivePhase = Boolean(userImage && viewMode === 'upload');

  const railStep: 1 | 2 | 3 = !userImage
    ? 1
    : tryOn.resultImage || viewMode === 'result' || viewMode === 'rotation'
      ? 3
      : 2;

  const handleFileSelect = useCallback(
    (file: File) => {
      setUserImageFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        if (result) {
          setUserImage(result);
          tryOn.reset();
          rotation.reset();
          setViewMode('upload');
        }
      };
      reader.readAsDataURL(file);
    },
    [tryOn, rotation]
  );

  const handleTryOn = useCallback(async () => {
    if (!userImage || !selectedProduct) return;

    // Try v1 MIRROR service first (requires raw File + product variant ID)
    if (userImageFile) {
      try {
        const success = await tryOn.processMirrorTryOn(
          userImageFile,
          selectedProduct.id,
          selectedProduct.category === 'bottoms' ? 'lower_body' : 'upper_body',
          { id: selectedProduct.id, name: selectedProduct.name }
        );
        if (success) {
          setViewMode('result');
          return;
        }
      } catch {
        // Fall back to legacy pipeline
      }
    }

    // Legacy pipeline (base64 image + garment URL)
    const success = await tryOn.processVirtualTryOn(
      userImage,
      selectedProduct.images[0],
      selectedProduct.name,
      selectedProduct.category,
      { id: selectedProduct.id, name: selectedProduct.name }
    );

    if (success) {
      setViewMode('result');
    }
  }, [userImage, userImageFile, selectedProduct, tryOn]);

  const handleSelectProduct = useCallback((index: number) => {
    setSelectedProductIndex(index);
  }, []);

  const handleView360 = useCallback(async () => {
    const img = tryOn.resultImage || userImage;
    if (!img) return;

    setViewMode('rotation');
    await rotation.generateRotation(img);
  }, [tryOn.resultImage, userImage, rotation]);

  const handleBackToResult = useCallback(() => {
    rotation.reset();
    setViewMode('result');
  }, [rotation]);

  const handleStartOver = useCallback(() => {
    setUserImage(null);
    setUserImageFile(null);
    tryOn.reset();
    rotation.reset();
    setViewMode('upload');
  }, [tryOn, rotation]);

  const handleAddToCart = useCallback(() => {
    if (!selectedProduct) return;
    const color = selectedProduct.colors?.[0] ?? '';
    addToCart(selectedProduct, 1, selectedSize, color);
    router.push('/cart');
  }, [selectedProduct, selectedSize, addToCart, router]);

  const handleSaveLook = useCallback(() => {
    if (typeof window !== 'undefined' && selectedProduct) {
      sessionStorage.setItem(
        'confit_tryon_outfit_seed',
        JSON.stringify({ fromTryOn: true, product: selectedProduct })
      );
    }
    router.push('/outfits');
  }, [router, selectedProduct]);

  const refreshLocalSessions = useCallback(() => {
    setLocalSessions(listTryOnSessions());
  }, []);

  const refreshDiagnostics = useCallback(async () => {
    try {
      setDiagnosticsError(null);
      const res = await fetch(apiUrl('/api/virtual-tryon/diagnostics'));
      if (!res.ok) {
        setDiagnosticsError(`Diagnostics HTTP ${res.status}`);
        return;
      }
      const payload = await res.json();
      const data = unwrapApiData<TryOnDiagnosticsPayload>(payload);
      setDiagnostics(data);
    } catch {
      setDiagnosticsError('Could not refresh diagnostics right now.');
    }
  }, []);

  const handleSaveFashnKey = useCallback(async () => {
    if (!adminTokenInput.trim()) {
      setFashnConfigMessage('Admin token is required.');
      return;
    }
    if (!fashnKeyInput.trim()) {
      setFashnConfigMessage('FASHN_API_KEY is required.');
      return;
    }
    setIsSavingFashnKey(true);
    setFashnConfigMessage(null);
    try {
      const res = await fetch(apiUrl('/api/virtual-tryon/config/fashn-key'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-TryOn-Admin-Token': adminTokenInput.trim(),
        },
        body: JSON.stringify({
          apiKey: fashnKeyInput.trim(),
          persistToEnv: persistKey,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      const data = unwrapApiData<{ configured?: boolean; fashnAvailable?: boolean }>(payload);
      if (!res.ok || payload?.success === false) {
        const err = payload?.error || payload?.detail || `HTTP ${res.status}`;
        setFashnConfigMessage(`Failed to configure key: ${String(err)}`);
        return;
      }
      const isReady = Boolean(data?.configured && data?.fashnAvailable);
      setFashnConfigMessage(
        isReady
          ? 'FASHN key configured successfully and backend is ready.'
          : 'Key saved, but backend still not ready. Re-check diagnostics.'
      );
      setFashnKeyInput('');
      setAdminTokenInput('');
      await refreshDiagnostics();
    } catch {
      setFashnConfigMessage('Failed to configure key due to network/server error.');
    } finally {
      setIsSavingFashnKey(false);
    }
  }, [adminTokenInput, fashnKeyInput, persistKey, refreshDiagnostics]);

  const productColumn = (
    <>
      <ProductSelector
        products={filteredProducts}
        selectedIndex={selectedProductIndex}
        onSelectProduct={handleSelectProduct}
        onTryOn={handleTryOn}
        canTryOn={!!userImage && !tryOn.isProcessing}
        isProcessing={tryOn.isProcessing}
        selectedSize={selectedSize}
        onSizeChange={setSelectedSize}
      />
      <GarmentSwitcher
        products={filteredProducts}
        selectedIndex={selectedProductIndex}
        onSelect={handleSelectProduct}
        isProcessing={tryOn.isProcessing}
      />
    </>
  );

  const diagnosticsPanel = (
    <div className="mb-4 rounded-xl border border-border/70 bg-card/50 p-3 text-xs text-muted-foreground">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-foreground">Try-on diagnostics</p>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={refreshDiagnostics}>
            Refresh
          </Button>
          <Button size="sm" onClick={() => setIsConfigDialogOpen(true)}>
            Configure FASHN key
          </Button>
        </div>
      </div>
      <p className="mt-1">
        preview:
        {' '}
        {diagnostics?.preview_available ? 'available' : 'unavailable'}
        {' · '}final:
        {' '}
        {diagnostics?.final_render_available ? 'available' : 'unavailable'}
      </p>
      <p className="mt-1">
        last backend:
        {' '}
        {tryOn.lastBackendUsed || 'n/a'}
        {' · '}
        last failure_kind:
        {' '}
        {tryOn.lastFailureKind || 'n/a'}
      </p>
      <p className="mt-1">
        active backend:
        {' '}
        {diagnostics?.active_backend || 'n/a'}
        {' · '}
        policy: free-first
      </p>
      {!diagnostics?.final_render_available &&
        diagnostics?.failure_reason && (
          <p className="mt-1 text-[11px]">
            {diagnostics.failure_reason}
          </p>
        )}
      {tryOn.finalNotice && (
        <p className="mt-2 rounded-md border border-blue-400/30 bg-blue-500/10 px-2 py-1 text-[11px] text-blue-300">
          {tryOn.finalNotice}
        </p>
      )}
      {diagnostics?.backend_priority && (
        <p className="mt-1 text-[11px]">priority: {diagnostics.backend_priority.join(' -> ')}</p>
      )}
      {diagnosticsError && <p className="mt-1 text-[11px] text-amber-500">{diagnosticsError}</p>}
    </div>
  );

  return (
    <MainLayout
      hideFooter={immersivePhase}
      className={cn(immersivePhase && 'bg-[hsl(220_25%_8%)]')}
    >
      <div
        className={cn(
          'relative min-h-[calc(100vh-5rem)] overflow-hidden',
          immersivePhase && 'bg-[hsl(220_25%_8%)]'
        )}
      >
        {!immersivePhase && <TryOnAmbientBackground />}

        <div
          className={cn(
            'relative z-10 mx-auto max-w-7xl px-4 pb-16 pt-6 md:px-6 md:pt-8',
            immersivePhase && 'max-w-6xl pt-4'
          )}
        >
          {!immersivePhase && (
            <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div className="flex items-start gap-3">
                <Button
                  variant="ghost"
                  size="icon"
                  className="mt-0.5 shrink-0 rounded-full"
                  onClick={() => router.back()}
                >
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <div>
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/50 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur-md"
                  >
                    <Sparkles className="h-3.5 w-3.5 text-accent" />
                    Studio · Virtual fitting
                  </motion.div>
                  <h1 className="mt-3 font-playfair text-3xl font-semibold tracking-tight md:text-4xl">
                    Try it on
                  </h1>
                  <p className="mt-2 max-w-xl text-base text-muted-foreground md:text-lg">
                    Upload a photo, pick a garment, and preview — the same focused layout as your
                    reference build.
                  </p>
                  <Link
                    href="/try-on/live"
                    className="mt-4 inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/40 px-4 py-2 text-sm font-medium text-foreground backdrop-blur-sm transition-colors hover:bg-card/70"
                  >
                    <Camera className="h-4 w-4 text-primary" />
                    Live AR fitting (camera)
                  </Link>
                </div>
              </div>
              {userImage && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStartOver}
                  className="shrink-0 gap-2 rounded-full border-border/80"
                >
                  <Camera className="h-4 w-4" />
                  New photo
                </Button>
              )}
            </div>
          )}

          {immersivePhase && (
            <div className="mb-6 flex items-center justify-between gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="text-white/85 hover:bg-white/10 hover:text-white"
                onClick={() => router.back()}
              >
                <ChevronLeft className="h-5 w-5" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 rounded-full text-white/85 hover:bg-white/10 hover:text-white"
                onClick={handleStartOver}
              >
                <Camera className="h-4 w-4" />
                New photo
              </Button>
            </div>
          )}

          {apiError && (
            <p className="mb-6 text-sm text-amber-600 dark:text-amber-400">{apiError}</p>
          )}
          {productsLoading && (
            <p className="mb-6 text-sm text-muted-foreground">Loading catalog…</p>
          )}

          {!immersivePhase && <TryOnStepRail step={railStep} />}
          {diagnosticsPanel}

          {immersivePhase ? (
            <div className="dark space-y-10">
              <PhotoUploadArea
                userImage={userImage}
                resultImage={tryOn.resultImage}
                isProcessing={tryOn.isProcessing}
                error={tryOn.error}
                stageLabel={tryOn.stageLabel}
                selectedProduct={selectedProduct}
                onFileSelect={handleFileSelect}
                onReset={handleStartOver}
                onAddToCart={handleAddToCart}
                onSaveLook={handleSaveLook}
                layout="immersive"
                previewOnly={Boolean(tryOn.finalNotice)}
              />
              <div className="border-t border-white/[0.06] pt-8">{productColumn}</div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 lg:gap-10">
              <div className="space-y-4">
                <AnimatePresence mode="wait">
                  {viewMode === 'rotation' ? (
                    <motion.div
                      key="rotation"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                    >
                      <div className="mb-3 flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleBackToResult}
                          className="gap-1 rounded-full"
                        >
                          <ChevronLeft className="h-4 w-4" />
                          Back
                        </Button>
                        <span className="flex items-center gap-1 text-sm text-muted-foreground">
                          <RotateCcw className="h-3.5 w-3.5" />
                          360°
                        </span>
                      </div>
                      <RotationViewer
                        frames={rotation.frames}
                        currentIndex={rotation.currentIndex}
                        currentAngleDeg={rotation.currentAngleDeg}
                        isLoading={rotation.isLoading}
                        isAutoPlaying={rotation.isAutoPlaying}
                        onRotateBy={rotation.rotateBy}
                        onToggleAutoPlay={rotation.toggleAutoPlay}
                      />
                    </motion.div>
                  ) : viewMode === 'result' && tryOn.resultImage && selectedProduct ? (
                    <motion.div
                      key="result"
                      initial={{ opacity: 0, scale: 0.98 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.98 }}
                    >
                      <TryOnResultPanel
                        resultImage={tryOn.resultImage}
                        originalImage={userImage || ''}
                        productName={selectedProduct.name}
                        onView360={handleView360}
                        is360Loading={rotation.isLoading}
                      />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="upload"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <PhotoUploadArea
                        userImage={userImage}
                        resultImage={tryOn.resultImage}
                        isProcessing={tryOn.isProcessing}
                        error={tryOn.error}
                        stageLabel={tryOn.stageLabel}
                        selectedProduct={selectedProduct}
                        onFileSelect={handleFileSelect}
                        onReset={handleStartOver}
                        onAddToCart={handleAddToCart}
                        onSaveLook={handleSaveLook}
                        layout="default"
                        previewOnly={Boolean(tryOn.finalNotice)}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="space-y-4">{productColumn}</div>
            </div>
          )}

          {!immersivePhase && (
            <>
              <TryOnRecentSessions sessions={localSessions} onRefresh={refreshLocalSessions} />

              <nav
                className="mt-12 flex flex-wrap gap-3 border-t border-border/60 pt-8 text-sm"
                aria-label="Continue shopping"
              >
                <span className="w-full text-muted-foreground">Continue exploring</span>
                <Link
                  href="/discover"
                  className="rounded-full border border-border bg-card/50 px-4 py-2 font-medium backdrop-blur-sm transition-colors hover:border-accent/50 hover:text-accent"
                >
                  Discover
                </Link>
                <Link
                  href="/stylist"
                  className="rounded-full border border-border bg-card/50 px-4 py-2 font-medium backdrop-blur-sm transition-colors hover:border-accent/50 hover:text-accent"
                >
                  Stylist
                </Link>
                <Link
                  href="/cart"
                  className="rounded-full border border-border bg-card/50 px-4 py-2 font-medium backdrop-blur-sm transition-colors hover:border-accent/50 hover:text-accent"
                >
                  Cart
                </Link>
              </nav>
            </>
          )}
        </div>
      </div>
      <Dialog open={isConfigDialogOpen} onOpenChange={setIsConfigDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configure FASHN_API_KEY</DialogTitle>
            <DialogDescription>
              This writes the key through a protected backend endpoint using an admin token.
              Token is kept in-memory only in this page.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="tryon-admin-token">Admin token</Label>
              <Input
                id="tryon-admin-token"
                type="password"
                value={adminTokenInput}
                onChange={(e) => setAdminTokenInput(e.target.value)}
                placeholder="X-TryOn-Admin-Token"
                autoComplete="off"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="fashn-api-key">FASHN API key</Label>
              <Input
                id="fashn-api-key"
                type="password"
                value={fashnKeyInput}
                onChange={(e) => setFashnKeyInput(e.target.value)}
                placeholder="sk_..."
                autoComplete="off"
              />
            </div>

            <div className="flex items-center justify-between rounded-md border border-border/70 px-3 py-2">
              <Label htmlFor="persist-fashn-key">Persist to backend .env</Label>
              <Switch
                id="persist-fashn-key"
                checked={persistKey}
                onCheckedChange={setPersistKey}
              />
            </div>

            {fashnConfigMessage && (
              <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                {fashnConfigMessage}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsConfigDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveFashnKey} disabled={isSavingFashnKey}>
              {isSavingFashnKey ? 'Saving...' : 'Save key'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
