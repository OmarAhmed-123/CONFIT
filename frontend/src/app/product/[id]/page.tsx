'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { MainLayout } from '@/components/layout';
import { api, APIError } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { useAuth } from '@/context/AuthContext';
import { useCart } from '@/context/CartContext';
import { Button } from '@/components/ui/button';
import { ArrowLeft, ShoppingCart, Heart, Share2, Star, Truck, Shield, RefreshCw, MapPinned, MessageCircle, Radio, Users } from 'lucide-react';
import { toast } from 'sonner';
import { safeImageSrc } from '@/lib/imageFallback';
import type { Product as CatalogProduct } from '@/types';

interface ProductApi {
  id: string;
  name: string;
  description: string;
  price: number;
  original_price?: number;
  originalPrice?: number;
  images: string[];
  image_url?: string;
  category: string;
  brand?: string | { name?: string };
  brand_id?: string;
  brandId?: string;
  sizes?: string[];
  size?: string;
  colors?: string[];
  color?: string;
  in_stock: boolean;
  inStock?: boolean;
  gender?: CatalogProduct['gender'];
  rating?: number;
  reviews_count?: number;
}

function normalizeProduct(data: ProductApi): ProductApi {
  const images = Array.isArray(data.images)
    ? data.images.filter(Boolean)
    : data.image_url
      ? [data.image_url]
      : [];
  return {
    ...data,
    images,
    sizes: Array.isArray(data.sizes) && data.sizes.length ? data.sizes : data.size ? [data.size] : ['M'],
    colors: Array.isArray(data.colors) && data.colors.length ? data.colors : data.color ? [data.color] : ['Default'],
    in_stock: data.in_stock ?? data.inStock ?? true,
    original_price: data.original_price ?? data.originalPrice,
  };
}

function toCartProduct(product: ProductApi): CatalogProduct {
  const brandName = typeof product.brand === 'string' ? product.brand : product.brand?.name;
  return {
    id: product.id,
    name: product.name,
    description: product.description,
    category: product.category,
    price: Number(product.price || 0),
    currency: 'USD',
    brand: brandName || '',
    brand_id: product.brand_id,
    brandId: product.brandId ?? product.brand_id,
    images: product.images,
    image_url: product.images[0],
    colors: product.colors,
    sizes: product.sizes,
    inStock: product.in_stock,
    originalPrice: product.original_price,
    gender: product.gender ?? 'unisex',
  };
}

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { addToCart } = useCart();
  const [product, setProduct] = useState<ProductApi | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSize, setSelectedSize] = useState<string>('');
  const [selectedColor, setSelectedColor] = useState<string>('');
  const [quantity, setQuantity] = useState(1);
  const productId = params?.id ?? '';

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const data = normalizeProduct(await api.get<ProductApi>(API_ENDPOINTS.PRODUCTS.DETAIL(productId)));
        setProduct(data);
        if (data.sizes?.length) setSelectedSize(data.sizes[0]);
        if (data.colors?.length) setSelectedColor(data.colors[0]);
      } catch (err) {
        if (err instanceof APIError) {
          setError(err.detail || err.message);
        } else {
          setError('Failed to load product');
        }
      } finally {
        setLoading(false);
      }
    };

    if (productId) {
      fetchProduct();
    }
  }, [productId]);

  const handleAddToCart = async () => {
    if (!isAuthenticated) {
      router.push(`/login?redirect=${encodeURIComponent(`/product/${productId}`)}`);
      return;
    }
    if (!product) return;
    addToCart(
      toCartProduct(product),
      quantity,
      selectedSize || product.sizes?.[0] || 'One Size',
      selectedColor || product.colors?.[0] || 'Default'
    );
    toast.success('Added to cart', {
      description: `${product.name} is ready for checkout.`,
    });
    router.push('/cart');
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

  if (error || !product) {
    return (
      <MainLayout>
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
          <p className="text-muted-foreground">{error || 'Product not found'}</p>
          <Button onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </div>
      </MainLayout>
    );
  }

  const discount = product.original_price 
    ? Math.round((1 - product.price / product.original_price) * 100) 
    : 0;
  const socialProofCount = Math.max(product.reviews_count || 0, 24);
  const liveViewerCount = Math.max(Math.round((product.rating || 4.5) * 16), 18);
  const brandName = typeof product.brand === 'string' ? product.brand : product.brand?.name || 'CONFIT';

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <button 
          onClick={() => router.back()} 
          className="flex items-center text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to shopping
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
          {/* Product Images */}
          <div className="space-y-4">
            <div className="aspect-square rounded-2xl overflow-hidden bg-muted">
              {product.images?.[0] ? (
                <img
                  src={safeImageSrc(product.images[0])}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                  No image available
                </div>
              )}
            </div>
            {product.images && product.images.length > 1 && (
              <div className="grid grid-cols-4 gap-2">
                {product.images.slice(1, 5).map((img, idx) => (
                  <div key={idx} className="aspect-square rounded-lg overflow-hidden bg-muted cursor-pointer hover:ring-2 hover:ring-accent">
                    <img src={safeImageSrc(img)} alt={`${product.name} ${idx + 2}`} className="w-full h-full object-cover" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Product Info */}
          <div className="space-y-6">
            <div>
              <p className="text-sm text-accent font-medium mb-2">{brandName}</p>
              <h1 className="text-3xl font-bold tracking-tight">{product.name}</h1>
            </div>

            {/* Rating */}
            {product.rating && (
              <div className="flex items-center gap-2">
                <div className="flex items-center">
                  {[...Array(5)].map((_, i) => (
                    <Star 
                      key={i} 
                      className={`h-4 w-4 ${i < Math.floor(product.rating!) ? 'text-yellow-500 fill-yellow-500' : 'text-muted'}`}
                    />
                  ))}
                </div>
                <span className="text-sm text-muted-foreground">
                  ({product.reviews_count || 0} reviews)
                </span>
              </div>
            )}

            {/* Price */}
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-bold">${product.price.toFixed(2)}</span>
              {product.original_price && (
                <>
                  <span className="text-lg text-muted-foreground line-through">
                    ${product.original_price.toFixed(2)}
                  </span>
                  <span className="text-sm font-medium text-green-500">
                    {discount}% OFF
                  </span>
                </>
              )}
            </div>

            {/* Description */}
            <p className="text-muted-foreground leading-relaxed">
              {product.description}
            </p>

            {/* Size Selection */}
            {product.sizes && product.sizes.length > 0 && (
              <div>
                <label className="text-sm font-medium mb-3 block">Size</label>
                <div className="flex flex-wrap gap-2">
                  {product.sizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setSelectedSize(size)}
                      className={`px-4 py-2 rounded-lg border transition-colors ${
                        selectedSize === size 
                          ? 'border-accent bg-accent/10 text-accent' 
                          : 'border-border hover:border-accent/50'
                      }`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Color Selection */}
            {product.colors && product.colors.length > 0 && (
              <div>
                <label className="text-sm font-medium mb-3 block">Color</label>
                <div className="flex flex-wrap gap-2">
                  {product.colors.map((color) => (
                    <button
                      key={color}
                      onClick={() => setSelectedColor(color)}
                      className={`px-4 py-2 rounded-lg border transition-colors ${
                        selectedColor === color 
                          ? 'border-accent bg-accent/10 text-accent' 
                          : 'border-border hover:border-accent/50'
                      }`}
                    >
                      {color}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Quantity */}
            <div>
              <label className="text-sm font-medium mb-3 block">Quantity</label>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="w-10 h-10 rounded-lg border border-border hover:border-accent/50 flex items-center justify-center"
                >
                  -
                </button>
                <span className="w-12 text-center font-medium">{quantity}</span>
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="w-10 h-10 rounded-lg border border-border hover:border-accent/50 flex items-center justify-center"
                >
                  +
                </button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Button 
                onClick={handleAddToCart}
                disabled={!product.in_stock}
                className="flex-1 h-12 text-base"
              >
                <ShoppingCart className="mr-2 h-5 w-5" />
                {product.in_stock ? 'Add to Cart' : 'Out of Stock'}
              </Button>
              <Button variant="outline" className="h-12 px-4">
                <Heart className="h-5 w-5" />
              </Button>
              <Button variant="outline" className="h-12 px-4">
                <Share2 className="h-5 w-5" />
              </Button>
            </div>

            <div className="grid gap-3 rounded-2xl border border-border bg-[linear-gradient(140deg,rgba(245,158,11,0.08),rgba(255,255,255,0.92))] p-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-foreground shadow-sm">
                  <Users className="h-3.5 w-3.5 text-amber-600" />
                  {socialProofCount}+ shoppers engaged with this style recently
                </span>
                {product.in_stock && (
                  <span className="inline-flex items-center gap-2 rounded-full bg-rose-500/10 px-3 py-1 text-xs font-medium text-rose-600">
                    <Radio className="h-3.5 w-3.5" />
                    Live store demo available
                  </span>
                )}
              </div>

              <div>
                <h2 className="text-lg font-semibold">Store support and live assistance</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Watch a live walkthrough, then use the store locator to contact the nearest branch
                  by WhatsApp or phone before you place the order.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <Button variant="outline" className="justify-start" asChild>
                  <Link href={`/try-on-live?product=${encodeURIComponent(product.id)}`}>
                    <Radio className="mr-2 h-4 w-4 text-rose-600" />
                    Watch Live
                  </Link>
                </Button>
                <Button variant="outline" className="justify-start" asChild>
                  <Link href={`/stores?search=${encodeURIComponent(brandName)}`}>
                    <MessageCircle className="mr-2 h-4 w-4 text-emerald-600" />
                    WhatsApp / Call Store
                  </Link>
                </Button>
                <Button variant="outline" className="justify-start" asChild>
                  <Link href={`/stores?search=${encodeURIComponent(brandName)}`}>
                    <MapPinned className="mr-2 h-4 w-4 text-blue-600" />
                    Store Locator
                  </Link>
                </Button>
              </div>

              <div className="rounded-xl border border-border/70 bg-white/70 p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">{brandName} live now</p>
                    <p className="text-muted-foreground">New arrivals, sizing walkthroughs, and pickup support.</p>
                  </div>
                  <span className="text-sm font-semibold text-rose-600">{liveViewerCount} viewing</span>
                </div>
              </div>
            </div>

            {/* Features */}
            <div className="grid grid-cols-3 gap-4 pt-6 border-t border-border">
              <div className="flex flex-col items-center text-center">
                <Truck className="h-5 w-5 text-accent mb-2" />
                <span className="text-xs text-muted-foreground">Free Shipping</span>
              </div>
              <div className="flex flex-col items-center text-center">
                <Shield className="h-5 w-5 text-accent mb-2" />
                <span className="text-xs text-muted-foreground">Secure Payment</span>
              </div>
              <div className="flex flex-col items-center text-center">
                <RefreshCw className="h-5 w-5 text-accent mb-2" />
                <span className="text-xs text-muted-foreground">Easy Returns</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
