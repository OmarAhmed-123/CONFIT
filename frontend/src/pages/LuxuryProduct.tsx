/**
 * LuxuryProduct - Premium product detail page
 * Features: Large imagery, luxury styling, smooth animations
 */

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Heart, 
  Share2, 
  ShoppingBag, 
  ChevronLeft, 
  ChevronRight,
  Star,
  Truck,
  Shield,
  RefreshCw,
} from 'lucide-react';
import { 
  TopNavigationBar,
  GoldButton,
  GlassContainer,
} from '@/components/luxury';
import { fadeUpVariants, staggerContainer, staggerItem, pageVariants, transitionStandard } from '@/motion';

// Mock product data
const product = {
  id: '1',
  name: 'Silk Evening Dress',
  brand: 'MAISON NOIR',
  price: 2450,
  originalPrice: 3200,
  description: 'Exquisite silk evening dress featuring a flowing silhouette and delicate hand-stitched details. Crafted from the finest mulberry silk, this piece embodies timeless elegance.',
  images: [
    'https://images.unsplash.com/photo-1595777457583-95e397a5e5c7?w=800',
    'https://images.unsplash.com/photo-1518611017547-1a8b8f0d4e5a?w=800',
    'https://images.unsplash.com/photo-1595777457583-95e397a5e5c7?w=800',
  ],
  sizes: ['XS', 'S', 'M', 'L', 'XL'],
  colors: ['Midnight Black', 'Ivory White', 'Champagne Gold'],
  category: 'Dresses',
  rating: 4.9,
  reviews: 127,
  isPremium: true,
};

const LuxuryProduct = () => {
  const { id } = useParams();
  const [selectedImage, setSelectedImage] = useState(0);
  const [selectedSize, setSelectedSize] = useState('M');
  const [selectedColor, setSelectedColor] = useState('Midnight Black');
  const [isLiked, setIsLiked] = useState(false);

  const discount = product.originalPrice 
    ? Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100) 
    : 0;

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="min-h-screen bg-[#0B0F1A]"
    >
      {/* Top Navigation */}
      <TopNavigationBar />

      <main className="pt-20 pb-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-8 lg:gap-16">
            {/* Image Gallery */}
            <motion.div
              variants={fadeUpVariants}
              initial="hidden"
              animate="visible"
              className="relative"
            >
              {/* Main Image */}
              <div className="relative aspect-[3/4] rounded-2xl overflow-hidden bg-[#151925] border border-white/[0.06]">
                <AnimatePresence mode="wait">
                  <motion.img
                    key={selectedImage}
                    src={product.images[selectedImage]}
                    alt={product.name}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={transitionStandard}
                    className="w-full h-full object-cover"
                  />
                </AnimatePresence>
                
                {/* Premium badge */}
                {product.isPremium && (
                  <div className="absolute top-4 left-4 px-3 py-1.5 bg-[#D4AF37] rounded-lg">
                    <span className="text-xs font-semibold text-[#0B0F1A] tracking-wider uppercase">Premium</span>
                  </div>
                )}
                
                {/* Discount badge */}
                {discount > 0 && (
                  <div className="absolute top-4 right-4 px-3 py-1.5 bg-[#F87171] rounded-lg">
                    <span className="text-xs font-semibold text-white tracking-wider">-{discount}%</span>
                  </div>
                )}
                
                {/* Navigation arrows */}
                <button
                  onClick={() => setSelectedImage(prev => prev === 0 ? product.images.length - 1 : prev - 1)}
                  aria-label="Previous image"
                  className="absolute left-4 top-1/2 -translate-y-1/2 p-2 bg-black/40 backdrop-blur-sm rounded-full text-white hover:bg-black/60 transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setSelectedImage(prev => prev === product.images.length - 1 ? 0 : prev + 1)}
                  aria-label="Next image"
                  className="absolute right-4 top-1/2 -translate-y-1/2 p-2 bg-black/40 backdrop-blur-sm rounded-full text-white hover:bg-black/60 transition-colors"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
              
              {/* Thumbnail strip */}
              <div className="flex gap-3 mt-4">
                {product.images.map((img, index) => (
                  <button
                    key={index}
                    onClick={() => setSelectedImage(index)}
                    aria-label={`View image ${index + 1}`}
                    className={`relative w-20 h-24 rounded-lg overflow-hidden border-2 transition-all ${
                      selectedImage === index 
                        ? 'border-[#D4AF37]' 
                        : 'border-white/10 hover:border-white/30'
                    }`}
                  >
                    <img src={img} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </motion.div>

            {/* Product Info */}
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
              className="flex flex-col"
            >
              {/* Breadcrumb */}
              <motion.div variants={staggerItem} className="text-sm text-[#A0A3A8] mb-4">
                <span className="hover:text-[#D4AF37] cursor-pointer">Home</span>
                <span className="mx-2">/</span>
                <span className="hover:text-[#D4AF37] cursor-pointer">{product.category}</span>
              </motion.div>

              {/* Brand */}
              <motion.p variants={staggerItem} className="text-sm text-[#D4AF37] font-medium tracking-wider uppercase mb-2">
                {product.brand}
              </motion.p>

              {/* Name */}
              <motion.h1 variants={staggerItem} className="text-3xl sm:text-4xl font-display font-bold text-[#F5F5F5] mb-4">
                {product.name}
              </motion.h1>

              {/* Rating */}
              <motion.div variants={staggerItem} className="flex items-center gap-3 mb-6">
                <div className="flex items-center gap-1">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-[#D4AF37] text-[#D4AF37]" />
                  ))}
                </div>
                <span className="text-sm text-[#A0A3A8]">{product.rating} ({product.reviews} reviews)</span>
              </motion.div>

              {/* Price */}
              <motion.div variants={staggerItem} className="flex items-baseline gap-4 mb-6">
                <span className="text-3xl font-bold text-[#D4AF37]">${product.price.toLocaleString()}</span>
                {product.originalPrice && (
                  <span className="text-xl text-[#A0A3A8] line-through">${product.originalPrice.toLocaleString()}</span>
                )}
              </motion.div>

              {/* Description */}
              <motion.p variants={staggerItem} className="text-[#A0A3A8] leading-relaxed mb-8">
                {product.description}
              </motion.p>

              {/* Color Selection */}
              <motion.div variants={staggerItem} className="mb-6">
                <label className="text-sm font-medium text-[#F5F5F5] mb-3 block">Color</label>
                <div className="flex flex-wrap gap-3">
                  {product.colors.map((color) => (
                    <button
                      key={color}
                      onClick={() => setSelectedColor(color)}
                      className={`px-4 py-2 rounded-lg text-sm transition-all ${
                        selectedColor === color
                          ? 'bg-[#D4AF37] text-[#0B0F1A] font-medium'
                          : 'bg-white/5 text-[#A0A3A8] hover:bg-white/10'
                      }`}
                    >
                      {color}
                    </button>
                  ))}
                </div>
              </motion.div>

              {/* Size Selection */}
              <motion.div variants={staggerItem} className="mb-8">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium text-[#F5F5F5]">Size</label>
                  <button className="text-sm text-[#D4AF37] hover:underline">Size Guide</button>
                </div>
                <div className="flex flex-wrap gap-3">
                  {product.sizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setSelectedSize(size)}
                      className={`w-12 h-12 rounded-lg text-sm font-medium transition-all ${
                        selectedSize === size
                          ? 'bg-[#D4AF37] text-[#0B0F1A]'
                          : 'bg-white/5 text-[#A0A3A8] hover:bg-white/10 border border-white/10'
                      }`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </motion.div>

              {/* Actions */}
              <motion.div variants={staggerItem} className="flex gap-4 mb-8">
                <GoldButton size="lg" className="flex-1" icon={<ShoppingBag className="w-5 h-5" />}>
                  Add to Cart
                </GoldButton>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setIsLiked(!isLiked)}
                  aria-label={isLiked ? 'Remove from wishlist' : 'Add to wishlist'}
                  className={`p-4 rounded-xl border transition-all ${
                    isLiked 
                      ? 'bg-[#D4AF37]/10 border-[#D4AF37]/30 text-[#D4AF37]' 
                      : 'bg-white/5 border-white/10 text-[#A0A3A8] hover:border-white/20'
                  }`}
                >
                  <Heart className={`w-5 h-5 ${isLiked ? 'fill-current' : ''}`} />
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  aria-label="Share product"
                  className="p-4 rounded-xl bg-white/5 border border-white/10 text-[#A0A3A8] hover:border-white/20 transition-all"
                >
                  <Share2 className="w-5 h-5" />
                </motion.button>
              </motion.div>

              {/* Features */}
              <motion.div variants={staggerItem}>
                <GlassContainer className="p-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    {[
                      { icon: Truck, label: 'Free Shipping' },
                      { icon: Shield, label: 'Authenticity' },
                      { icon: RefreshCw, label: 'Easy Returns' },
                    ].map((item, index) => (
                      <div key={index} className="flex flex-col items-center gap-2">
                        <item.icon className="w-5 h-5 text-[#D4AF37]" />
                        <span className="text-xs text-[#A0A3A8]">{item.label}</span>
                      </div>
                    ))}
                  </div>
                </GlassContainer>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </main>
    </motion.div>
  );
};

export default LuxuryProduct;
