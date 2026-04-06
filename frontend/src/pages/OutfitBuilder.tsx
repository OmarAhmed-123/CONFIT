import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, Save, Share2, DollarSign, Sparkles, Layers, Shirt, ShoppingBag } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { useOutfitBuilderViewModel, type OutfitSlot, type OutfitItem } from '@/viewmodels/useOutfitBuilderViewModel';

export default function OutfitBuilderPage() {
  const { isAuthenticated } = useAuth();

  const {
    slots,
    budget,
    totalPrice,
    styleScore,
    filledSlotsCount,
    activeSlot,
    isSaving,
    isLoadingData,
    catalogItems,
    wardrobeItems,

    setBudget,
    setActiveSlot,
    selectItem,
    removeItem,
    clearAll,
    saveOutfit,
    getItemsForSlot, // Helper to get filtered items
  } = useOutfitBuilderViewModel();

  // Local state for the selection panel (source toggle)
  const [itemSource, setItemSource] = useState<'catalog' | 'wardrobe'>('catalog');

  const handleSourceChange = (source: 'catalog' | 'wardrobe') => {
    setItemSource(source);
  };

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
            <div>
              <div className="inline-flex items-center gap-2 bg-charcoal/5 text-charcoal px-4 py-2 rounded-full mb-4">
                <Layers className="h-4 w-4" />
                <span className="text-sm font-medium">Mix & Match</span>
              </div>
              <h1 className="heading-hero mb-2">Outfit Builder</h1>
              <p className="text-muted-foreground">
                Create complete looks by mixing pieces across brands and your own wardrobe
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" onClick={clearAll} disabled={filledSlotsCount === 0}>
                Clear All
              </Button>
              <Button variant="hero" onClick={saveOutfit} disabled={isSaving || filledSlotsCount === 0}>
                <Save className="h-4 w-4 mr-2" />
                {isSaving ? 'Saving...' : 'Save Outfit'}
              </Button>
            </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Left: Outfit Builder */}
            <div className="lg:col-span-2 space-y-6">
              {/* Budget Tracker */}
              <div className="bg-card rounded-xl border border-border p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                      <DollarSign className="h-5 w-5 text-accent" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Budget</p>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">$</span>
                        <input
                          type="number"
                          value={budget}
                          onChange={(e) => setBudget(Number(e.target.value))}
                          className="w-20 bg-transparent border-b border-border focus:border-accent outline-none font-semibold"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Current Total</p>
                    <p className={`font-semibold text-lg ${totalPrice > budget ? 'text-destructive' : 'text-foreground'}`}>
                      ${totalPrice}
                    </p>
                  </div>
                </div>
                <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`absolute left-0 top-0 h-full rounded-full transition-all duration-500 ${totalPrice > budget ? 'bg-destructive' : 'bg-accent'
                      }`}
                    style={{ width: `${Math.min((totalPrice / budget) * 100, 100)}%` }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                  <span>${totalPrice} spent</span>
                  <span>${Math.max(budget - totalPrice, 0)} remaining</span>
                </div>
              </div>

              {/* Outfit Slots */}
              <div className="space-y-4">
                {slots.map((slot) => (
                  <motion.div
                    key={slot.position}
                    layout
                    className={`bg-card rounded-xl border transition-colors ${activeSlot === slot.position ? 'border-accent ring-1 ring-accent' : 'border-border'
                      }`}
                  >
                    {slot.item ? (
                      <div className="flex items-center gap-4 p-4">
                        <div className="w-20 h-24 rounded-lg overflow-hidden bg-muted shrink-0 relative">
                          <img
                            src={slot.item.image}
                            alt={slot.item.name}
                            className="w-full h-full object-cover"
                          />
                          {slot.item.source === 'wardrobe' && (
                            <div className="absolute top-1 right-1 bg-black/50 rounded-full p-1" title="From Wardrobe">
                              <Shirt className="h-3 w-3 text-white" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-label text-muted-foreground">{slot.label}</p>
                          <h4 className="font-medium truncate">{slot.item.name}</h4>
                          <p className="text-sm text-muted-foreground">{slot.item.brand}</p>
                          <p className="font-semibold mt-1">${slot.item.price}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => setActiveSlot(slot.position)}
                          >
                            <Plus className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => removeItem(slot.position)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setActiveSlot(slot.position === activeSlot ? null : slot.position)}
                        className="w-full flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors rounded-xl group"
                      >
                        <div className="w-20 h-24 rounded-lg bg-muted border-2 border-dashed border-border group-hover:border-accent flex items-center justify-center transition-colors">
                          <Plus className="h-6 w-6 text-muted-foreground group-hover:text-accent transition-colors" />
                        </div>
                        <div className="text-left">
                          <p className="font-medium">{slot.label}</p>
                          <p className="text-sm text-muted-foreground">Click to add</p>
                        </div>
                      </button>
                    )}

                    {/* Product Selection Panel */}
                    <AnimatePresence>
                      {activeSlot === slot.position && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="border-t border-border overflow-hidden"
                        >
                          <div className="p-4 bg-muted/10">
                            <div className="flex mb-4 gap-2">
                              <button
                                onClick={() => handleSourceChange('catalog')}
                                className={`flex-1 py-2 text-sm font-medium rounded-md transition-all flex items-center justify-center gap-2 ${itemSource === 'catalog' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:bg-muted'}`}
                              >
                                <ShoppingBag className="h-4 w-4" />
                                Catalog
                              </button>
                              <button
                                onClick={() => handleSourceChange('wardrobe')}
                                className={`flex-1 py-2 text-sm font-medium rounded-md transition-all flex items-center justify-center gap-2 ${itemSource === 'wardrobe' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:bg-muted'}`}
                              >
                                <Shirt className="h-4 w-4" />
                                My Wardrobe
                              </button>
                            </div>

                            {isLoadingData ? (
                              <div className="flex justify-center p-8">
                                <span className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                              </div>
                            ) : (
                              <>
                                {itemSource === 'wardrobe' && !isAuthenticated && (
                                  <div className="text-center p-4 text-muted-foreground text-sm">
                                    Sign in to access your wardrobe items.
                                  </div>
                                )}

                                {getItemsForSlot(slot.position, itemSource).length > 0 ? (
                                  <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 gap-3 max-h-60 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
                                    {getItemsForSlot(slot.position, itemSource).map((product) => (
                                      <button
                                        key={product.id}
                                        onClick={() => selectItem(slot.position, { ...product, source: itemSource })} // Ensure source is set correctly
                                        className="aspect-[3/4] rounded-lg overflow-hidden border-2 border-transparent hover:border-accent transition-colors relative group"
                                        title={`${product.name} - $${product.price}`}
                                      >
                                        <img
                                          src={product.image}
                                          alt={product.name}
                                          className="w-full h-full object-cover"
                                        />
                                        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-1 pt-4 opacity-0 group-hover:opacity-100 transition-opacity">
                                          <p className="text-[10px] text-white truncate text-center">${product.price}</p>
                                        </div>
                                      </button>
                                    ))}
                                  </div>
                                ) : (
                                  <div className="text-center p-8 text-muted-foreground text-sm">
                                    No items found in {itemSource} for this slot.
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Right: Outfit Preview & Stats */}
            <div className="space-y-6">
              {/* Outfit Preview */}
              <div className="bg-card rounded-xl border border-border p-6 sticky top-24">
                <h3 className="font-semibold mb-4">Outfit Preview</h3>
                <div className="aspect-[3/4] bg-muted rounded-lg flex items-center justify-center mb-4 overflow-hidden relative">
                  {filledSlotsCount > 0 ? (
                    <div className="grid grid-cols-2 gap-2 p-4 w-full h-full">
                      {slots.filter(s => s.item).map((slot) => (
                        <div key={slot.position} className="rounded-lg overflow-hidden bg-white/5 relative">
                          <img
                            src={slot.item!.image}
                            alt={slot.item!.name}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/60 rounded text-[10px] text-white uppercase font-bold">
                            {slot.label}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center text-muted-foreground">
                      <Layers className="h-12 w-12 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">Add items to see your outfit</p>
                    </div>
                  )}
                </div>

                {/* Stats */}
                {filledSlotsCount > 0 && (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Style Score</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent rounded-full transition-all duration-500"
                            style={{ width: `${styleScore}%` }}
                          />
                        </div>
                        <span className="font-medium">{styleScore}%</span>
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Items</span>
                      <span className="font-medium">{filledSlotsCount} / {slots.length}</span>
                    </div>
                    <div className="flex justify-between items-center border-t border-border pt-2 mt-2">
                      <span className="text-sm font-medium">Total</span>
                      <span className="font-bold text-lg">${totalPrice}</span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="space-y-3 mt-6">
                  <Button variant="hero" className="w-full" disabled={filledSlotsCount === 0}>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Try On Complete Outfit
                  </Button>
                  <Button variant="outline" className="w-full" disabled={filledSlotsCount === 0}>
                    <Share2 className="h-4 w-4 mr-2" />
                    Share This Look
                  </Button>
                </div>

                {/* AI Suggestions */}
                <div className="mt-4 bg-accent/5 border border-accent/20 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Sparkles className="h-5 w-5 text-accent shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-sm mb-1">Style Suggestion</p>
                      <p className="text-xs text-muted-foreground">
                        {filledSlotsCount === 0
                          ? "Start by adding a top or bottom to get personalized suggestions."
                          : "Consider adding a statement accessory to elevate this look. A gold necklace would complement beautifully."
                        }
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout >
  );
}
