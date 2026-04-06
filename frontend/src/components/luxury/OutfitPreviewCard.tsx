/**
 * OutfitPreviewCard - Luxury outfit preview component
 * Premium styling for outfit builder with gold accents
 */

import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { luxuryCardVariants, createStaggerTransition } from '@/motion';
import { Sparkles, Heart, Share2 } from 'lucide-react';

export interface OutfitItem {
  id: string;
  name: string;
  image: string;
  category: string;
}

export interface OutfitPreviewCardProps {
  id: string;
  name: string;
  items: OutfitItem[];
  totalPrice: number;
  style?: string;
  occasion?: string;
  isLiked?: boolean;
  onLike?: () => void;
  onShare?: () => void;
  onClick?: () => void;
  className?: string;
}

export const OutfitPreviewCard: React.FC<OutfitPreviewCardProps> = ({
  name,
  items,
  totalPrice,
  style,
  occasion,
  isLiked = false,
  onLike,
  onShare,
  onClick,
  className,
}) => {
  return (
    <motion.div
      variants={luxuryCardVariants}
      initial="initial"
      whileHover="hover"
      whileTap="tap"
      onClick={onClick}
      className={cn(
        'group relative cursor-pointer',
        'bg-gradient-to-b from-[#1A1F2E] to-[#151925]',
        'rounded-2xl overflow-hidden',
        'border border-white/[0.06]',
        'hover:border-[#D4AF37]/30',
        'shadow-[0_8px_30px_0_rgba(0,0,0,0.5)]',
        'hover:shadow-[0_0_30px_0_rgba(212,175,55,0.15)]',
        'transition-all duration-300',
        className
      )}
    >
      {/* Header with gold accent */}
      <div className="relative px-5 py-4 border-b border-white/[0.06]">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#D4AF37]/50 to-transparent" />
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#D4AF37]" />
            <span className="text-xs text-[#A0A3A8] uppercase tracking-wider">{style || 'Curated'}</span>
          </div>
          {occasion && (
            <span className="px-2 py-0.5 bg-[#D4AF37]/10 rounded text-xs text-[#D4AF37]">{occasion}</span>
          )}
        </div>
        
        <h3 className="text-lg font-display font-semibold text-[#F5F5F5] mt-2">{name}</h3>
      </div>
      
      {/* Items Grid */}
      <div className="p-4">
        <div className="grid grid-cols-2 gap-3">
          {items.slice(0, 4).map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={createStaggerTransition(index)}
              className="relative aspect-square rounded-xl overflow-hidden bg-[#0B0F1A] border border-white/[0.04]"
            >
              <img
                src={item.image}
                alt={item.name}
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-gradient-to-t from-[#0B0F1A]/80 to-transparent">
                <span className="text-[10px] text-[#A0A3A8] truncate">{item.category}</span>
              </div>
            </motion.div>
          ))}
          {items.length > 4 && (
            <div className="aspect-square rounded-xl bg-[#0B0F1A] border border-white/[0.04] flex items-center justify-center">
              <span className="text-sm text-[#A0A3A8]">+{items.length - 4}</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/[0.06] flex items-center justify-between">
        <div>
          <span className="text-xs text-[#A0A3A8]">Total</span>
          <p className="text-lg font-semibold text-[#D4AF37]">${totalPrice.toFixed(2)}</p>
        </div>
        
        <div className="flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={(e) => {
              e.stopPropagation();
              onShare?.();
            }}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-[#A0A3A8] transition-colors"
          >
            <Share2 className="w-4 h-4" />
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={(e) => {
              e.stopPropagation();
              onLike?.();
            }}
            className={cn(
              'p-2 rounded-lg transition-colors',
              isLiked 
                ? 'bg-[#D4AF37]/20 text-[#D4AF37]' 
                : 'bg-white/5 hover:bg-white/10 text-[#A0A3A8]'
            )}
          >
            <Heart className={cn('w-4 h-4', isLiked && 'fill-current')} />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};

// ═══════════════════════════════════════════════════════════════
// OUTFIT CARD MINI
// ═══════════════════════════════════════════════════════════════

export interface OutfitCardMiniProps {
  image: string;
  name: string;
  itemCount: number;
  onClick?: () => void;
  className?: string;
}

export const OutfitCardMini: React.FC<OutfitCardMiniProps> = ({
  image,
  name,
  itemCount,
  onClick,
  className,
}) => (
  <motion.div
    whileHover={{ y: -4 }}
    whileTap={{ scale: 0.98 }}
    onClick={onClick}
    className={cn(
      'cursor-pointer rounded-xl overflow-hidden',
      'bg-[#151925] border border-white/[0.06]',
      'hover:border-[#D4AF37]/20',
      'transition-colors duration-200',
      className
    )}
  >
    <div className="aspect-square relative">
      <img src={image} alt={name} className="w-full h-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0B0F1A]/80 to-transparent" />
      <div className="absolute bottom-2 left-2 right-2">
        <p className="text-sm font-medium text-[#F5F5F5] truncate">{name}</p>
        <p className="text-xs text-[#A0A3A8]">{itemCount} items</p>
      </div>
    </div>
  </motion.div>
);

export default OutfitPreviewCard;
