import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload, Search, Camera, Image as ImageIcon, Loader2, X, Sparkles, Tag } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ProductCard } from '@/components/product/ProductCard';
import { resolveImageUrl } from '@/lib/imageUrl';
import { safeImageSrc } from '@/lib/imageFallback';
import { toast } from 'sonner';
import type { Product } from '@/types';
import { useGender } from '@/context/GenderContext';
import { visualSearchService, type VisualSearchResponse } from '@/services/aiFeaturesService';

function toProduct(p: Record<string, unknown>): Product {
  return {
    id: String(p.id ?? ''),
    name: String(p.name ?? ''),
    brand: String(p.brand ?? ''),
    brandId: String(p.brandId ?? p.brand_id ?? ''),
    price: Number(p.price ?? 0),
    originalPrice: p.originalPrice != null ? Number(p.originalPrice) : undefined,
    currency: String(p.currency ?? 'USD'),
    category: (p.category as Product['category']) ?? 'tops',
    subcategory: String(p.subcategory ?? ''),
    images: Array.isArray(p.images)
      ? (p.images as unknown[]).map(resolveImageUrl).filter(Boolean)
      : p.image_url
        ? [resolveImageUrl(p.image_url)]
        : [],
    colors: Array.isArray(p.colors) ? (p.colors as string[]) : [],
    sizes: Array.isArray(p.sizes) ? (p.sizes as string[]) : ['S', 'M', 'L'],
    description: String(p.description ?? ''),
    styleCompatibility: Number(p.styleCompatibility ?? p.style_compatibility ?? 85),
    inStock: p.inStock !== false,
    tags: Array.isArray(p.tags) ? (p.tags as string[]) : [],
    gender: (p.gender as Product['gender']) ?? 'unisex',
  };
}

export default function VisualSearchPage() {
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<Product[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [detectedAttributes, setDetectedAttributes] = useState<VisualSearchResponse['attributes'] | null>(null);
  const [processingTime, setProcessingTime] = useState<number>(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const { selectedGender } = useGender();

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    setSelectedFile(file);

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setUploadedImage(dataUrl);
      setHasSearched(false);
      setResults([]);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleSearch = useCallback(async () => {
    if (!selectedFile) {
      toast.error('Please upload an image first');
      return;
    }

    setIsSearching(true);
    setHasSearched(true);

    try {
      // Use v1 SNAP & STYLE service
      const data = await visualSearchService.searchByImage(selectedFile, 20);

      setDetectedAttributes(data.attributes);
      setProcessingTime(data.processing_time_ms);

      let products: Product[] = data.matches.map((m) => toProduct({
        id: m.product_id,
        name: m.name,
        brand: m.brand,
        price: m.price,
        currency: m.currency,
        image_url: m.image_url,
        category: m.matched_attributes[0] || 'tops',
      }));

      // Gender filtering: men/women show only relevant + unisex
      if (selectedGender === 'men') {
        products = products.filter(p => p.gender === 'men' || p.gender === 'unisex');
      } else if (selectedGender === 'women') {
        products = products.filter(p => p.gender === 'women' || p.gender === 'unisex');
      }

      setResults(products);

      if (products.length === 0) {
        toast.info('No similar products found', {
          description: 'Try uploading a different image or adjusting your search.',
        });
      }
    } catch (error) {
      console.error('Visual search error:', error);
      toast.error('Search failed', {
        description: 'Unable to perform visual search. Please try again.',
      });
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [selectedFile, searchQuery, selectedGender]);

  const handleClear = useCallback(() => {
    setUploadedImage(null);
    setSelectedFile(null);
    setSearchQuery('');
    setResults([]);
    setHasSearched(false);
    setDetectedAttributes(null);
    setProcessingTime(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full mb-4">
              <Search className="h-4 w-4" />
              <span className="text-sm font-medium">AI-Powered Search</span>
            </div>
            <h1 className="heading-hero mb-4">Visual Search</h1>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Upload an image of clothing you like and find similar products from our catalog
            </p>
          </div>

          {/* Upload Area */}
          <div className="bg-card rounded-xl border border-border p-8 mb-8">
            {!uploadedImage ? (
              <div className="flex flex-col items-center justify-center py-12 border-2 border-dashed border-border rounded-lg">
                <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
                  <Upload className="h-8 w-8 text-accent" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Upload an Image</h3>
                <p className="text-sm text-muted-foreground mb-6">
                  Drag and drop an image here, or click to browse
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="image-upload"
                  title="Upload image file"
                />
                <Button
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  className="gap-2"
                >
                  <Camera className="h-4 w-4" />
                  Choose Image
                </Button>
                <Button
                  variant="outline"
                  onClick={() => cameraInputRef.current?.click()}
                  className="gap-2"
                >
                  <Camera className="h-4 w-4" />
                  Use Camera
                </Button>
                <input
                  ref={cameraInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleFileSelect}
                  className="hidden"
                  title="Take photo with camera"
                />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="relative inline-block">
                  <img
                    src={safeImageSrc(uploadedImage)}
                    alt="Uploaded"
                    className="max-w-full max-h-96 rounded-lg object-contain"
                    onError={(e) => {
                      e.currentTarget.src = safeImageSrc('');
                    }}
                  />
                  <button
                    onClick={handleClear}
                    className="absolute top-2 right-2 p-2 bg-background/90 rounded-full hover:bg-background transition-colors"
                    title="Remove image"
                    aria-label="Remove uploaded image"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="flex gap-3">
                  <Input
                    placeholder="Optional: describe what you're looking for..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    className="flex-1"
                  />
                  <Button
                    variant="hero"
                    onClick={handleSearch}
                    disabled={isSearching}
                    className="gap-2"
                  >
                    {isSearching ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4" />
                        Search
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Detected Attributes */}
          {detectedAttributes && hasSearched && (
            <div className="bg-card rounded-xl border border-border p-6 mb-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-accent" />
                <h3 className="font-semibold">AI Detected Attributes</h3>
                {processingTime > 0 && (
                  <span className="text-xs text-muted-foreground ml-auto">
                    {(processingTime / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {detectedAttributes.type && (
                  <Badge variant="secondary" className="gap-1">
                    <Tag className="h-3 w-3" />
                    {detectedAttributes.type}
                  </Badge>
                )}
                {detectedAttributes.color.map((c) => (
                  <Badge key={c} variant="outline" className="gap-1">
                    <span className="w-2 h-2 rounded-full bg-accent" />
                    {c}
                  </Badge>
                ))}
                {detectedAttributes.style.map((s) => (
                  <Badge key={s} variant="outline">{s}</Badge>
                ))}
                {detectedAttributes.pattern.map((p) => (
                  <Badge key={p} variant="outline">{p}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {hasSearched && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-semibold">
                  {isSearching ? 'Searching...' : `Found ${results.length} similar products`}
                </h2>
                {results.length > 0 && (
                  <Button variant="outline" onClick={handleClear} size="sm">
                    New Search
                  </Button>
                )}
              </div>

              {results.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
                  {results.map((product, index) => (
                    <ProductCard key={product.id} product={product} index={index} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-16">
                  <ImageIcon className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <p className="text-lg text-muted-foreground mb-2">No products found</p>
                  <p className="text-sm text-muted-foreground mb-6">
                    Try uploading a different image or adjusting your search query
                  </p>
                  <Button variant="outline" onClick={handleClear}>
                    Start Over
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
