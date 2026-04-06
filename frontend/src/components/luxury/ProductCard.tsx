/**
 * ProductCard - Luxury product card component
 * Premium styling with hover animations and gold accents
 */

import { ReactNode, CSSProperties } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { productCardVariants, productImageVariants } from '@/motion';
import { Heart, ShoppingBag } from 'lucide-react';

export interface ProductCardProps {
  id: string;
  name: string;
  brand: string;
  price: number;
  originalPrice?: number;
  image: string;
  category?: string;
  isLiked?: boolean;
  isPremium?: boolean;
  onLike?: () => void;
  onAddToCart?: () => void;
  onClick?: () => void;
  className?: string;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  name,
  brand,
  price,
  originalPrice,
  image,
  category,
  isLiked = false,
  isPremium = false,
  onLike,
  onAddToCart,
  onClick,
  className,
}) => {
  const discount = originalPrice ? Math.round(((originalPrice - price) / originalPrice) * 100) : 0;

  return (
    <motion.div
      variants={productCardVariants}
      initial="initial"
      animate="animate"
      whileHover="hover"
      whileTap="tap"
      onClick={onClick}
      className={cn(
        'group relative cursor-pointer',
        'bg-[#151925] rounded-2xl overflow-hidden',
        'border border-white/[0.06]',
        'shadow-[0_4px_20px_0_rgba(0,0,0,0.4)]',
        'hover:shadow-[0_12px_40px_0_rgba(0,0,0,0.5)]',
        'transition-shadow duration-300',
        className
      )}
    >
      {/* Image Container */}
      <div className="relative aspect-[3/4] overflow-hidden bg-[#0B0F1A]">
        <motion.img
          src={image}
          alt={name}
          variants={productImageVariants}
          initial="initial"
          whileHover="hover"
          className="w-full h-full object-cover"
        />
        
        {/* Overlay gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0B0F1A]/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        
        {/* Premium badge */}
        {isPremium && (
          <div className="absolute top-3 left-3 px-2 py-1 bg-[#D4AF37] rounded-md">
            <span className="text-[10px] font-semibold text-[#0B0F1A] tracking-wider uppercase">Premium</span>
          </div>
        )}
        
        {/* Discount badge */}
        {discount > 0 && (
          <div className="absolute top-3 right-3 px-2 py-1 bg-[#F87171] rounded-md">
            <span className="text-[10px] font-semibold text-white tracking-wider">-{discount}%</span>
          </div>
        )}
        
        {/* Quick actions */}
        <div className="absolute bottom-3 left-3 right-3 flex gap-2 opacity-0 translate-y-2 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={(e) => {
              e.stopPropagation();
              onAddToCart?.();
            }}
            className="flex-1 flex items-center justify-center gap-2 py-2 bg-[#D4AF37] rounded-lg text-[#0B0F1A] font-medium text-sm"
          >
            <ShoppingBag className="w-4 h-4" />
            Add
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={(e) => {
              e.stopPropagation();
              onLike?.();
            }}
            className={cn(
              'p-2 rounded-lg transition-colors duration-200',
              isLiked 
                ? 'bg-[#D4AF37] text-[#0B0F1A]' 
                : 'bg-white/10 text-white hover:bg-white/20'
            )}
          >
            <Heart className={cn('w-4 h-4', isLiked && 'fill-current')} />
          </motion.button>
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4">
        {/* Category */}
        {category && (
          <span className="text-[10px] text-[#A0A3A8] uppercase tracking-wider">{category}</span>
        )}
        
        {/* Brand */}
        <p className="text-xs text-[#D4AF37] font-medium mt-1">{brand}</p>
        
        {/* Name */}
        <h3 className="text-sm font-medium text-[#F5F5F5] mt-1 line-clamp-2 leading-snug">{name}</h3>
        
        {/* Price */}
        <div className="flex items-center gap-2 mt-2">
          <span className="text-base font-semibold text-[#F5F5F5]">${price.toFixed(2)}</span>
          {originalPrice && (
            <span className="text-sm text-[#A0A3A8] line-through">${originalPrice.toFixed(2)}</span>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// ═══════════════════════════════════════════════════════════════
// PRODUCT CARD SKELETON
// ═══════════════════════════════════════════════════════════════

export const ProductCardSkeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('bg-[#151925] rounded-2xl overflow-hidden border border-white/[0.06]', className)}>
    <div className="aspect-[3/4] bg-[#1A1F2E] animate-pulse" />
    <div className="p-4 space-y-2">
      <div className="h-3 w-16 bg-[#1A1F2E] rounded animate-pulse" />
      <div className="h-3 w-24 bg-[#1A1F2E] rounded animate-pulse" />
      <div className="h-4 w-32 bg-[#1A1F2E] rounded animate-pulse" />
      <div className="h-5 w-20 bg-[#1A1F2E] rounded animate-pulse mt-3" />
    </div>
  </div>
);

export default ProductCard;
