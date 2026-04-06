import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { transitionStandard } from '@/motion';

interface ImageOptimizedProps {
  src: string;
  alt: string;
  className?: string;
  containerClassName?: string;
  fallback?: string;
  blurDataURL?: string;
  priority?: boolean;
  onLoad?: () => void;
  onError?: () => void;
  sizes?: string;
  aspectRatio?: 'square' | 'video' | 'portrait' | 'landscape';
  objectFit?: 'cover' | 'contain' | 'fill' | 'none';
  lazy?: boolean;
  placeholder?: 'blur' | 'empty';
}

export function ImageOptimized({
  src,
  alt,
  className,
  containerClassName,
  fallback = '/placeholder.png',
  blurDataURL,
  priority = false,
  onLoad,
  onError,
  sizes = '100vw',
  aspectRatio = 'square',
  objectFit = 'cover',
  lazy = true,
  placeholder = 'empty',
}: ImageOptimizedProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isInView, setIsInView] = useState(!lazy || priority);
  const imgRef = useRef<HTMLImageElement>(null);

  // Calculate aspect ratio
  const aspectRatioClass = {
    square: 'aspect-square',
    video: 'aspect-video',
    portrait: 'aspect-[3/4]',
    landscape: 'aspect-[4/3]',
  }[typeof aspectRatio === 'string' ? aspectRatio : 'square'] || 'aspect-square';

  // Intersection observer for lazy loading
  useEffect(() => {
    if (!lazy || priority) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        rootMargin: '200px',
        threshold: 0.01,
      }
    );

    if (imgRef.current) {
      observer.observe(imgRef.current);
    }

    return () => observer.disconnect();
  }, [lazy, priority]);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  return (
    <div
      className={cn(
        'relative overflow-hidden bg-muted',
        aspectRatioClass,
        containerClassName
      )}
      ref={imgRef}
    >
      {/* Blur placeholder */}
      {placeholder === 'blur' && blurDataURL && !isLoaded && (
        <img
          src={blurDataURL}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 h-full w-full scale-110 object-cover blur-2xl"
        />
      )}

      {/* Shimmer placeholder */}
      {!isLoaded && placeholder === 'empty' && (
        <div className="absolute inset-0 animate-shimmer bg-gradient-to-r from-muted via-muted/50 to-muted bg-[length:200%_100%]" />
      )}

      {/* Main image */}
      {isInView && (
        <motion.img
          src={hasError ? fallback : src}
          alt={alt}
          sizes={sizes}
          loading={priority ? 'eager' : 'lazy'}
          decoding={priority ? 'sync' : 'async'}
          onLoad={handleLoad}
          onError={handleError}
          initial={{ opacity: 0 }}
          animate={{ opacity: isLoaded ? 1 : 0 }}
          transition={transitionStandard}
          className={cn(
            'h-full w-full transition-transform duration-300',
            objectFit === 'cover' && 'object-cover',
            objectFit === 'contain' && 'object-contain',
            objectFit === 'fill' && 'object-fill',
            objectFit === 'none' && 'object-none',
            className
          )}
        />
      )}
    </div>
  );
}

// Image gallery with lazy loading
interface ImageGalleryProps {
  images: string[];
  alt: string;
  className?: string;
  aspectRatio?: ImageOptimizedProps['aspectRatio'];
}

export function ImageGallery({ images, alt, className, aspectRatio }: ImageGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Main image */}
      <ImageOptimized
        src={images[selectedIndex]}
        alt={`${alt} - Image ${selectedIndex + 1}`}
        aspectRatio={aspectRatio}
        priority
      />

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {images.map((image, index) => (
            <button
              key={index}
              onClick={() => setSelectedIndex(index)}
              aria-label={`View image ${index + 1}`}
              className={cn(
                'flex-shrink-0 overflow-hidden rounded-md border-2 transition-colors',
                selectedIndex === index ? 'border-primary' : 'border-transparent'
              )}
            >
              <ImageOptimized
                src={image}
                alt={`${alt} - Thumbnail ${index + 1}`}
                aspectRatio="square"
                className="h-16 w-16"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Responsive image with srcset
interface ResponsiveImageProps extends Omit<ImageOptimizedProps, 'src'> {
  srcSet: {
    default: string;
    sm?: string;
    md?: string;
    lg?: string;
    xl?: string;
    '2xl'?: string;
  };
}

export function ResponsiveImage({ srcSet, ...props }: ResponsiveImageProps) {
  const sources = Object.entries(srcSet)
    .filter(([key]) => key !== 'default')
    .map(([size, src]) => `${src} ${size === 'sm' ? '640w' : size === 'md' ? '768w' : size === 'lg' ? '1024w' : size === 'xl' ? '1280w' : '1536w'}`)
    .join(', ');

  return (
    <ImageOptimized
      {...props}
      src={srcSet.default}
      sizes={props.sizes || sources}
    />
  );
}
