import { motion } from 'framer-motion';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Heart, ShoppingBag, Camera, Truck, RotateCcw, Shield,
  ChevronLeft, ChevronRight, Minus, Plus, MapPin
} from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { useProductViewModel } from '@/viewmodels/useProductViewModel';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { pageVariants, transitionStandard } from '@/motion';
import { safeImageSrc } from '@/lib/imageFallback';

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();

  const {
    product,
    relatedProducts,
    isLoading,
    notFound,
    selectedSize,
    selectedColor,
    quantity,
    activeImageIndex,
    isAddingToCart,
    isWishlisted,
    fitRec,
    stores,
    height,
    weight,
    setSelectedSize,
    setSelectedColor,
    setActiveImageIndex,
    setHeight,
    setWeight,
    incrementQuantity,
    decrementQuantity,
    handleAddToCart,
    toggleWishlist,
    calculateSize,
  } = useProductViewModel(id || '');

  if (notFound) {
    return (
      <MainLayout>
        <div className="container py-20 text-center">
          <h1 className="heading-section mb-4">Product Not Found</h1>
          <p className="text-muted-foreground mb-8">The product you're looking for doesn't exist.</p>
          <Button variant="hero" asChild>
            <Link href="/discover">Browse Products</Link>
          </Button>
        </div>
      </MainLayout>
    );
  }

  if (isLoading || !product) {
    return (
      <MainLayout>
        <div className="container py-40 flex justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent"></div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <motion.div
        className="container py-8"
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
      >
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
          <Link href="/" className="hover:text-foreground">Home</Link>
          <span>/</span>
          <Link href="/discover" className="hover:text-foreground">Discover</Link>
          <span>/</span>
          <span className="capitalize">{product.category}</span>
          <span>/</span>
          <span className="text-foreground">{product.name}</span>
        </nav>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Left: Image Gallery */}
          <div className="space-y-4">
            {/* Main Image */}
            <motion.div
              key={activeImageIndex}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="aspect-[3/4] rounded-xl overflow-hidden bg-muted relative group"
            >
              {product.images?.[activeImageIndex] && (
                <motion.img
                  layoutId={`product-image-${product.id}`}
                  src={safeImageSrc(product.images?.[activeImageIndex])}
                  alt={product.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.currentTarget.src = safeImageSrc('');
                  }}
                  transition={transitionStandard}
                />
              )}

              {/* Navigation Arrows */}
              {product.images && product.images.length > 1 && (
                <>
                  <button
                    onClick={() => setActiveImageIndex(prev =>
                      prev === 0 ? product.images.length - 1 : prev - 1
                    )}
                    className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-background/90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    onClick={() => setActiveImageIndex(prev =>
                      prev === product.images.length - 1 ? 0 : prev + 1
                    )}
                    className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-background/90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </>
              )}

              {/* Sale Badge */}
              {product.originalPrice && (
                <span className="absolute top-4 left-4 bg-destructive text-destructive-foreground text-sm font-semibold px-3 py-1 rounded">
                  {Math.round((1 - product.price / product.originalPrice) * 100)}% OFF
                </span>
              )}
            </motion.div>

            {/* Thumbnail Gallery */}
            {product.images && product.images.length > 1 && (
              <div className="flex gap-3">
                {product.images.map((image, index) => (
                  <button
                    key={index}
                    onClick={() => setActiveImageIndex(index)}
                    className={`w-20 h-24 rounded-lg overflow-hidden border-2 transition-all ${index === activeImageIndex
                      ? 'border-accent'
                      : 'border-transparent hover:border-border'
                      }`}
                  >
                    <img
                      src={safeImageSrc(image)}
                      alt=""
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.currentTarget.src = safeImageSrc('');
                      }}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right: Product Info */}
          <div className="space-y-6">
            {/* Brand & Name */}
            <div>
              <p className="text-label text-muted-foreground mb-2">{product.brand}</p>
              <motion.h1 layoutId={`product-title-${product.id}`} className="heading-hero mb-4">
                {product.name}
              </motion.h1>

              {/* Price */}
              <div className="flex items-center gap-4">
                <span className="text-3xl font-bold">${product.price}</span>
                {product.originalPrice && (
                  <span className="text-xl text-muted-foreground line-through">
                    ${product.originalPrice}
                  </span>
                )}
              </div>
            </div>

            {/* Fit Recommendation - Enhanced */}
            <div className="bg-accent/5 border border-accent/20 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">Style & Fit Match</span>
                <span className={`font-semibold ${fitRec.color}`}>{fitRec.text}</span>
              </div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all"
                    style={{ width: `${product.styleCompatibility}%` }}
                  />
                </div>
                <span className="font-medium">{product.styleCompatibility}%</span>
              </div>
              <p className="text-xs text-muted-foreground">
                82% of users say this runs <span className="font-semibold text-foreground">True to Size</span>.
              </p>
            </div>

            {/* Description */}
            <p className="text-muted-foreground">{product.description}</p>

            {/* BNPL Widget */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground border-y border-border py-3 my-4">
              <span className="font-semibold text-foreground">Klarna.</span>
              <span>Pay in 4 interest-free payments of ${(product.price / 4).toFixed(2)}.</span>
              <button className="underline hover:text-foreground">Learn more</button>
            </div>

            {/* Color Selection */}
            <div>
              <p className="font-medium mb-3">
                Color: <span className="text-muted-foreground">{selectedColor || product.colors?.[0]}</span>
              </p>
              <div className="flex gap-2">
                {product.colors?.map((color) => (
                  <button
                    key={color}
                    onClick={() => setSelectedColor(color)}
                    className={`px-4 py-2 rounded-full border text-sm transition-all ${(selectedColor || product.colors?.[0]) === color
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border hover:border-accent'
                      }`}
                  >
                    {color}
                  </button>
                ))}
              </div>
            </div>

            {/* Size Selection */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="font-medium">Size</p>
                <div className="flex gap-4">
                  <Dialog>
                    <DialogTrigger asChild>
                      <button className="text-sm text-accent hover:underline">Calculate My Size</button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Calculate My Size</DialogTitle>
                        <DialogDescription>Enter your measurements to get a recommendation.</DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <label className="text-sm font-medium">Height (cm)</label>
                            <input
                              type="number"
                              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                              placeholder="170"
                              value={height}
                              onChange={e => setHeight(e.target.value)}
                            />
                          </div>
                          <div className="space-y-2">
                            <label className="text-sm font-medium">Weight (kg)</label>
                            <input
                              type="number"
                              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                              placeholder="65"
                              value={weight}
                              onChange={e => setWeight(e.target.value)}
                            />
                          </div>
                        </div>
                        <Button onClick={calculateSize}>Find My Size</Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                  <button className="text-sm text-muted-foreground hover:underline">Size Guide</button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {product.sizes?.map((size) => (
                  <button
                    key={size}
                    onClick={() => setSelectedSize(size)}
                    className={`w-14 h-12 rounded-lg border text-sm font-medium transition-all ${selectedSize === size
                      ? 'border-accent bg-accent text-accent-foreground'
                      : 'border-border hover:border-accent'
                      }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            {/* Store Availability for BOPIS */}
            <div className="flex items-start gap-3 p-3 bg-muted rounded-lg text-sm">
              <MapPin className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Check Store Availability</p>
                <p className="text-muted-foreground mb-2">See if this item is in stock at a store near you.</p>
                <Dialog>
                  <DialogTrigger asChild>
                    <button className="text-accent underline font-medium hover:text-accent/80">
                      Find in Store
                    </button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Find in Store</DialogTitle>
                      <DialogDescription>
                        Check availability at stores near you.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 mt-2">
                      {stores.map(store => (
                        <div key={store.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <p className="font-medium">{store.name}</p>
                            <p className="text-sm text-muted-foreground">{store.address}</p>
                            <p className="text-xs text-muted-foreground mt-1">{store.distance} away</p>
                          </div>
                          <div className="text-right">
                            <span className={`text-sm font-medium ${store.stock === 'High Stock' ? 'text-green-600' :
                              store.stock === 'Low Stock' ? 'text-orange-600' : 'text-red-600'
                              }`}>
                              {store.stock}
                            </span>
                            {store.stock !== 'Out of Stock' && (
                              <Button size="sm" variant="outline" className="block mt-2 h-7 text-xs ml-auto">
                                Pick Up
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            </div>

            {/* Quantity */}
            <div>
              <p className="font-medium mb-3">Quantity</p>
              <div className="flex items-center gap-4">
                <div className="flex items-center border border-border rounded-lg">
                  <button
                    onClick={decrementQuantity}
                    className="w-10 h-10 flex items-center justify-center hover:bg-muted transition-colors"
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                  <span className="w-12 text-center font-medium">{quantity}</span>
                  <button
                    onClick={incrementQuantity}
                    className="w-10 h-10 flex items-center justify-center hover:bg-muted transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
                <span className="text-sm text-muted-foreground">
                  {product.inStock ? 'In Stock' : 'Out of Stock'}
                </span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-4">
              <Button
                variant="hero"
                size="lg"
                className="flex-1"
                onClick={handleAddToCart}
                disabled={!product.inStock || isAddingToCart}
              >
                <ShoppingBag className="h-5 w-5 mr-2" />
                {isAddingToCart ? 'Adding...' : `Add to Cart — $${(product.price * quantity).toFixed(2)}`}
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={toggleWishlist}
                className={isWishlisted ? 'text-destructive border-destructive' : ''}
              >
                <Heart className={`h-5 w-5 ${isWishlisted ? 'fill-current' : ''}`} />
              </Button>
            </div>

            {/* Try On Button */}
            <Button variant="gold" className="w-full" asChild>
              <Link href="/try-on">
                <Camera className="h-4 w-4 mr-2" />
                Virtual Try-On
              </Link>
            </Button>

            {/* Trust Badges */}
            <div className="grid grid-cols-3 gap-4 pt-6 border-t border-border">
              <div className="text-center">
                <Truck className="h-6 w-6 mx-auto mb-2 text-accent" />
                <p className="text-xs text-muted-foreground">Free Shipping</p>
              </div>
              <div className="text-center">
                <RotateCcw className="h-6 w-6 mx-auto mb-2 text-accent" />
                <p className="text-xs text-muted-foreground">Easy Returns</p>
              </div>
              <div className="text-center">
                <Shield className="h-6 w-6 mx-auto mb-2 text-accent" />
                <p className="text-xs text-muted-foreground">Secure Payment</p>
              </div>
            </div>
          </div>
        </div>

        {/* Related Products */}
        <section className="mt-20">
          <h2 className="heading-section mb-8">You May Also Like</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {relatedProducts.map((relProduct) => (
              <Link
                key={relProduct.id}
                href={`/product/${relProduct.id}`}
                className="group"
              >
                <div className="aspect-[3/4] rounded-lg overflow-hidden bg-muted mb-3">
                  <img
                    src={safeImageSrc(relProduct.images?.[0])}
                    alt={relProduct.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={(e) => {
                      e.currentTarget.src = safeImageSrc('');
                    }}
                  />
                </div>
                <p className="text-label text-muted-foreground">{relProduct.brand}</p>
                <h3 className="font-medium group-hover:text-accent transition-colors">{relProduct.name}</h3>
                <p className="font-semibold">${relProduct.price}</p>
              </Link>
            ))}
          </div>
        </section>
      </motion.div>
    </MainLayout>
  );
}
