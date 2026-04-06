import { motion } from 'framer-motion';
import Link from 'next/link';
import { Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getFeaturedProducts } from '@/services/mockData';
import type { Product } from '@/types';
import { safeImageSrc } from '@/lib/imageFallback';
import { createTransition } from '@/motion';

export function FeaturedProducts() {
  const products = getFeaturedProducts(8);

  return (
    <section className="py-16 md:py-24 bg-secondary/50">
      <div className="container">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-12">
          <div>
            <h2 className="heading-section mb-2">Today's Style Picks</h2>
            <p className="text-muted-foreground">
              Curated pieces selected just for you
            </p>
          </div>
          <Button variant="elegant" asChild>
            <Link href="/discover">View All</Link>
          </Button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
          {products.map((product, index) => (
            <ProductCard key={product.id} product={product} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}

function ProductCard({ product, index }: { product: Product; index: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={createTransition({ duration: 0.4, delay: index * 0.05 })}
      className="group"
    >
      <Link href={`/product/${product.id}`} className="block">
        {/* Image Container */}
        <div className="relative aspect-[3/4] mb-4 overflow-hidden rounded-lg bg-muted">
          <img
            src={safeImageSrc(product.images?.[0])}
            alt={product.name}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={(e) => {
              e.currentTarget.src = safeImageSrc('');
            }}
            loading="lazy"
          />
          
          {/* Overlay Actions */}
          <div className="absolute inset-0 bg-charcoal/0 group-hover:bg-charcoal/20 transition-colors duration-300" />
          
          {/* Wishlist Button */}
          <button 
            className="absolute top-3 right-3 w-9 h-9 bg-background/90 backdrop-blur-sm rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-background"
            onClick={(e) => {
              e.preventDefault();
              // Handle wishlist
            }}
          >
            <Heart className="h-4 w-4 text-foreground" />
          </button>

          {/* Sale Badge */}
          {product.originalPrice && (
            <span className="absolute top-3 left-3 bg-destructive text-destructive-foreground text-xs font-semibold px-2 py-1 rounded">
              SALE
            </span>
          )}

          {/* Quick Try-On */}
          <div className="absolute bottom-3 left-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="gold" size="sm" className="w-full text-xs">
              Quick Try-On
            </Button>
          </div>
        </div>

        {/* Product Info */}
        <div className="space-y-1">
          <p className="text-label text-muted-foreground">{product.brand}</p>
          <h3 className="font-medium text-foreground group-hover:text-accent transition-colors line-clamp-1">
            {product.name}
          </h3>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-foreground">
              ${product.price}
            </span>
            {product.originalPrice && (
              <span className="text-sm text-muted-foreground line-through">
                ${product.originalPrice}
              </span>
            )}
          </div>
          
          {/* Style Score */}
          <div className="flex items-center gap-1 pt-1">
            <div className="h-1 flex-1 bg-muted rounded-full overflow-hidden">
              <div 
                className="h-full bg-accent rounded-full transition-all duration-500"
                style={{ width: `${product.styleCompatibility}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {product.styleCompatibility}% match
            </span>
          </div>
        </div>
      </Link>
    </motion.article>
  );
}
