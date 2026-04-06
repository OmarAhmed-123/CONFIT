import { motion } from 'framer-motion';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ImageOptimized } from '@/components/lazy';

interface BrandCardProps {
  id: string;
  name: string;
  logo?: string;
  coverImage?: string;
  description?: string;
  productCount?: number;
  isVerified?: boolean;
  isFollowing?: boolean;
  onFollow?: () => void;
  className?: string;
  variant?: 'default' | 'compact' | 'featured';
}

export function BrandCard({
  id,
  name,
  logo,
  coverImage,
  description,
  productCount,
  isVerified,
  isFollowing,
  onFollow,
  className,
  variant = 'default',
}: BrandCardProps) {
  if (variant === 'compact') {
    return (
      <motion.div
        whileHover={{ scale: 1.02 }}
        className={cn('flex items-center gap-3 rounded-lg border p-3', className)}
      >
        <Link href={`/brand/${id}`} className="flex items-center gap-3 flex-1">
          <div className="h-12 w-12 overflow-hidden rounded-full bg-muted">
            {logo ? (
              <ImageOptimized src={logo} alt={name} aspectRatio="square" />
            ) : (
              <div className="flex h-full items-center justify-center text-lg font-bold">
                {name.charAt(0)}
              </div>
            )}
          </div>
          <div>
            <div className="flex items-center gap-1">
              <h3 className="font-semibold">{name}</h3>
              {isVerified && (
                <Badge variant="secondary" className="h-4 px-1 text-xs">
                  ✓
                </Badge>
              )}
            </div>
            {productCount !== undefined && (
              <p className="text-xs text-muted-foreground">
                {productCount} products
              </p>
            )}
          </div>
        </Link>
        <Button
          size="sm"
          variant={isFollowing ? 'secondary' : 'default'}
          onClick={onFollow}
        >
          {isFollowing ? 'Following' : 'Follow'}
        </Button>
      </motion.div>
    );
  }

  if (variant === 'featured') {
    return (
      <motion.article
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ y: -4 }}
        className={cn('group relative rounded-xl overflow-hidden', className)}
      >
        <Link href={`/brand/${id}`}>
          {coverImage ? (
            <ImageOptimized
              src={coverImage}
              alt={name}
              aspectRatio="video"
              className="transition-transform duration-500 group-hover:scale-105"
            />
          ) : (
            <div className="aspect-video bg-gradient-to-br from-primary/20 to-primary/5" />
          )}
          
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          
          <div className="absolute bottom-0 left-0 right-0 p-6">
            <div className="flex items-end justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  {logo && (
                    <div className="h-10 w-10 overflow-hidden rounded-full bg-white">
                      <ImageOptimized src={logo} alt={name} aspectRatio="square" />
                    </div>
                  )}
                  <div>
                    <h3 className="text-lg font-bold text-white">{name}</h3>
                    {isVerified && (
                      <Badge variant="secondary" className="text-xs">
                        Verified
                      </Badge>
                    )}
                  </div>
                </div>
                {description && (
                  <p className="text-sm text-white/80 line-clamp-2 max-w-md">
                    {description}
                  </p>
                )}
              </div>
              <Button
                variant="secondary"
                onClick={(e) => {
                  e.preventDefault();
                  onFollow?.();
                }}
              >
                {isFollowing ? 'Following' : 'Follow'}
              </Button>
            </div>
          </div>
        </Link>
      </motion.article>
    );
  }

  // Default variant
  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className={cn('group rounded-lg border overflow-hidden', className)}
    >
      <Link href={`/brand/${id}`}>
        <div className="relative h-32 bg-gradient-to-br from-primary/10 to-transparent">
          {coverImage && (
            <ImageOptimized
              src={coverImage}
              alt={name}
              aspectRatio="video"
              className="absolute inset-0 opacity-30"
            />
          )}
        </div>
        
        <div className="p-4">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 overflow-hidden rounded-full bg-muted -mt-8 border-4 border-background">
              {logo ? (
                <ImageOptimized src={logo} alt={name} aspectRatio="square" />
              ) : (
                <div className="flex h-full items-center justify-center text-lg font-bold">
                  {name.charAt(0)}
                </div>
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-1">
                <h3 className="font-semibold">{name}</h3>
                {isVerified && (
                  <Badge variant="secondary" className="h-4 px-1 text-xs">
                    ✓
                  </Badge>
                )}
              </div>
              {productCount !== undefined && (
                <p className="text-xs text-muted-foreground">
                  {productCount} products
                </p>
              )}
            </div>
          </div>
          
          {description && (
            <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
              {description}
            </p>
          )}
          
          <div className="mt-4 flex gap-2">
            <Button asChild size="sm" className="flex-1">
              <Link href={`/brand/${id}`}>View</Link>
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.preventDefault();
                onFollow?.();
              }}
            >
              {isFollowing ? 'Following' : 'Follow'}
            </Button>
          </div>
        </div>
      </Link>
    </motion.article>
  );
}
