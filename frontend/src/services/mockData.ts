import type { Product, Outfit, ProductCategory, OccasionType } from '@/types';

// Mock product images (placeholder URLs - will be replaced with generated images)
const productImages = {
  tops: [
    'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop',
  ],
  bottoms: [
    'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400&h=500&fit=crop',
  ],
  dresses: [
    'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400&h=500&fit=crop',
  ],
  outerwear: [
    'https://images.unsplash.com/photo-1544923246-77307dd628b8?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&h=500&fit=crop',
  ],
  shoes: [
    'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1560343090-f0409e92791a?w=400&h=500&fit=crop',
  ],
  accessories: [
    'https://images.unsplash.com/photo-1611923134239-b9be5816f80d?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1523779105320-d1cd346ff52b?w=400&h=500&fit=crop',
  ],
  bags: [
    'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=400&h=500&fit=crop',
    'https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&h=500&fit=crop',
  ],
};

export const brands = [
  'CONFIT Essentials',
  'Maison Élégance',
  'Urban Luxe',
  'Atelier Noir',
  'Vogue Milano',
  'Nordic Minimal',
  'Casa Bella',
  'The Heritage Co.',
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

function generateProducts(): Product[] {
  const products: Product[] = [];
  const categories: ProductCategory[] = ['tops', 'bottoms', 'dresses', 'outerwear', 'shoes', 'accessories', 'bags'];

  const productNames: Record<ProductCategory, string[]> = {
    tops: [
      'Silk Blouse', 'Cashmere Sweater', 'Linen Shirt', 'Knit Turtleneck', 'Cotton Tee', 'Blazer Top',
      'Oversized Hoodie', 'Graphic T-Shirt', 'Polo Shirt', 'Oxford Button-Down', 'Crop Top', 'Tank Top',
      'Cardigan', 'V-Neck Sweater', 'Crew Neck Sweatshirt', 'Long Sleeve Tee', 'Henley Shirt', 'Flannel Shirt',
      'Denim Shirt', 'Chambray Shirt', 'Bodysuit', 'Cami Top', 'Peplum Top', 'Wrap Top', 'Bandeau Top'
    ],
    bottoms: [
      'Tailored Trousers', 'Wide-Leg Pants', 'Pencil Skirt', 'Denim Jeans', 'Culottes', 'Pleated Skirt',
      'Cargo Pants', 'Chino Shorts', 'Joggers', 'Leggings', 'Midi Skirt', 'A-Line Skirt',
      'Bermuda Shorts', 'Track Pants', 'Corduroy Pants', 'Palazzo Pants', 'Cropped Pants', 'High-Waisted Jeans',
      'Skinny Jeans', 'Straight Leg Jeans', 'Bootcut Jeans', 'Flared Pants', 'Paperbag Waist Pants', 'Trouser Shorts'
    ],
    dresses: [
      'Midi Dress', 'Evening Gown', 'Wrap Dress', 'Shirt Dress', 'Cocktail Dress', 'Maxi Dress',
      'Mini Dress', 'Sundress', 'Bodycon Dress', 'Slip Dress', 'Kaftan', 'Tunic Dress',
      'A-Line Dress', 'Fit and Flare Dress', 'Shift Dress', 'Sheath Dress', 'Peplum Dress', 'Smock Dress',
      'Tiered Dress', 'Ruffled Dress', 'Floral Dress', 'Polka Dot Dress', 'Striped Dress', 'Plaid Dress'
    ],
    outerwear: [
      'Wool Coat', 'Trench Coat', 'Leather Jacket', 'Blazer', 'Puffer Jacket', 'Cardigan',
      'Denim Jacket', 'Bomber Jacket', 'Parka', 'Raincoat', 'Peacoat', 'Fleece Jacket', 'Windbreaker',
      'Quilted Jacket', 'Sherpa Jacket', 'Varsity Jacket', 'Motorcycle Jacket', 'Trucker Jacket', 'Field Jacket',
      'Duster Coat', 'Cape Coat', 'Poncho', 'Knit Cardigan', 'Hooded Jacket', 'Cropped Jacket'
    ],
    shoes: [
      'Leather Loafers', 'Ankle Boots', 'Stiletto Heels', 'Sneakers', 'Ballet Flats', 'Oxford Shoes',
      'Running Shoes', 'Sandals', 'Chelsea Boots', 'Espadrilles', 'Mules', 'Platform Boots',
      'High Heels', 'Wedges', 'Flats', 'Slip-Ons', 'Lace-Up Boots', 'Knee-High Boots',
      'Combat Boots', 'Hiking Boots', 'Dress Shoes', 'Casual Sneakers', 'Athletic Shoes', 'Formal Pumps'
    ],
    accessories: [
      'Silk Scarf', 'Leather Belt', 'Statement Earrings', 'Watch', 'Sunglasses', 'Hair Clip',
      'Fedora Hat', 'Beanie', 'Necklace', 'Bracelet', 'Tie', 'Cufflinks',
      'Baseball Cap', 'Bucket Hat', 'Beret', 'Headband', 'Hair Scrunchie', 'Barrette',
      'Choker', 'Pendant', 'Brooch', 'Pin', 'Ring', 'Anklet', 'Wallet', 'Keychain'
    ],
    bags: [
      'Tote Bag', 'Crossbody Bag', 'Clutch', 'Shoulder Bag', 'Backpack', 'Satchel',
      'Messenger Bag', 'Duffel Bag', 'Wristlet', 'Fanny Pack', 'Hobo Bag', 'Bucket Bag',
      'Structured Handbag', 'Quilted Bag', 'Chain Bag', 'Woven Bag', 'Leather Bag', 'Canvas Bag',
      'Evening Clutch', 'Mini Bag', 'Micro Bag', 'Oversized Tote', 'Laptop Bag', 'Gym Bag'
    ],
  };

  let id = 1;

  for (let loop = 0; loop < 3; loop++) {
    categories.forEach(category => {
      const names = productNames[category];
      const images = productImages[category];

      names.forEach((name, index) => {
        const brandName = brands[Math.floor(Math.random() * brands.length)];
        const brandId = `brand-${brandName.toLowerCase().replace(/\s/g, '-')}`;
        const basePrice = Math.floor(Math.random() * 300) + 50;
        const hasDiscount = Math.random() > 0.7;
        const productColors = colors.slice(0, Math.floor(Math.random() * 4) + 2).map(c => c.name);

        // Random gender assignment for broad testing
        const genderRoll = Math.random();
        const gender: 'men' | 'women' | 'unisex' = genderRoll > 0.6 ? 'women' : (genderRoll > 0.3 ? 'men' : 'unisex');

        products.push({
          id: `prod-${id++}`,
          name,
          brand: brandName,
          brandId,
          price: hasDiscount ? Math.floor(basePrice * 0.7) : basePrice,
          originalPrice: hasDiscount ? basePrice : undefined,
          currency: 'USD',
          category,
          subcategory: name.toLowerCase(),
          gender,
          images: [images[index % images.length]],
          colors: productColors,
          sizes: category === 'shoes'
            ? ['36', '37', '38', '39', '40', '41', '42']
            : ['XS', 'S', 'M', 'L', 'XL'],
          description: `Elevate your wardrobe with this exquisite ${name.toLowerCase()} from ${brandName}. Crafted with premium materials for lasting elegance.`,
          styleCompatibility: Math.floor(Math.random() * 30) + 70,
          inStock: Math.random() > 0.1,
          tags: [category, brandName.toLowerCase().replace(/\s/g, '-'), gender, ...productColors.map(c => c.toLowerCase())],
        });
      });
    });
  }

  return products;
}

let _mockProducts: Product[] | null = null;

export function getMockProducts(): Product[] {
  if (!_mockProducts) {
    _mockProducts = generateProducts();
  }
  return _mockProducts;
}

export const mockProducts: Product[] = new Proxy([] as Product[], {
  get(target, prop) {
    const products = getMockProducts();
    // Handle array methods and length correctly
    if (prop === 'length') return products.length;
    if (typeof prop === 'string' && !isNaN(Number(prop))) {
      return products[Number(prop)];
    }
    // Handle array methods like map, filter, etc.
    const value = Reflect.get(products, prop);
    if (typeof value === 'function') {
      return value.bind(products);
    }
    return value;
  },
}) as Product[];

// Featured outfits for the homepage
export const featuredOutfits: Partial<Outfit>[] = [
  {
    id: 'outfit-1',
    name: 'Executive Elegance',
    occasion: 'work',
    totalPrice: 485,
    styleScore: 92,
  },
  {
    id: 'outfit-2',
    name: 'Weekend Sophisticate',
    occasion: 'casual',
    totalPrice: 320,
    styleScore: 88,
  },
  {
    id: 'outfit-3',
    name: 'Evening Glamour',
    occasion: 'party',
    totalPrice: 650,
    styleScore: 95,
  },
  {
    id: 'outfit-4',
    name: 'Date Night Chic',
    occasion: 'date',
    totalPrice: 420,
    styleScore: 90,
  },
];

// Occasion data for quick access
export const occasions: { id: OccasionType; label: string; icon: string }[] = [
  { id: 'work', label: 'Work', icon: '💼' },
  { id: 'wedding', label: 'Wedding', icon: '💒' },
  { id: 'party', label: 'Party', icon: '🎉' },
  { id: 'casual', label: 'Casual', icon: '☕' },
  { id: 'date', label: 'Date Night', icon: '💝' },
  { id: 'vacation', label: 'Vacation', icon: '✈️' },
  { id: 'formal-event', label: 'Formal Event', icon: '🎭' },
  { id: 'formal', label: 'Formal', icon: '👔' },
  { id: 'active', label: 'Active', icon: '🏃' },
  { id: 'everyday', label: 'Everyday', icon: '🌟' },
];

// Style types for preferences
export const styleTypes = [
  { id: 'casual', label: 'Casual', description: 'Relaxed and comfortable everyday wear' },
  { id: 'formal', label: 'Formal', description: 'Professional and polished looks' },
  { id: 'streetwear', label: 'Streetwear', description: 'Urban and trend-forward styles' },
  { id: 'minimalist', label: 'Minimalist', description: 'Clean lines and simple elegance' },
  { id: 'bohemian', label: 'Bohemian', description: 'Free-spirited and artistic' },
  { id: 'classic', label: 'Classic', description: 'Timeless and sophisticated' },
  { id: 'sporty', label: 'Sporty', description: 'Athletic and active lifestyle' },
  { id: 'elegant', label: 'Elegant', description: 'Refined and luxurious' },
];

// Search/filter products
export function searchProducts(
  query: string,
  filters?: {
    categories?: ProductCategory[];
    priceMin?: number;
    priceMax?: number;
    brands?: string[];
    colors?: string[];
    inStockOnly?: boolean;
  }
): Product[] {
  let results = [...mockProducts];

  // Text search
  if (query.trim()) {
    const searchTerms = query.toLowerCase().split(' ');
    results = results.filter(product => {
      const searchableText = `${product.name} ${product.brand} ${product.description} ${product.tags.join(' ')}`.toLowerCase();
      return searchTerms.every(term => searchableText.includes(term));
    });
  }

  // Apply filters
  if (filters) {
    if (filters.categories?.length) {
      results = results.filter(p => filters.categories!.includes(p.category));
    }
    if (filters.priceMin !== undefined) {
      results = results.filter(p => p.price >= filters.priceMin!);
    }
    if (filters.priceMax !== undefined) {
      results = results.filter(p => p.price <= filters.priceMax!);
    }
    if (filters.brands?.length) {
      results = results.filter(p => filters.brands!.includes(p.brand));
    }
    if (filters.colors?.length) {
      results = results.filter(p =>
        p.colors.some(c => filters.colors!.includes(c))
      );
    }
    if (filters.inStockOnly) {
      results = results.filter(p => p.inStock);
    }
  }

  return results;
}

export function getProductById(id: string): Product | undefined {
  // Direct match
  const directMatch = mockProducts.find(p => p.id === id);
  if (directMatch) return directMatch;

  // Handle number-only IDs (e.g. "1" -> "prod-1")
  if (!isNaN(Number(id))) {
    return mockProducts.find(p => p.id === `prod-${id}`);
  }

  // Handle "prod-" prefix if missing or malformed (fuzzy)
  return mockProducts.find(p => p.id.endsWith(`-${id}`));
}

export function getProductsByCategory(category: ProductCategory): Product[] {
  return mockProducts.filter(p => p.category === category);
}

export function getFeaturedProducts(limit: number = 8): Product[] {
  return mockProducts
    .sort((a, b) => b.styleCompatibility - a.styleCompatibility)
    .slice(0, limit);
}

export function getTrendingProducts(limit: number = 6): Product[] {
  return mockProducts
    .filter(p => p.originalPrice !== undefined) // Products on sale are "trending"
    .slice(0, limit);
}

// --- Wardrobe Specific Mocks ---

export const sampleWardrobeItems = [
  { id: '1', name: 'Navy Blazer', category: 'outerwear', color: 'Navy', image: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop', brand: 'Hugo Boss', tags: ['formal', 'work', 'outerwear'] },
  { id: '2', name: 'White Silk Blouse', category: 'tops', color: 'White', image: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=300&h=400&fit=crop', brand: 'Theory', tags: ['work', 'elegant', 'tops'] },
  { id: '3', name: 'Black Trousers', category: 'bottoms', color: 'Black', image: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=300&h=400&fit=crop', brand: 'Zara', tags: ['work', 'casual', 'bottoms'] },
  { id: '4', name: 'Leather Loafers', category: 'shoes', color: 'Brown', image: 'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=300&h=400&fit=crop', brand: 'Cole Haan', tags: ['work', 'shoes'] },
  { id: '5', name: 'Cashmere Sweater', category: 'tops', color: 'Beige', image: 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=300&h=400&fit=crop', brand: 'Everlane', tags: ['casual', 'comfort', 'tops'] },
  { id: '6', name: 'Statement Earrings', category: 'accessories', color: 'Gold', image: 'https://images.unsplash.com/photo-1611923134239-b9be5816f80d?w=300&h=400&fit=crop', brand: 'Kate Spade', tags: ['party', 'accessories'] },
];

export async function mockAutoTagging(file: File): Promise<{
  category: ProductCategory;
  color: string;
  tags: string[];
}> {
  // Simulate AI delay
  await new Promise(resolve => setTimeout(resolve, 1500));

  // Randomly assign tags for demo
  const categories: ProductCategory[] = ['tops', 'bottoms', 'dresses', 'shoes', 'accessories'];
  const colorsList = ['Black', 'White', 'Blue', 'Red', 'Beige'];

  return {
    category: categories[Math.floor(Math.random() * categories.length)],
    color: colorsList[Math.floor(Math.random() * colorsList.length)],
    tags: ['auto-tagged', 'smart-wardrobe', 'new-arrival']
  };
}
