/**
 * CONFIT — AR Virtual Try-On Page Component
 * ==========================================
 * Full-page AR try-on experience with garment selection.
 *
 * Features:
 * - AR camera with live preview
 * - Product selector
 * - Screenshot gallery
 * - Privacy-first design
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Shirt,
  Camera,
  Download,
  Share2,
  Trash2,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ARCamera } from './ARCamera';
import { ProductSelector } from './ProductSelector';
import { useARPerformance, useBatteryAware } from '@/hooks/useARPerformance';
import type { Product } from '@/types';
import { safeImageSrc } from '@/lib/imageFallback';
import { getPrimaryProductImageUrl } from '@/lib/productImages';

interface CapturedLook {
  id: string;
  image: string;
  productId: string;
  productName: string;
  timestamp: Date;
}

interface ARCameraPageProps {
  products?: Product[];
  onBack?: () => void;
  onAddToCart?: (product: Product) => void;
  onSaveToWardrobe?: (image: string, productId: string) => void;
}

export function ARCameraPage({
  products = [],
  onBack,
  onAddToCart,
  onSaveToWardrobe,
}: ARCameraPageProps) {
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(
    products[0] || null
  );
  const [capturedLooks, setCapturedLooks] = useState<CapturedLook[]>([]);
  const [activeTab, setActiveTab] = useState<'camera' | 'gallery'>('camera');

  const { shouldConservePower } = useBatteryAware();
  const { capabilities } = useARPerformance();

  // Handle screenshot capture
  const handleSaveLook = useCallback((imageData: string) => {
    if (!selectedProduct) return;

    const newLook: CapturedLook = {
      id: `look-${Date.now()}`,
      image: imageData,
      productId: selectedProduct.id,
      productName: selectedProduct.name,
      timestamp: new Date(),
    };

    setCapturedLooks((prev) => [newLook, ...prev]);

    if (onSaveToWardrobe) {
      onSaveToWardrobe(imageData, selectedProduct.id);
    }
  }, [selectedProduct, onSaveToWardrobe]);

  // Handle add to cart
  const handleAddToCart = useCallback(() => {
    if (selectedProduct && onAddToCart) {
      onAddToCart(selectedProduct);
    }
  }, [selectedProduct, onAddToCart]);

  // Delete captured look
  const deleteLook = useCallback((lookId: string) => {
    setCapturedLooks((prev) => prev.filter((l) => l.id !== lookId));
  }, []);

  // Download look
  const downloadLook = useCallback((look: CapturedLook) => {
    const link = document.createElement('a');
    link.href = look.image;
    link.download = `confit-${look.productName}-${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, []);

  // Share look
  const shareLook = useCallback(async (look: CapturedLook) => {
    if (!navigator.share) {
      return;
    }

    try {
      const response = await fetch(look.image);
      const blob = await response.blob();
      const file = new File([blob], 'tryon-look.jpg', { type: 'image/jpeg' });

      await navigator.share({
        title: 'My CONFIT Virtual Try-On',
        text: `Check out how ${look.productName} looks on me!`,
        files: [file],
      });
    } catch (err) {
      console.error('Share failed:', err);
    }
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur-sm border-b">
        <div className="container flex items-center justify-between h-16 px-4">
          <div className="flex items-center gap-4">
            {onBack && (
              <Button variant="ghost" size="icon" onClick={onBack}>
                <ArrowLeft className="h-5 w-5" />
              </Button>
            )}
            <div>
              <h1 className="font-semibold">AR Virtual Try-On</h1>
              <p className="text-xs text-muted-foreground">
                {capabilities.isMobile ? 'Mobile' : 'Desktop'} •{' '}
                {capabilities.isLowEnd ? 'Performance mode' : 'Quality mode'}
              </p>
            </div>
          </div>

          {shouldConservePower && (
            <Badge variant="outline" className="text-yellow-600 border-yellow-600">
              <Sparkles className="h-3 w-3 mr-1" />
              Battery Saver
            </Badge>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="camera" className="flex items-center gap-2">
              <Camera className="h-4 w-4" />
              Camera
            </TabsTrigger>
            <TabsTrigger value="gallery" className="flex items-center gap-2">
              <Shirt className="h-4 w-4" />
              Gallery ({capturedLooks.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="camera" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* AR Camera */}
              <div className="lg:col-span-2">
                {selectedProduct ? (
                  <ARCamera
                    selectedProduct={selectedProduct}
                    onAddToCart={handleAddToCart}
                    onSaveLook={handleSaveLook}
                  />
                ) : (
                  <Card className="aspect-[3/4] flex items-center justify-center">
                    <div className="text-center p-8">
                      <Shirt className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                      <p className="text-muted-foreground">
                        Select a product to start trying on
                      </p>
                    </div>
                  </Card>
                )}
              </div>

              {/* Product Selector */}
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Select Garment</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[400px]">
                      <ProductSelector
                        products={products}
                        selectedIndex={products.findIndex(p => p.id === selectedProduct?.id)}
                        onSelectProduct={(index) => setSelectedProduct(products[index])}
                        onTryOn={() => setActiveTab('camera')}
                        canTryOn={!!selectedProduct}
                        isProcessing={false}
                      />
                    </ScrollArea>
                  </CardContent>
                </Card>

                {/* Selected Product Info */}
                {selectedProduct && (
                  <Card className="mt-4">
                    <CardContent className="p-4">
                      <div className="flex gap-3">
                        <img
                          src={safeImageSrc(getPrimaryProductImageUrl(selectedProduct))}
                          alt={selectedProduct.name}
                          className="w-16 h-20 object-cover rounded-lg"
                          onError={(e) => {
                            e.currentTarget.src = safeImageSrc('');
                          }}
                        />
                        <div className="flex-1">
                          <p className="font-medium text-sm">{selectedProduct.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {selectedProduct.brand}
                          </p>
                          <p className="font-semibold mt-1">
                            ${selectedProduct.price}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="hero"
                        className="w-full mt-3"
                        onClick={handleAddToCart}
                      >
                        Add to Cart
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="gallery" className="space-y-6">
            {capturedLooks.length === 0 ? (
              <Card className="p-12">
                <div className="text-center">
                  <Shirt className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="font-medium">No captured looks yet</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Take screenshots during AR try-on to save them here
                  </p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => setActiveTab('camera')}
                  >
                    <Camera className="h-4 w-4 mr-2" />
                    Start Try-On
                  </Button>
                </div>
              </Card>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                <AnimatePresence>
                  {capturedLooks.map((look) => (
                    <motion.div
                      key={look.id}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      layout
                    >
                      <Card className="overflow-hidden group">
                        <div className="relative aspect-[3/4]">
                          <img
                            src={safeImageSrc(look.image)}
                            alt={look.productName}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.currentTarget.src = safeImageSrc('');
                            }}
                          />
                          
                          {/* Overlay actions */}
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <Button
                              size="icon"
                              variant="secondary"
                              onClick={() => downloadLook(look)}
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                            <Button
                              size="icon"
                              variant="secondary"
                              onClick={() => shareLook(look)}
                            >
                              <Share2 className="h-4 w-4" />
                            </Button>
                            <Button
                              size="icon"
                              variant="destructive"
                              onClick={() => deleteLook(look.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        
                        <CardContent className="p-3">
                          <p className="text-sm font-medium truncate">
                            {look.productName}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {look.timestamp.toLocaleDateString()}
                          </p>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Privacy Footer */}
      <footer className="border-t bg-muted/30 py-4">
        <div className="container px-4">
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Shield className="h-3 w-3" />
            <span>
              Privacy-first: All processing happens on your device. 
              Images are not stored on our servers.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

// Shield icon component
function Shield({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

export default ARCameraPage;
