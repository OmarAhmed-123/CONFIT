/**
 * LuxuryHome - Premium dark luxury home page
 * Features: Hero section, featured products, curated outfits
 */

import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, TrendingUp, Crown } from 'lucide-react';
import { 
  ConfitLogo, 
  BrandTagline, 
  LuxuryDivider,
  GoldButton,
  ProductCard,
  OutfitPreviewCard,
  TopNavigationBar,
  NavigationBar,
  GlassContainer,
} from '@/components/luxury';
import { staggerContainer, staggerItem, fadeUpVariants, pageVariants, createStaggerTransition, gestureFabFloat } from '@/motion';

// Mock data for demonstration
const featuredProducts = [
  { id: '1', name: 'Silk Evening Dress', brand: 'MAISON NOIR', price: 2450, originalPrice: 3200, image: 'https://images.unsplash.com/photo-1595777457583-95e397a5e5c7?w=400', category: 'Dresses', isPremium: true },
  { id: '2', name: 'Cashmere Overcoat', brand: 'AURUM', price: 1890, image: 'https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=400', category: 'Outerwear' },
  { id: '3', name: 'Leather Tote Bag', brand: 'LUXE ATELIER', price: 890, originalPrice: 1100, image: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400', category: 'Bags' },
  { id: '4', name: 'Signature Watch', brand: 'CHRONOS', price: 4500, image: 'https://images.unsplash.com/photo-1523275335687-8508644d6c67?w=400', category: 'Accessories', isPremium: true },
];

const curatedOutfits = [
  {
    id: '1',
    name: 'Evening Elegance',
    style: 'Formal',
    occasion: 'Evening',
    totalPrice: 4890,
    items: [
      { id: '1', name: 'Silk Dress', image: 'https://images.unsplash.com/photo-1595777457583-95e397a5e5c7?w=200', category: 'Dress' },
      { id: '2', name: 'Heels', image: 'https://images.unsplash.com/photo-1543163524-1f5ba7b0c5d8?w=200', category: 'Shoes' },
      { id: '3', name: 'Clutch', image: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=200', category: 'Bag' },
      { id: '4', name: 'Earrings', image: 'https://images.unsplash.com/photo-1535632066927-ab7c9ab35995?w=200', category: 'Jewelry' },
    ],
  },
  {
    id: '2',
    name: 'Weekend Luxe',
    style: 'Casual',
    occasion: 'Day',
    totalPrice: 2340,
    items: [
      { id: '1', name: 'Blazer', image: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=200', category: 'Outerwear' },
      { id: '2', name: 'Trousers', image: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=200', category: 'Pants' },
      { id: '3', name: 'Loafers', image: 'https://images.unsplash.com/photo-1533837637406-70a3e1c3c7db?w=200', category: 'Shoes' },
    ],
  },
];

const LuxuryHome = () => {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className="min-h-screen bg-[#0B0F1A]"
    >
      {/* Top Navigation */}
      <TopNavigationBar 
        transparent 
        actions={
          <div className="flex items-center gap-4">
            <GoldButton size="sm" variant="outline">
              Sign In
            </GoldButton>
          </div>
        }
      />

      {/* Hero Section */}
      <section className="relative min-h-[85vh] flex items-center justify-center overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#0B0F1A] via-[#10141C] to-[#0B0F1A]" />
        
        {/* Subtle grid pattern */}
        <div 
          className="absolute inset-0 opacity-[0.02] bg-grid-pattern"
        />
        
        {/* Gold glow accent */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-[#D4AF37]/5 rounded-full blur-[120px]" />
        
        {/* Content */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="relative z-10 text-center px-6 max-w-4xl mx-auto"
        >
          {/* Logo */}
          <motion.div variants={staggerItem} className="mb-8">
            <ConfitLogo size="xl" animated={false} />
          </motion.div>
          
          {/* Tagline */}
          <motion.div variants={staggerItem}>
            <BrandTagline className="mb-12" />
          </motion.div>
          
          {/* Main heading */}
          <motion.h1 
            variants={staggerItem}
            className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-display font-bold text-[#F5F5F5] mb-6 leading-tight"
          >
            Discover Your
            <br />
            <span className="text-gradient-gold">Signature Style</span>
          </motion.h1>
          
          {/* Description */}
          <motion.p 
            variants={staggerItem}
            className="text-lg sm:text-xl text-[#A0A3A8] max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            AI-powered styling meets luxury fashion. Curated outfits, 
            personalized recommendations, and exclusive collections.
          </motion.p>
          
          {/* CTA Buttons */}
          <motion.div 
            variants={staggerItem}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <GoldButton size="lg" icon={<Sparkles className="w-5 h-5" />}>
              Build Your Outfit
            </GoldButton>
            <GoldButton size="lg" variant="outline" icon={<ArrowRight className="w-5 h-5" />} iconPosition="right">
              Explore Collection
            </GoldButton>
          </motion.div>
        </motion.div>
        
        {/* Scroll indicator */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={createStaggerTransition(12)}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={gestureFabFloat.transition}
            className="w-6 h-10 border-2 border-white/20 rounded-full flex items-start justify-center p-1"
          >
            <div className="w-1 h-2 bg-[#D4AF37] rounded-full" />
          </motion.div>
        </motion.div>
      </section>

      {/* Featured Products Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <motion.div
            variants={fadeUpVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="flex items-center justify-between mb-12"
          >
            <div>
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-[#D4AF37]" />
                <span className="text-sm text-[#D4AF37] uppercase tracking-wider">Featured</span>
              </div>
              <h2 className="text-3xl sm:text-4xl font-display font-bold text-[#F5F5F5]">
                Curated for You
              </h2>
            </div>
            <GoldButton variant="ghost" icon={<ArrowRight className="w-4 h-4" />} iconPosition="right">
              View All
            </GoldButton>
          </motion.div>

          {/* Products Grid */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6"
          >
            {featuredProducts.map((product) => (
              <motion.div key={product.id} variants={staggerItem}>
                <ProductCard {...product} />
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Luxury Divider */}
      <div className="max-w-4xl mx-auto px-6">
        <LuxuryDivider />
      </div>

      {/* Curated Outfits Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <motion.div
            variants={fadeUpVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <div className="flex items-center justify-center gap-2 mb-2">
              <Crown className="w-5 h-5 text-[#D4AF37]" />
              <span className="text-sm text-[#D4AF37] uppercase tracking-wider">AI Curated</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-display font-bold text-[#F5F5F5] mb-4">
              Complete Looks
            </h2>
            <p className="text-[#A0A3A8] max-w-xl mx-auto">
              Expertly styled outfits tailored to your preferences and occasions
            </p>
          </motion.div>

          {/* Outfits Grid */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto"
          >
            {curatedOutfits.map((outfit) => (
              <motion.div key={outfit.id} variants={staggerItem}>
                <OutfitPreviewCard {...outfit} />
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid md:grid-cols-3 gap-6"
          >
            {[
              { title: 'AI Stylist', desc: 'Personalized recommendations powered by advanced AI', icon: Sparkles },
              { title: 'Virtual Try-On', desc: 'See how items look on you before purchasing', icon: Crown },
              { title: 'Curated Boxes', desc: 'Handpicked selections delivered to your door', icon: TrendingUp },
            ].map((feature, index) => (
              <motion.div key={index} variants={staggerItem}>
                <GlassContainer className="p-6 text-center hover:bg-white/[0.05] transition-colors cursor-pointer">
                  <feature.icon className="w-8 h-8 text-[#D4AF37] mx-auto mb-4" />
                  <h3 className="text-lg font-display font-semibold text-[#F5F5F5] mb-2">{feature.title}</h3>
                  <p className="text-sm text-[#A0A3A8]">{feature.desc}</p>
                </GlassContainer>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Bottom Navigation */}
      <NavigationBar variant="glass" />
      
      {/* Spacer for bottom nav */}
      <div className="h-20" />
    </motion.div>
  );
};

export default LuxuryHome;
