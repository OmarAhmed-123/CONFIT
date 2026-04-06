import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import type { ProductCategory } from '@/types';

interface FilterPanelProps {
  selectedCategories: ProductCategory[];
  setSelectedCategories: (categories: ProductCategory[]) => void;
  priceRange: { min: number; max: number };
  setPriceRange: (range: { min: number; max: number }) => void;
  selectedBrands: string[];
  setSelectedBrands: (brands: string[]) => void;
  selectedColors: string[];
  setSelectedColors: (colors: string[]) => void;
  inStockOnly: boolean;
  setInStockOnly: (value: boolean) => void;
}

const categories: { id: ProductCategory; label: string }[] = [
  { id: 'tops', label: 'Tops' },
  { id: 'bottoms', label: 'Bottoms' },
  { id: 'dresses', label: 'Dresses' },
  { id: 'outerwear', label: 'Outerwear' },
  { id: 'shoes', label: 'Shoes' },
  { id: 'accessories', label: 'Accessories' },
  { id: 'bags', label: 'Bags' },
];

const brands = [
  'CONFIT Essentials',
  'Maison Élégance',
  'Urban Luxe',
  'Atelier Noir',
  'Vogue Milano',
  'Nordic Minimal',
];

const colors = [
  { name: 'Black', hex: '#0D0D0D' },
  { name: 'White', hex: '#FAFAFA' },
  { name: 'Navy', hex: '#1E3A5F' },
  { name: 'Champagne', hex: '#C9A962' },
  { name: 'Burgundy', hex: '#722F37' },
  { name: 'Olive', hex: '#556B2F' },
  { name: 'Camel', hex: '#C19A6B' },
  { name: 'Slate', hex: '#708090' },
];

export function FilterPanel({
  selectedCategories,
  setSelectedCategories,
  priceRange,
  setPriceRange,
  selectedBrands,
  setSelectedBrands,
  selectedColors,
  setSelectedColors,
  inStockOnly,
  setInStockOnly,
}: FilterPanelProps) {
  const toggleCategory = (category: ProductCategory) => {
    if (selectedCategories.includes(category)) {
      setSelectedCategories(selectedCategories.filter(c => c !== category));
    } else {
      setSelectedCategories([...selectedCategories, category]);
    }
  };

  const toggleBrand = (brand: string) => {
    if (selectedBrands.includes(brand)) {
      setSelectedBrands(selectedBrands.filter(b => b !== brand));
    } else {
      setSelectedBrands([...selectedBrands, brand]);
    }
  };

  const toggleColor = (color: string) => {
    if (selectedColors.includes(color)) {
      setSelectedColors(selectedColors.filter(c => c !== color));
    } else {
      setSelectedColors([...selectedColors, color]);
    }
  };

  return (
    <div className="space-y-8">
      {/* Categories */}
      <div>
        <h3 className="font-semibold mb-4">Category</h3>
        <div className="space-y-3">
          {categories.map((category) => (
            <label
              key={category.id}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <Checkbox
                checked={selectedCategories.includes(category.id)}
                onCheckedChange={() => toggleCategory(category.id)}
              />
              <span className="text-sm group-hover:text-accent transition-colors">
                {category.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Price Range */}
      <div>
        <h3 className="font-semibold mb-4">Price Range</h3>
        <div className="px-1">
          <Slider
            defaultValue={[priceRange.min, priceRange.max]}
            min={0}
            max={1000}
            step={10}
            onValueChange={([min, max]) => setPriceRange({ min, max })}
            className="mb-4"
          />
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>${priceRange.min}</span>
            <span>${priceRange.max}</span>
          </div>
        </div>
      </div>

      {/* Brands */}
      <div>
        <h3 className="font-semibold mb-4">Brand</h3>
        <div className="space-y-3">
          {brands.map((brand) => (
            <label
              key={brand}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <Checkbox
                checked={selectedBrands.includes(brand)}
                onCheckedChange={() => toggleBrand(brand)}
              />
              <span className="text-sm group-hover:text-accent transition-colors">
                {brand}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Colors */}
      <div>
        <h3 className="font-semibold mb-4">Color</h3>
        <div className="flex flex-wrap gap-2">
          {colors.map((color) => (
            <button
              key={color.name}
              onClick={() => toggleColor(color.name)}
              className={`w-8 h-8 rounded-full border-2 transition-all ${
                selectedColors.includes(color.name)
                  ? 'border-accent scale-110'
                  : 'border-transparent hover:scale-105'
              }`}
              style={{ backgroundColor: color.hex }}
              title={color.name}
            />
          ))}
        </div>
      </div>

      {/* In Stock */}
      <div>
        <label className="flex items-center gap-3 cursor-pointer">
          <Checkbox
            checked={inStockOnly}
            onCheckedChange={(checked) => setInStockOnly(checked === true)}
          />
          <span className="text-sm">In Stock Only</span>
        </label>
      </div>
    </div>
  );
}
