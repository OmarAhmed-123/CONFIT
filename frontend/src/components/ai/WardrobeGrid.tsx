/**
 * CONFIT Frontend - Wardrobe Grid Component
 * MY CLOSET virtual wardrobe interface
 */

'use client';

import React, { useState } from 'react';
import { useWardrobe } from '@/hooks/useWardrobe';
import { 
  Plus, Heart, Trash2, Loader2, Upload, 
  Shirt, ChevronRight, AlertCircle, Sparkles 
} from 'lucide-react';

interface WardrobeGridProps {
  onSelectItem?: (itemId: string) => void;
  showOutfitSuggestions?: boolean;
}

export function WardrobeGrid({ onSelectItem, showOutfitSuggestions = true }: WardrobeGridProps) {
  const {
    items,
    isLoading,
    isUploading,
    error,
    totalItems,
    quotaRemaining,
    outfitSuggestions,
    addItem,
    deleteItem,
    suggestOutfits,
    checkDuplicates,
  } = useWardrobe();

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [newItemCategory, setNewItemCategory] = useState('tops');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [showOutfits, setShowOutfits] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const categories = [
    { id: 'tops', label: 'Tops', icon: 'shirt' },
    { id: 'bottoms', label: 'Bottoms', icon: 'pants' },
    { id: 'dresses', label: 'Dresses', icon: 'dress' },
    { id: 'shoes', label: 'Shoes', icon: 'shoe' },
    { id: 'accessories', label: 'Accessories', icon: 'accessory' },
  ];

  const filteredItems = selectedCategory
    ? items.filter(item => item.category === selectedCategory)
    : items;

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setUploadPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!uploadFile) return;

    const item = await addItem(uploadFile, newItemName || undefined, newItemCategory || undefined);
    
    if (item) {
      setShowUpload(false);
      setUploadFile(null);
      setUploadPreview(null);
      setNewItemName('');
      setNewItemCategory('tops');
    }
  };

  const handleDelete = async (itemId: string) => {
    setDeletingId(itemId);
    await deleteItem(itemId);
    setDeletingId(null);
  };

  const handleSuggestOutfits = async () => {
    await suggestOutfits();
    setShowOutfits(true);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">My Closet</h2>
          <p className="text-sm text-gray-500">
            {totalItems} items · {quotaRemaining} slots remaining
          </p>
        </div>
        <div className="flex gap-2">
          {showOutfitSuggestions && (
            <button
              onClick={handleSuggestOutfits}
              className="px-3 py-2 text-sm bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors flex items-center gap-1"
            >
              <Sparkles className="w-4 h-4" />
              Suggest Outfits
            </button>
          )}
          <button
            onClick={() => setShowUpload(true)}
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            Add Item
          </button>
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
            selectedCategory === null
              ? 'bg-gray-900 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap transition-colors ${
              selectedCategory === cat.id
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-600 rounded-lg">
          <AlertCircle className="w-4 h-4" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Items Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-12">
          <Shirt className="w-12 h-12 mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">
            {selectedCategory
              ? `No ${selectedCategory} in your closet yet`
              : 'Your closet is empty'}
          </p>
          <button
            onClick={() => setShowUpload(true)}
            className="mt-3 text-sm text-blue-600 hover:underline"
          >
            Add your first item
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {filteredItems.map(item => (
            <div
              key={item.id}
              className="group relative bg-gray-100 rounded-lg overflow-hidden aspect-square cursor-pointer"
              onClick={() => onSelectItem?.(item.id)}
            >
              {item.image_url ? (
                <img
                  src={item.image_url}
                  alt={item.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Shirt className="w-8 h-8 text-gray-400" />
                </div>
              )}
              
              {/* Overlay */}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors">
                <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                  <p className="text-white text-xs font-medium truncate">{item.name}</p>
                  <p className="text-white/70 text-xs">{item.category}</p>
                </div>
                
                {/* Actions */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      // Toggle favorite
                    }}
                    className="p-1.5 bg-white/90 rounded-full hover:bg-white transition-colors"
                    title="Favorite"
                    aria-label="Toggle favorite"
                  >
                    <Heart className={`w-3 h-3 ${item.is_favorite ? 'fill-red-500 text-red-500' : 'text-gray-600'}`} />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(item.id);
                    }}
                    disabled={deletingId === item.id}
                    className="p-1.5 bg-white/90 rounded-full hover:bg-red-50 transition-colors"
                    title="Delete"
                    aria-label="Delete item"
                  >
                    {deletingId === item.id ? (
                      <Loader2 className="w-3 h-3 animate-spin text-gray-600" />
                    ) : (
                      <Trash2 className="w-3 h-3 text-gray-600 hover:text-red-500" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Add to Closet</h3>
              <button
                onClick={() => {
                  setShowUpload(false);
                  setUploadFile(null);
                  setUploadPreview(null);
                }}
                className="p-1 hover:bg-gray-100 rounded-full"
                title="Close"
                aria-label="Close modal"
              >
                <span className="sr-only">Close</span>
                ×
              </button>
            </div>

            <div className="space-y-4">
              {/* Photo Upload */}
              <div
                onClick={() => document.getElementById('wardrobe-upload')?.click()}
                className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 transition-colors"
              >
                {uploadPreview ? (
                  <img
                    src={uploadPreview}
                    alt="Preview"
                    className="w-24 h-24 object-cover rounded-lg mx-auto"
                  />
                ) : (
                  <>
                    <Upload className="w-6 h-6 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600">Upload photo</p>
                  </>
                )}
              </div>
              <input
                id="wardrobe-upload"
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
                aria-label="Upload item photo"
              />

              {/* Name */}
              <input
                type="text"
                placeholder="Item name (optional)"
                value={newItemName}
                onChange={(e) => setNewItemName(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              {/* Category */}
              <select
                value={newItemCategory}
                onChange={(e) => setNewItemCategory(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Select category"
              >
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.label}</option>
                ))}
              </select>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowUpload(false);
                    setUploadFile(null);
                    setUploadPreview(null);
                  }}
                  className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!uploadFile || isUploading}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    'Add Item'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Outfit Suggestions Modal */}
      {showOutfits && outfitSuggestions.length > 0 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full max-h-[80vh] overflow-y-auto">
            <div className="sticky top-0 bg-white p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold">Outfit Suggestions</h3>
              <button
                onClick={() => setShowOutfits(false)}
                className="p-1 hover:bg-gray-100 rounded-full"
                title="Close"
                aria-label="Close modal"
              >
                <span className="sr-only">Close</span>
                ×
              </button>
            </div>
            <div className="p-4 space-y-4">
              {outfitSuggestions.map(outfit => (
                <div key={outfit.outfit_id} className="border rounded-lg p-3">
                  <p className="font-medium text-sm mb-2">{outfit.name}</p>
                  <div className="flex gap-2 mb-2">
                    {outfit.items.map(item => (
                      <div key={item.id} className="w-12 h-12 bg-gray-100 rounded flex items-center justify-center">
                        {item.image_url ? (
                          <img src={item.image_url} alt={item.name} className="w-full h-full object-cover rounded" />
                        ) : (
                          <Shirt className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                    ))}
                  </div>
                  {outfit.tips.length > 0 && (
                    <p className="text-xs text-gray-500">Tip: {outfit.tips[0]}</p>
                  )}
                  <div className="flex gap-2 mt-2 text-xs text-gray-500">
                    <span>Color: {Math.round(outfit.color_harmony_score * 100)}%</span>
                    <span>·</span>
                    <span>Style: {Math.round(outfit.style_match_score * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WardrobeGrid;
