import { motion } from 'framer-motion';
import Link from 'next/link';
import { Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProductSustainabilityBadge } from '@/components/sustainability';
import type { Product } from '@/types';
import { safeImageSrc } from '@/lib/imageFallback';
import { transitionHero, transitionStandard, transitionLuxury, springGentle, springSnappy, springMagnetic, createStaggerTransition, createTransition } from '@/motion';
import { emitEcosystemEvent } from '@/services/telemetry';

interface ProductCardProps {
  product: Product;
  index?: number;
  viewMode?: 'grid' | 'list';
}

export function ProductCard({ product, index = 0, viewMode = 'grid' }: ProductCardProps) {
  if (viewMode === 'list') {
    return <ProductCardList product={product} index={index} />;
  }

  return (
    <motion.article
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={createTransition({ 
        ...transitionHero,
        ...createStaggerTransition(index, 0.08, 0.4),
        ...springGentle,
      })}
      whileHover={{ 
        y: -4,
        transition: springSnappy
      }}
      className="group"
    >
      <Link
        href={`/product/${product.id}`}
        className="block"
        onClick={() => {
          void emitEcosystemEvent("product_viewed", {
            product_id: product.id,
            category: product.category,
            brand: product.brand,
            price: product.price,
            source: "product_card",
          });
        }}
      >
        {/* Image Container */}
        <div className="relative aspect-[3/4] mb-4 overflow-hidden rounded-lg bg-muted">
          <motion.img
            layoutId={`product-image-${product.id}`}
            src={safeImageSrc(product.images?.[0])}
            alt={product.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.src = safeImageSrc('');
            }}
            loading="lazy"
            initial={{ scale: 1.1 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={createTransition({ ...transitionHero, ...createStaggerTransition(index, 0.08, 0.4) })}
            whileHover={{ scale: 1.08, transition: transitionLuxury }}
          />
          
          {/* Overlay Actions */}
          <motion.div 
            className="absolute inset-0 bg-gradient-to-t from-charcoal/60 via-charcoal/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            initial={{ opacity: 0 }}
          />
          
          {/* Wishlist Button */}
          <motion.button 
            className="absolute top-3 right-3 w-9 h-9 bg-background/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-lg"
            onClick={(e) => {
              e.preventDefault();
              // Handle wishlist
            }}
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            whileHover={{ 
              scale: 1.15, 
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              transition: springSnappy
            }}
            whileTap={{ scale: 0.9 }}
            transition={springMagnetic}
          >
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={createTransition({ duration: 0.2, delay: 0.1 })}
            >
              <Heart className="h-4 w-4 text-foreground group-hover:text-destructive transition-colors" />
            </motion.div>
          </motion.button>

          {/* Sale Badge */}
          {product.originalPrice && (
            <motion.span 
              className="absolute top-3 left-3 bg-destructive text-destructive-foreground text-xs font-semibold px-2 py-1 rounded shadow-lg"
              initial={{ scale: 0, x: -20 }}
              animate={{ scale: 1, x: 0 }}
              transition={createTransition({ ...springMagnetic, delay: Math.min(index * 0.08, 0.4) + 0.2 })}
              whileHover={{ scale: 1.05 }}
            >
              <motion.span
                animate={{ scale: [1, 1.05, 1] }}
                transition={createTransition({ duration: 2, repeat: Infinity })}
              >
                SALE
              </motion.span>
            </motion.span>
          )}

          {/* Sustainability Badge */}
          <div className="absolute top-3 left-3 mt-8">
            <ProductSustainabilityBadge productId={product.id} />
          </div>

          {/* Quick Try-On */}
          <motion.div 
            className="absolute bottom-3 left-3 right-3"
            initial={{ y: 20, opacity: 0 }}
            whileHover={{ y: 0, opacity: 1 }}
            transition={springGentle}
          >
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Button variant="gold" size="sm" className="w-full text-xs shadow-lg backdrop-blur-sm bg-background/90">
                <motion.span
                  animate={{ x: [0, 2, 0] }}
                  transition={createTransition({ duration: 1.5, repeat: Infinity, ease: "easeInOut" })}
                >
                  Quick Try-On
                </motion.span>
              </Button>
            </motion.div>
          </motion.div>
        </div>

        {/* Product Info */}
        <motion.div 
          className="space-y-1"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ delay: Math.min(index * 0.08, 0.4) + 0.3 })}
          
        >
          <motion.p 
            className="text-label text-muted-foreground/80 font-medium"
            whileHover={{ x: 2 }}
            transition={transitionStandard}
          >
            {product.brand}
          </motion.p>
          <motion.h3 layoutId={`product-title-${product.id}`} className="font-semibold text-foreground group-hover:text-accent transition-colors line-clamp-1">
            {product.name}
          </motion.h3>
          <div className="flex items-center gap-2">
            <motion.span 
              className="font-bold text-lg text-foreground"
              whileHover={{ scale: 1.05 }}
              transition={springSnappy}
            >
              ${product.price}
            </motion.span>
            {product.originalPrice && (
              <motion.span 
                className="text-sm text-muted-foreground/70 line-through"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={createTransition({ delay: Math.min(index * 0.08, 0.4) + 0.5 })}
              >
                ${product.originalPrice}
              </motion.span>
            )}
          </div>
          
          {/* Style Score */}
          <div className="flex items-center gap-1 pt-1">
            <div className="h-1.5 flex-1 bg-muted/60 rounded-full overflow-hidden">
              <motion.div 
                className="h-full bg-gradient-to-r from-accent to-accent/80 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${product.styleCompatibility}%` }}
                transition={createTransition({ 
                  duration: 1, 
                  delay: Math.min(index * 0.08, 0.4) + 0.4,
                  type: "spring",
                  stiffness: 200
                })}
                whileHover={{ height: "6px" }}
              />
            </div>
            <motion.span 
              className="text-xs font-medium text-muted-foreground"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={createTransition({ delay: Math.min(index * 0.08, 0.4) + 0.6 })}
            >
              {product.styleCompatibility}% match
            </motion.span>
          </div>
        </motion.div>
      </Link>
    </motion.article>
  );
}

function ProductCardList({ product, index }: { product: Product; index: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={createTransition({ duration: 0.4, delay: Math.min(index * 0.05, 0.3) })}
      
      className="group"
    >
      <Link
        href={`/product/${product.id}`}
        className="flex gap-6 p-4 rounded-lg hover:bg-muted/50 transition-colors"
        onClick={() => {
          void emitEcosystemEvent("product_viewed", {
            product_id: product.id,
            category: product.category,
            brand: product.brand,
            price: product.price,
            source: "product_card_list",
          });
        }}
      >
        {/* Image */}
        <div className="relative w-32 h-40 shrink-0 overflow-hidden rounded-lg bg-muted">
          <img
            src={safeImageSrc(product.images?.[0])}
            alt={product.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.src = safeImageSrc('');
            }}
            loading="lazy"
          />
          {product.originalPrice && (
            <span className="absolute top-2 left-2 bg-destructive text-destructive-foreground text-xs font-semibold px-2 py-0.5 rounded">
              SALE
            </span>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 py-2">
          <p className="text-label text-muted-foreground mb-1">{product.brand}</p>
          <h3 className="font-medium text-lg text-foreground group-hover:text-accent transition-colors mb-2">
            {product.name}
          </h3>
          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
            {product.description}
          </p>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-lg">${product.price}</span>
              {product.originalPrice && (
                <span className="text-sm text-muted-foreground line-through">
                  ${product.originalPrice}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <div className="h-1.5 w-20 bg-muted rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-accent rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${product.styleCompatibility}%` }}
                  transition={transitionStandard}
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {product.styleCompatibility}%
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 py-2">
          <Button variant="hero" size="sm">Try On</Button>
          <Button variant="outline" size="sm">
            <Heart className="h-4 w-4" />
          </Button>
        </div>
      </Link>
    </motion.article>
  );
}
