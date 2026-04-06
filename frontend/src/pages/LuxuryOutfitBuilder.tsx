/**
 * LuxuryOutfitBuilder - Premium outfit builder page
 * Features: Interactive outfit creation, AI suggestions, luxury styling
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  Wand2, 
  Plus, 
  X, 
  ChevronRight,
  Crown,
  RefreshCw,
  Save,
} from 'lucide-react';
import { 
  TopNavigationBar,
  GoldButton,
  GoldFAB,
  GlassContainer,
  ProductCard,
  LuxuryCard,
} from '@/components/luxury';
import { fadeUpVariants, pageVariants, fadeVariants, transitionFast } from '@/motion';

// Mock categories and items
const categories = ['Tops', 'Bottoms', 'Outerwear', 'Shoes', 'Accessories', 'Bags'];

const availableItems = [
  { id: '1', name: 'Silk Blouse', brand: 'AURUM', price: 450, image: 'https://images.unsplash.com/photo-1485968579580-b6d095142e6e?w=400', category: 'Tops' },
  { id: '2', name: 'Tailored Trousers', brand: 'MAISON NOIR', price: 380, image: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=400', category: 'Bottoms' },
  { id: '3', name: 'Cashmere Coat', brand: 'LUXE ATELIER', price: 1200, image: 'https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=400', category: 'Outerwear' },
  { id: '4', name: 'Leather Loafers', brand: 'CHRONOS', price: 520, image: 'https://images.unsplash.com/photo-1533837637406-70a3e1c3c7db?w=400', category: 'Shoes' },
  { id: '5', name: 'Gold Watch', brand: 'CHRONOS', price: 2800, image: 'https://images.unsplash.com/photo-1523275335687-8508644d6c67?w=400', category: 'Accessories' },
  { id: '6', name: 'Leather Tote', brand: 'LUXE ATELIER', price: 890, image: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400', category: 'Bags' },
];

const aiSuggestions = [
  { id: 's1', name: 'Evening Gala', items: 4, style: 'Formal' },
  { id: 's2', name: 'Business Meeting', items: 5, style: 'Professional' },
  { id: 's3', name: 'Weekend Brunch', items: 3, style: 'Casual' },
];

const LuxuryOutfitBuilder = () => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [outfitItems, setOutfitItems] = useState<typeof availableItems>([]);
  const [showItemPicker, setShowItemPicker] = useState(false);

  const totalPrice = outfitItems.reduce((sum, item) => sum + item.price, 0);

  const addItem = (item: typeof availableItems[0]) => {
    if (!outfitItems.find(i => i.id === item.id)) {
      setOutfitItems([...outfitItems, item]);
    }
    setShowItemPicker(false);
    setSelectedCategory(null);
  };

  const removeItem = (itemId: string) => {
    setOutfitItems(outfitItems.filter(item => item.id !== itemId));
  };

  const filteredItems = selectedCategory 
    ? availableItems.filter(item => item.category === selectedCategory)
    : availableItems;

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
        actions={
          <div className="flex items-center gap-3">
            <GoldButton variant="ghost" size="sm" icon={<Save className="w-4 h-4" />}>
              Save
            </GoldButton>
          </div>
        }
      />

      <main className="pt-20 pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <motion.div
            variants={fadeUpVariants}
            initial="hidden"
            animate="visible"
            className="text-center mb-12"
          >
            <div className="flex items-center justify-center gap-2 mb-2">
              <Crown className="w-5 h-5 text-[#D4AF37]" />
              <span className="text-sm text-[#D4AF37] uppercase tracking-wider">Outfit Builder</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-display font-bold text-[#F5F5F5] mb-4">
              Create Your Look
            </h1>
            <p className="text-[#A0A3A8] max-w-xl mx-auto">
              Build your perfect outfit from our curated collection
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Outfit Preview */}
            <div className="lg:col-span-2">
              <motion.div
                variants={fadeUpVariants}
                initial="hidden"
                animate="visible"
              >
                <GlassContainer className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-display font-semibold text-[#F5F5F5]">Your Outfit</h2>
                    <span className="text-[#D4AF37] font-semibold">${totalPrice.toLocaleString()}</span>
                  </div>

                  {/* Outfit Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {/* Add item button */}
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setShowItemPicker(true)}
                      className="aspect-square rounded-xl border-2 border-dashed border-white/20 flex flex-col items-center justify-center gap-2 text-[#A0A3A8] hover:border-[#D4AF37]/50 hover:text-[#D4AF37] transition-colors"
                    >
                      <Plus className="w-6 h-6" />
                      <span className="text-sm">Add Item</span>
                    </motion.button>

                    {/* Selected items */}
                    <AnimatePresence>
                      {outfitItems.map((item) => (
                        <motion.div
                          key={item.id}
                          variants={fadeVariants}
                          initial="hidden"
                          animate="visible"
                          exit="exit"
                          className="relative aspect-square rounded-xl overflow-hidden bg-[#151925] border border-white/[0.06] group"
                        >
                          <img src={item.image} alt={item.name} className="w-full h-full object-cover" />
                          <div className="absolute inset-0 bg-gradient-to-t from-[#0B0F1A]/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                          <button
                            onClick={() => removeItem(item.id)}
                            aria-label={`Remove ${item.name}`}
                            className="absolute top-2 right-2 p-1 bg-black/40 rounded-full text-white opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <X className="w-4 h-4" />
                          </button>
                          <div className="absolute bottom-2 left-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <p className="text-xs text-[#D4AF37]">{item.brand}</p>
                            <p className="text-sm text-[#F5F5F5] truncate">{item.name}</p>
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>

                  {/* Category quick-add */}
                  <div className="flex flex-wrap gap-2 mt-6">
                    {categories.map((cat) => (
                      <button
                        key={cat}
                        onClick={() => {
                          setSelectedCategory(cat);
                          setShowItemPicker(true);
                        }}
                        className="px-3 py-1.5 text-xs bg-white/5 border border-white/10 rounded-lg text-[#A0A3A8] hover:border-[#D4AF37]/30 hover:text-[#D4AF37] transition-colors"
                      >
                        + {cat}
                      </button>
                    ))}
                  </div>
                </GlassContainer>
              </motion.div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* AI Suggestions */}
              <motion.div
                variants={fadeUpVariants}
                initial="hidden"
                animate="visible"
              >
                <LuxuryCard variant="gold" padding="md">
                  <div className="flex items-center gap-2 mb-4">
                    <Sparkles className="w-5 h-5 text-[#D4AF37]" />
                    <h3 className="text-lg font-display font-semibold text-[#F5F5F5]">AI Suggestions</h3>
                  </div>
                  <div className="space-y-3">
                    {aiSuggestions.map((suggestion) => (
                      <button
                        key={suggestion.id}
                        className="w-full flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors group"
                      >
                        <div className="text-left">
                          <p className="text-sm font-medium text-[#F5F5F5]">{suggestion.name}</p>
                          <p className="text-xs text-[#A0A3A8]">{suggestion.items} items • {suggestion.style}</p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-[#A0A3A8] group-hover:text-[#D4AF37] transition-colors" />
                      </button>
                    ))}
                  </div>
                  <GoldButton variant="ghost" size="sm" className="w-full mt-4" icon={<Wand2 className="w-4 h-4" />}>
                    Generate New Look
                  </GoldButton>
                </LuxuryCard>
              </motion.div>

              {/* Style Tips */}
              <motion.div
                variants={fadeUpVariants}
                initial="hidden"
                animate="visible"
                transition={transitionFast}
              >
                <GlassContainer className="p-4">
                  <h3 className="text-sm font-semibold text-[#F5F5F5] mb-3">Style Tips</h3>
                  <ul className="space-y-2 text-xs text-[#A0A3A8]">
                    <li className="flex items-start gap-2">
                      <span className="text-[#D4AF37]">•</span>
                      Pair neutral tones with one statement piece
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#D4AF37]">•</span>
                      Balance proportions for a cohesive look
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#D4AF37]">•</span>
                      Add accessories to elevate your style
                    </li>
                  </ul>
                </GlassContainer>
              </motion.div>
            </div>
          </div>
        </div>
      </main>

      {/* Item Picker Modal */}
      <AnimatePresence>
        {showItemPicker && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowItemPicker(false)}
          >
            <motion.div
              variants={fadeVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-2xl max-h-[80vh] overflow-hidden bg-[#151925] rounded-2xl border border-white/[0.06] shadow-2xl"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-[#D4AF37]" />
                  <h3 className="text-lg font-display font-semibold text-[#F5F5F5]">Select Items</h3>
                </div>
                <button
                  onClick={() => setShowItemPicker(false)}
                  aria-label="Close"
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5 text-[#A0A3A8]" />
                </button>
              </div>

              {/* Category filters */}
              <div className="flex gap-2 p-4 overflow-x-auto border-b border-white/[0.06]">
                <button
                  onClick={() => setSelectedCategory(null)}
                  className={`px-3 py-1.5 text-sm rounded-lg whitespace-nowrap transition-colors ${
                    !selectedCategory 
                      ? 'bg-[#D4AF37] text-[#0B0F1A]' 
                      : 'bg-white/5 text-[#A0A3A8] hover:bg-white/10'
                  }`}
                >
                  All
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-3 py-1.5 text-sm rounded-lg whitespace-nowrap transition-colors ${
                      selectedCategory === cat 
                        ? 'bg-[#D4AF37] text-[#0B0F1A]' 
                        : 'bg-white/5 text-[#A0A3A8] hover:bg-white/10'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Items grid */}
              <div className="p-4 overflow-y-auto max-h-[50vh]">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {filteredItems.map((item) => (
                    <motion.button
                      key={item.id}
                      whileHover={{ y: -2 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => addItem(item)}
                      disabled={outfitItems.some(i => i.id === item.id)}
                      className={`text-left rounded-xl overflow-hidden border transition-all ${
                        outfitItems.some(i => i.id === item.id)
                          ? 'border-[#D4AF37]/30 opacity-50 cursor-not-allowed'
                          : 'border-white/[0.06] hover:border-[#D4AF37]/30'
                      }`}
                    >
                      <div className="aspect-square bg-[#0B0F1A]">
                        <img src={item.image} alt={item.name} className="w-full h-full object-cover" />
                      </div>
                      <div className="p-3 bg-[#151925]">
                        <p className="text-xs text-[#D4AF37]">{item.brand}</p>
                        <p className="text-sm text-[#F5F5F5] truncate">{item.name}</p>
                        <p className="text-sm font-semibold text-[#F5F5F5] mt-1">${item.price}</p>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB */}
      {outfitItems.length > 0 && (
        <GoldFAB 
          icon={<Sparkles className="w-5 h-5" />}
          label={`Build Outfit (${outfitItems.length})`}
          position="bottom-center"
        />
      )}
    </motion.div>
  );
};

export default LuxuryOutfitBuilder;
