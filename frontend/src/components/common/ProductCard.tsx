import { motion } from 'framer-motion';
import Link from 'next/link';
import { Heart, ShoppingCart, Eye } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ImageOptimized } from '@/components/lazy';
import { productCardVariants, createStaggerTransition, transitionFast } from '@/motion';

interface ProductCardProps {
  id: string;
  name: string;
  brand: string;
  price: number;
  originalPrice?: number;
  image: string;
  images?: string[];
  category?: string;
  isNew?: boolean;
  isOnSale?: boolean;
  isFavorite?: boolean;
  onAddToCart?: () => void;
  onToggleFavorite?: () => void;
  className?: string;
  aspectRatio?: 'square' | 'portrait' | 'landscape';
}

export function ProductCard({
  id,
  name,
  brand,
  price,
  originalPrice,
  image,
  isNew,
  isOnSale,
  isFavorite,
  onAddToCart,
  onToggleFavorite,
  className,
  aspectRatio = 'portrait',
}: ProductCardProps) {
  const discount = originalPrice ? Math.round(((originalPrice - price) / originalPrice) * 100) : 0;

  return (
    <motion.article
      variants={productCardVariants}
      initial="initial"
      animate="animate"
      whileHover="hover"
      whileTap="tap"
      transition={transitionFast}
      className={cn('group relative flex flex-col', className)}
    >
      {/* Image Container */}
      <Link href={`/product/${id}`} className="relative overflow-hidden rounded-lg">
        <motion.div layoutId={`product-image-${id}`}>
          <ImageOptimized
            src={image}
            alt={name}
            aspectRatio={aspectRatio}
            className="transition-transform duration-500 group-hover:scale-105"
          />
        </motion.div>

        {/* Badges */}
        <div className="absolute left-3 top-3 flex flex-col gap-2">
          {isNew && (
            <Badge variant="default" className="bg-primary text-primary-foreground">
              New
            </Badge>
          )}
          {isOnSale && discount > 0 && (
            <Badge variant="destructive">-{discount}%</Badge>
          )}
        </div>

        {/* Quick Actions */}
        <div className="absolute right-3 top-3 flex flex-col gap-2 opacity-0 transition-opacity group-hover:opacity-100">
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8 rounded-full"
            onClick={(e) => {
              e.preventDefault();
              onToggleFavorite?.();
            }}
            aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Heart
              className={cn('h-4 w-4', isFavorite && 'fill-destructive text-destructive')}
            />
          </Button>
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8 rounded-full"
            onClick={(e) => {
              e.preventDefault();
              onAddToCart?.();
            }}
            aria-label="Add to cart"
          >
            <ShoppingCart className="h-4 w-4" />
          </Button>
        </div>

        {/* View Button */}
        <div className="absolute inset-x-3 bottom-3 opacity-0 transition-opacity group-hover:opacity-100">
          <Button type="button" size="sm" className="w-full" variant="secondary" onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}>
            <Eye className="mr-2 h-4 w-4" />
            Quick View
          </Button>
        </div>
      </Link>

      {/* Content */}
      <div className="mt-3 space-y-1.5">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {brand}
        </p>
        <Link href={`/product/${id}`}>
          <motion.h3 layoutId={`product-title-${id}`} className="line-clamp-2 text-sm font-medium leading-tight hover:text-primary">
            {name}
          </motion.h3>
        </Link>
        <div className="flex items-center gap-2">
          <span className="font-semibold">${price.toLocaleString()}</span>
          {originalPrice && (
            <span className="text-sm text-muted-foreground line-through">
              ${originalPrice.toLocaleString()}
            </span>
          )}
        </div>
      </div>
    </motion.article>
  );
}

// Product Grid Component
interface ProductGridProps {
  products: Array<ProductCardProps>;
  className?: string;
  columns?: 2 | 3 | 4 | 5;
}

export function ProductGrid({ products, className, columns = 4 }: ProductGridProps) {
  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4',
    5: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5',
  };

  return (
    <div className={cn('grid gap-4 sm:gap-6', gridCols[columns], className)}>
      {products.map((product, index) => (
        <motion.div
          key={product.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createStaggerTransition(index)}
        >
          <ProductCard {...product} />
        </motion.div>
      ))}
    </div>
  );
}
