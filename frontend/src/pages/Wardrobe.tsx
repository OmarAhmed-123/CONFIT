import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Plus, Search, Tag, Shirt, MoreVertical, Sparkles, Upload } from 'lucide-react';
import { toast } from 'sonner';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AddItemModal, type WardrobeItemInput } from '@/components/wardrobe/AddItemModal';
import WardrobeAnalyticsPanel from '@/components/wardrobe/WardrobeAnalyticsPanel';
import { useWardrobeViewModel, type WardrobeItemData } from '@/viewmodels/useWardrobeViewModel';
import { getAuthToken } from '@/lib/auth';
import { createStaggerTransition, transitionStandard } from '@/motion';
import { GlassCard } from '@/components/shared';
import { ScrollReveal } from '@/components/motion/ScrollReveal';

export default function WardrobePage() {
  const {
    items,
    isLoading,
    isUploading,
    searchQuery,
    selectedCategory,
    categories,
    setSearchQuery,
    setSelectedCategory,
    addItem,
    analyzeImage, // Returns { category, color, tags }
    checkDuplicate, // Returns { hasDuplicates, matches }
    generateOutfitIdea,
    listForResale
  } = useWardrobeViewModel();

  const [showAddModal, setShowAddModal] = useState(false);
  const [localUploading, setLocalUploading] = useState(false); // Local state for file reading UI feedback
  const [displayItems, setDisplayItems] = useState(items);
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  useEffect(() => {
    setDisplayItems(items);
  }, [items]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLocalUploading(true);
    const toastId = toast.loading('Analyzing your item...');

    try {
      // 1. Read file for preview
      const reader = new FileReader();
      const imageUrl = await new Promise<string>((resolve) => {
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.readAsDataURL(file);
      });

      // 2. Auto-tag via ViewModel
      const tags = await analyzeImage(file);

      const newName = `New ${tags.color} ${tags.category}`;
      const input: WardrobeItemInput = {
        name: newName,
        category: tags.category,
        color: tags.color,
        brand: 'Unknown',
        image: imageUrl,
        tags: tags.tags
      };

      // 3. Check duplicate
      const duplicateResult = await checkDuplicate({ ...input, brand: undefined }); // brand is 'Unknown' so might not match strict check, but passing what we have

      if (duplicateResult?.hasDuplicates && duplicateResult.matches && duplicateResult.matches.length > 0) {
        toast.dismiss(toastId);
        toast.warning('Potential Duplicate Detected', {
          description: `You may already have a similar ${tags.color} ${tags.category}.`,
          action: {
            label: 'Add Anyway',
            onClick: () => {
              addItem(input);
            },
          },
        });
        setLocalUploading(false);
        return;
      }

      // 4. Add item
      await addItem(input);
      toast.dismiss(toastId);
      // Success toast is handled by addItem in VM, but we can add more detail if needed.
      // VM toast is generic "Item added".

    } catch (error) {
      console.error("Upload failed", error);
      toast.dismiss(toastId);
      toast.error("Failed to analyze image");
    } finally {
      setLocalUploading(false);
    }
  };


  const handleAddItemModal = async (input: WardrobeItemInput) => {
    // Check duplicates before saving? The modal is manual entry.
    // The original code checked duplicates here too.
    const duplicateResult = await checkDuplicate(input);

    if (duplicateResult?.hasDuplicates) {
      toast.error('Duplicate Item', {
        description: 'You already have an item with this name and brand!',
      });
      return;
    }

    await addItem(input);
    setShowAddModal(false);
  };

  const handleResell = async (id: string, price?: number) => {
    await listForResale(id, price);
  };

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
            <ScrollReveal className="flex-1">
              <div className="inline-flex items-center gap-2 bg-muted text-muted-foreground px-4 py-2 rounded-full mb-4">
                <Shirt className="h-4 w-4" />
                <span className="text-sm font-medium">Digital Closet</span>
              </div>
              <h1 className="heading-hero mb-2">My Wardrobe</h1>
              <p className="text-muted-foreground">
                Digitize your closet and get smart outfit suggestions
              </p>
            </ScrollReveal>
            <div className="flex gap-2">
              <Button variant="outline" className="relative" disabled={isUploading || localUploading}>
                <input
                  type="file"
                  accept="image/*"
                  aria-label="Upload wardrobe item photo"
                  className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                  onChange={handleFileUpload}
                  disabled={isUploading || localUploading}
                />
                <Upload className="h-4 w-4 mr-2" />
                {isUploading || localUploading ? 'Analyzing...' : 'Quick Upload'}
              </Button>
              <Button variant="hero" onClick={() => setShowAddModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Item
              </Button>
            </div>
          </div>

          {/* Analytics Panel */}
          <div className="mb-8">
            <WardrobeAnalyticsPanel />
          </div>

          {/* Search & Filters */}
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search your wardrobe..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-12 h-12"
                aria-label="Search wardrobe"
              />
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex gap-2 overflow-x-auto pb-4 mb-6 scrollbar-hide">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${selectedCategory === category
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80 text-muted-foreground'
                  }`}
              >
                {category === 'all' ? 'All' : category.charAt(0).toUpperCase() + category.slice(1)}
              </button>
            ))}
          </div>

          {/* Wardrobe Grid */}
          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="aspect-[3/4] bg-muted animate-pulse rounded-lg" />
              ))}
            </div>
          ) : displayItems.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
              {displayItems.map((item, index) => (
                <WardrobeItemCard
                  key={item.id}
                  item={item}
                  index={index}
                  onResell={handleResell}
                  draggable
                  onDragStart={() => setDragIndex(index)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => {
                    if (dragIndex === null || dragIndex === index) return;
                    setDisplayItems((prev) => {
                      const next = [...prev];
                      const [moved] = next.splice(dragIndex, 1);
                      next.splice(index, 0, moved);
                      return next;
                    });
                    setDragIndex(null);
                  }}
                />
              ))}

              {/* Add Item Card */}
              <motion.button
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={createStaggerTransition(displayItems.length)}
                onClick={() => setShowAddModal(true)}
                className="aspect-[3/4] rounded-lg border-2 border-dashed border-border hover:border-accent flex flex-col items-center justify-center gap-3 transition-colors"
              >
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                  <Plus className="h-6 w-6 text-muted-foreground" />
                </div>
                <span className="text-sm text-muted-foreground">Add Item</span>
              </motion.button>
            </div>
          ) : (
            <div className="text-center py-16">
              <Shirt className="h-16 w-16 text-muted-foreground/30 mx-auto mb-4" />
              <h3 className="font-semibold text-lg mb-2">No items found</h3>
              <p className="text-muted-foreground mb-6">
                {searchQuery
                  ? `No items match "${searchQuery}"`
                  : "Start building your digital wardrobe"
                }
              </p>
              <Button variant="hero" onClick={() => setShowAddModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Item
              </Button>
            </div>
          )}

          {/* AI Suggestion Banner */}
          <div className="mt-12 bg-gradient-hero rounded-xl p-8 text-primary-foreground">
            <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
              <div className="w-16 h-16 rounded-full bg-accent/20 flex items-center justify-center shrink-0">
                <Sparkles className="h-8 w-8 text-accent" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-xl mb-2">Get Personalized Outfit Ideas</h3>
                <p className="text-primary-foreground/80 mb-4">
                  Our AI can analyze your wardrobe and suggest new outfits using what you already own,
                  plus recommend pieces that would complement your existing collection.
                </p>
                <Button variant="gold" onClick={generateOutfitIdea}>
                  Generate Outfit Ideas
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add Item Modal */}
      <AddItemModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSave={handleAddItemModal}
      />
    </MainLayout>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <GlassCard className="p-4">
      <p className="text-sm text-muted-foreground mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </GlassCard>
  );
}

function WardrobeItemCard({
  item,
  index,
  onResell,
  draggable,
  onDragStart,
  onDragOver,
  onDrop
}: {
  item: WardrobeItemData;
  index: number;
  onResell: (id: string, price?: number) => void;
  draggable?: boolean;
  onDragStart?: () => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDrop?: () => void;
}) {
  const token = getAuthToken();
  const canResell = Boolean(token);

  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={createStaggerTransition(index, 0.05, 0.3, transitionStandard)}
      className="group relative"
      draggable={Boolean(draggable)}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart?.();
      }}
      onDragOver={(e) => onDragOver?.(e)}
      onDrop={(e) => {
        e.preventDefault();
        onDrop?.();
      }}
    >
      <div className="aspect-[3/4] rounded-lg overflow-hidden bg-muted mb-3">
        <img
          src={item.image}
          alt={item.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />

        {/* Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-charcoal/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

        {/* Actions */}
        <div className="absolute bottom-3 left-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="gold" size="sm" className="flex-1 text-xs">
            Style This
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-xs"
            disabled={!canResell}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onResell(item.id, item.price);
            }}
          >
            Resell
          </Button>
          <Button variant="secondary" size="icon" aria-label="Item actions">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </div>

        {/* Color Tag */}
        <div className="absolute top-3 left-3">
          <span className="inline-flex items-center gap-1 bg-background/90 backdrop-blur-sm text-xs px-2 py-1 rounded-full">
            <Tag className="h-3 w-3" />
            {item.color}
          </span>
        </div>
      </div>

      <div>
        <h3 className="font-medium text-sm group-hover:text-accent transition-colors">
          {item.name}
        </h3>
        {item.brand && (
          <p className="text-xs text-muted-foreground">{item.brand}</p>
        )}
      </div>
    </motion.article>
  );
}
