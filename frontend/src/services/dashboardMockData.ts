/**
 * CONFIT — Dashboard Mock Data
 * =============================
 * 80+ realistic sales records for the Store Owner Dashboard.
 * Spans the last 90 days with varied categories, segments, margins, and statuses.
 */

import type { SaleRecord, SaleCategory, CustomerSegment, ReturnStatus } from '@/types/dashboard';

// ─── Helpers ────────────────────────────────────────────────────

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  d.setHours(Math.floor(Math.random() * 14) + 8, Math.floor(Math.random() * 60), 0, 0);
  return d.toISOString();
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ─── Data Pools ─────────────────────────────────────────────────

const CUSTOMER_NAMES = [
  'Nour Ahmed', 'Omar Khalil', 'Sara Mansour', 'Laila Farouk', 'Ahmed Rami',
  'Mohamed Ali', 'Yasmin Tarek', 'Karim Hassan', 'Dina Salah', 'Hana Mostafa',
  'Amr Youssef', 'Mona El-Sayed', 'Tarek Nabil', 'Fatma Ibrahim', 'Youssef Adel',
  'Rana Wael', 'Sherif Magdy', 'Nada Khaled', 'Mahmoud Fathy', 'Salma Gamal',
  'Ali Reda', 'Reem Ashraf', 'Hassan Emad', 'Mariam Samy', 'Khaled Tamer',
];

const SEGMENTS: CustomerSegment[] = ['New Customer', 'Returning', 'VIP', 'Wholesale'];
const STATUSES: ReturnStatus[] = ['Completed', 'Completed', 'Completed', 'Completed', 'Returned', 'Pending Return'];
const PAYMENT_METHODS = ['Credit Card', 'Cash on Delivery', 'BNPL', 'Digital Wallet', 'Bank Transfer'];
const BRANDS = ['Zahra', 'Tie House', 'Town Team', 'Tomato', 'La Reina', 'Cairo Couture', 'Nile & Co'];

interface ProductDef {
  name: string;
  category: SaleCategory;
  type: string;
  priceRange: [number, number];
  marginRange: [number, number];
  sku: string;
  thumbnail: string;
}

const PRODUCTS: ProductDef[] = [
  // Clothes
  { name: 'Silk Evening Gown', category: 'Clothes', type: 'Dresses', priceRange: [3800, 5200], marginRange: [32, 48], sku: 'CLT-001', thumbnail: 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=80&h=80&fit=crop' },
  { name: 'Linen Blazer', category: 'Clothes', type: 'Blazers', priceRange: [2800, 4200], marginRange: [28, 42], sku: 'CLT-002', thumbnail: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=80&h=80&fit=crop' },
  { name: 'Urban Cargo Pants', category: 'Clothes', type: 'Bottoms', priceRange: [900, 1500], marginRange: [35, 52], sku: 'CLT-003', thumbnail: 'https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=80&h=80&fit=crop' },
  { name: 'Graphic T-Shirt', category: 'Clothes', type: 'T-Shirts', priceRange: [350, 650], marginRange: [55, 72], sku: 'CLT-004', thumbnail: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=80&h=80&fit=crop' },
  { name: 'Cashmere Knit Sweater', category: 'Clothes', type: 'Tops', priceRange: [2200, 3400], marginRange: [25, 38], sku: 'CLT-005', thumbnail: 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=80&h=80&fit=crop' },
  { name: 'Tailored Wool Trousers', category: 'Clothes', type: 'Bottoms', priceRange: [1800, 2600], marginRange: [30, 44], sku: 'CLT-006', thumbnail: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=80&h=80&fit=crop' },
  { name: 'Cotton Polo Shirt', category: 'Clothes', type: 'Tops', priceRange: [450, 850], marginRange: [45, 65], sku: 'CLT-007', thumbnail: 'https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=80&h=80&fit=crop' },
  { name: 'Denim Jacket', category: 'Clothes', type: 'Jackets', priceRange: [1400, 2200], marginRange: [32, 48], sku: 'CLT-008', thumbnail: 'https://images.unsplash.com/photo-1551537482-f2075a1d41f2?w=80&h=80&fit=crop' },
  { name: 'Maxi Wrap Dress', category: 'Clothes', type: 'Dresses', priceRange: [2400, 3800], marginRange: [28, 42], sku: 'CLT-009', thumbnail: 'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=80&h=80&fit=crop' },
  { name: 'Slim Fit Chinos', category: 'Clothes', type: 'Bottoms', priceRange: [800, 1300], marginRange: [40, 58], sku: 'CLT-010', thumbnail: 'https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=80&h=80&fit=crop' },
  // Shoes
  { name: 'Classic Oxford Shoes', category: 'Shoes', type: 'Formal', priceRange: [2200, 3600], marginRange: [22, 38], sku: 'SH-001', thumbnail: 'https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=80&h=80&fit=crop' },
  { name: 'Casual Sneakers', category: 'Shoes', type: 'Sneakers', priceRange: [800, 1400], marginRange: [40, 58], sku: 'SH-002', thumbnail: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=80&h=80&fit=crop' },
  { name: 'Stiletto Heels', category: 'Shoes', type: 'Heels', priceRange: [1800, 3200], marginRange: [30, 45], sku: 'SH-003', thumbnail: 'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=80&h=80&fit=crop' },
  { name: 'Leather Ankle Boots', category: 'Shoes', type: 'Boots', priceRange: [2400, 3800], marginRange: [25, 40], sku: 'SH-004', thumbnail: 'https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=80&h=80&fit=crop' },
  { name: 'Canvas Slip-Ons', category: 'Shoes', type: 'Casual', priceRange: [500, 900], marginRange: [50, 68], sku: 'SH-005', thumbnail: 'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=80&h=80&fit=crop' },
  // Accessories
  { name: 'Gold Statement Necklace', category: 'Accessories', type: 'Jewelry', priceRange: [2800, 5500], marginRange: [45, 65], sku: 'AC-001', thumbnail: 'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=80&h=80&fit=crop' },
  { name: 'Leather Handbag', category: 'Accessories', type: 'Bags', priceRange: [3500, 6200], marginRange: [30, 48], sku: 'AC-002', thumbnail: 'https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=80&h=80&fit=crop' },
  { name: 'Luxury Watch', category: 'Accessories', type: 'Watches', priceRange: [4500, 12000], marginRange: [18, 35], sku: 'AC-003', thumbnail: 'https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=80&h=80&fit=crop' },
  { name: 'Italian Leather Belt', category: 'Accessories', type: 'Belts', priceRange: [600, 1200], marginRange: [50, 70], sku: 'AC-004', thumbnail: 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=80&h=80&fit=crop' },
  { name: 'Silk Scarf', category: 'Accessories', type: 'Scarves', priceRange: [800, 1800], marginRange: [45, 62], sku: 'AC-005', thumbnail: 'https://images.unsplash.com/photo-1601924921557-45e8e0e8eaf6?w=80&h=80&fit=crop' },
  // Full Outfit
  { name: 'Evening Gala Set', category: 'Full Outfit', type: 'Evening Set', priceRange: [8000, 15000], marginRange: [20, 35], sku: 'FO-001', thumbnail: 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=80&h=80&fit=crop' },
  { name: 'Business Formal Set', category: 'Full Outfit', type: 'Formal Set', priceRange: [5500, 9000], marginRange: [22, 38], sku: 'FO-002', thumbnail: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop' },
  { name: 'Weekend Casual Set', category: 'Full Outfit', type: 'Casual Set', priceRange: [2500, 4500], marginRange: [35, 50], sku: 'FO-003', thumbnail: 'https://images.unsplash.com/photo-1516257984-b1b4d707412e?w=80&h=80&fit=crop' },
  { name: 'Bridal Collection Set', category: 'Full Outfit', type: 'Bridal Set', priceRange: [12000, 25000], marginRange: [15, 28], sku: 'FO-004', thumbnail: 'https://images.unsplash.com/photo-1519741497674-611481863552?w=80&h=80&fit=crop' },
];

// ─── Generator ──────────────────────────────────────────────────

function randomInRange(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function generateRecords(count: number): SaleRecord[] {
  const records: SaleRecord[] = [];
  for (let i = 0; i < count; i++) {
    const product = PRODUCTS[i % PRODUCTS.length];
    const price = randomInRange(product.priceRange[0], product.priceRange[1]);
    const margin = randomInRange(product.marginRange[0], product.marginRange[1]);
    const customer = pick(CUSTOMER_NAMES);
    const segment = pick(SEGMENTS);
    const status = pick(STATUSES);
    const brand = pick(BRANDS);
    const dayOffset = randomInRange(0, 89);

    records.push({
      id: `sale-${String(i + 1).padStart(4, '0')}`,
      productName: product.name,
      thumbnail: product.thumbnail,
      category: product.category,
      productType: product.type,
      price,
      quantity: segment === 'Wholesale' ? randomInRange(5, 25) : randomInRange(1, 3),
      currency: 'EGP',
      customerName: customer,
      customerEmail: `${customer.toLowerCase().replace(/\s+/g, '.')}@email.com`,
      customerPhone: `+20 10${randomInRange(10000000, 99999999)}`,
      customerSegment: segment,
      saleDate: daysAgo(dayOffset),
      profitMargin: margin,
      returnStatus: status,
      sku: `${product.sku}-${String(randomInRange(100, 999))}`,
      brand,
      storeName: 'CONFIT Cairo Flagship',
      storeAddress: '15 El-Tahrir Square, Downtown Cairo',
      paymentMethod: pick(PAYMENT_METHODS),
      orderId: `ORD-${String(2000 + i).padStart(6, '0')}`,
    });
  }

  // Sort by sale date descending (most recent first)
  return records.sort((a, b) => new Date(b.saleDate).getTime() - new Date(a.saleDate).getTime());
}

export const MOCK_SALES: SaleRecord[] = generateRecords(85);
