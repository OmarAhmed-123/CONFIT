/**
 * CONFIT — Primary Navigation
 * ============================
 * 6-icon navigation with contextual mega menus (desktop) and bottom sheets (mobile)
 * Icons: Fashion, Category, Brands, Occasion, Style Me, My Space
 *
 * Features:
 * - Background dim overlay when mega menu is open
 * - Premium glow on Style Me icon (brand identity)
 * - Smart Mode: prompts "Would you like CONFIT to style this for you?"
 * - Mobile: scrollable horizontal icon row + full-screen bottom overlay
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3,
  User as UserIcon,
  ShoppingBag,
  Tag,
  Target,
  Sparkles,
  Heart,
  ChevronRight,
  X,
  Search,
  Bell,
  Menu,
  Shirt,
  Gem,
  Wand2,
  Camera,
  Crown,
  Clock,
  Package,
  Shield,
  Store,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { useCart } from '@/context/CartContext';
import { useWishlist } from '@/context/WishlistContext';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { createTransition } from '@/motion';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import type { UserProfile } from '@/types';
import { hasRole } from '@/lib/auth/roles';

// ─── Types ───
interface NavSubItem {
  label: string;
  href: string;
  description?: string;
  icon?: React.ReactNode;
  emoji?: string;
  secondaryItems?: NavSubItem[];
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  emoji?: string;
  href?: string;
  subItems?: NavSubItem[];
  isPremium?: boolean;
}

// Shoe icon (lucide-react doesn't export Shoe in all versions)
function ShoeIcon({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M3 17h18v-2a4 4 0 0 0-4-4h-1l-2-4H8l-1 2c-2 0-4 2-4 4v4z"/>
      <path d="M6 17v2"/>
      <path d="M18 17v2"/>
    </svg>
  );
}

// ─── Nav Data ───
const FASHION_CATEGORIES: NavSubItem[] = [
  { label: 'Clothes', href: '#clothes', description: 'Tops, bottoms, dresses', icon: <Shirt className="h-4 w-4" /> },
  { label: 'Shoes', href: '#shoes', description: 'Sneakers, heels, boots', icon: <ShoeIcon className="h-4 w-4" /> },
  { label: 'Accessories', href: '#accessories', description: 'Bags, jewelry, more', icon: <Gem className="h-4 w-4" /> },
];

const BASE_NAV_ITEMS: NavItem[] = [
  {
    id: 'fashion',
    label: 'Fashion',
    icon: <UserIcon className="h-5 w-5" />,
    emoji: '👤',
    subItems: [
      {
        label: 'Women',
        href: '/products?gender=women',
        description: "Women's fashion",
        secondaryItems: FASHION_CATEGORIES.map(c => ({
          ...c,
          href: `/products?gender=women&category=${c.label.toLowerCase()}`
        }))
      },
      {
        label: 'Men',
        href: '/products?gender=men',
        description: "Men's fashion",
        secondaryItems: FASHION_CATEGORIES.map(c => ({
          ...c,
          href: `/products?gender=men&category=${c.label.toLowerCase()}`
        }))
      },
      {
        label: 'Kids',
        href: '/products?gender=kids',
        description: "Kids' fashion",
        secondaryItems: FASHION_CATEGORIES.map(c => ({
          ...c,
          href: `/products?gender=kids&category=${c.label.toLowerCase()}`
        }))
      },
    ],
  },
  {
    id: 'category',
    label: 'Category',
    icon: <ShoppingBag className="h-5 w-5" />,
    emoji: '🛍',
    subItems: [
      { label: 'Clothes', href: '/products?category=clothes', description: 'All apparel', icon: <Shirt className="h-4 w-4" /> },
      { label: 'Shoes', href: '/products?category=shoes', description: 'Footwear for all', icon: <ShoeIcon className="h-4 w-4" /> },
      { label: 'Accessories', href: '/products?category=accessories', description: 'Complete your look', icon: <Gem className="h-4 w-4" /> },
      { label: '✨ Full Outfit', href: '/outfits', description: 'Curated complete looks', icon: <Sparkles className="h-4 w-4" /> },
    ],
  },
  {
    id: 'brands',
    label: 'Brands',
    icon: <Tag className="h-5 w-5" />,
    emoji: '🏷',
    subItems: [
      { label: 'Zahra', href: '/brands/zahra', description: 'Elegant modest fashion' },
      { label: 'Town Team', href: '/brands/town-team', description: 'Urban casual style' },
      { label: 'Tie House', href: '/brands/tie-house', description: 'Premium formal wear' },
      { label: 'Tomato', href: '/brands/tomato', description: 'Trendy youth fashion' },
      { label: 'View All Brands', href: '/brands', description: 'Browse all partners' },
    ],
  },
  {
    id: 'occasion',
    label: 'Occasion',
    icon: <Target className="h-5 w-5" />,
    emoji: '🎯',
    subItems: [
      { label: 'Party', href: '/occasions/party', description: 'Stand out in style' },
      { label: 'Work', href: '/occasions/work', description: 'Professional looks' },
      { label: 'Wedding', href: '/occasions/wedding', description: 'Guest & party attire' },
      { label: 'Casual', href: '/occasions/casual', description: 'Everyday comfort' },
      { label: 'Smart Casual', href: '/occasions/smart-casual', description: 'Polished yet relaxed' },
      { label: 'Classic', href: '/occasions/classic', description: 'Timeless elegance' },
      { label: 'Sport', href: '/occasions/sport', description: 'Active & athletic' },
    ],
  },
  {
    id: 'style-me',
    label: 'Style Me',
    icon: <Sparkles className="h-5 w-5" />,
    emoji: '✨',
    href: '/ai-stylist',
    isPremium: true,
    subItems: [
      { label: '🤖 AI Style', href: '/ai-stylist', description: '"Styled For You"', icon: <Wand2 className="h-4 w-4" /> },
      { label: '👤 Virtual Try-On', href: '/try-on', description: '"See It On You"', icon: <Camera className="h-4 w-4" /> },
      { label: '👑 CONFIT Studio', href: '/outfits', description: '"Create Your CONFIT Look"', icon: <Crown className="h-4 w-4" /> },
    ],
  },
  {
    id: 'my-space',
    label: 'My Space',
    icon: <Heart className="h-5 w-5" />,
    emoji: '❤️',
    subItems: [
      { label: 'Wishlist', href: '/wishlist', description: 'Items you love', icon: <Heart className="h-4 w-4" /> },
      { label: 'Saved Outfits', href: '/wardrobe?tab=outfits', description: 'Your curated looks', icon: <Sparkles className="h-4 w-4" /> },
      { label: 'Recently Viewed', href: '/profile?tab=history', description: 'Your browsing history', icon: <Clock className="h-4 w-4" /> },
      { label: 'My Orders', href: '/orders', description: 'Track purchases', icon: <Package className="h-4 w-4" /> },
    ],
  },
];

function buildMySpaceItems(user: UserProfile | null | undefined): NavSubItem[] {
  const items: NavSubItem[] = [
    { label: 'Wishlist', href: '/wishlist', description: 'Items you love', icon: <Heart className="h-4 w-4" /> },
    { label: 'Saved Outfits', href: '/wardrobe?tab=outfits', description: 'Your curated looks', icon: <Sparkles className="h-4 w-4" /> },
    { label: 'Recently Viewed', href: '/profile?tab=history', description: 'Your browsing history', icon: <Clock className="h-4 w-4" /> },
    { label: 'My Orders', href: '/orders', description: 'Track purchases', icon: <Package className="h-4 w-4" /> },
    { label: 'Notifications', href: '/notifications', description: 'Order and account updates', icon: <Bell className="h-4 w-4" /> },
    { label: 'My Analytics', href: '/analytics/me', description: 'Your shopping insights', icon: <BarChart3 className="h-4 w-4" /> },
  ];

  if (hasRole(user?.roles, 'brand_manager')) {
    items.unshift(
      { label: 'Brand Dashboard', href: '/brand-dashboard', description: 'Products, orders, and operations', icon: <Store className="h-4 w-4" /> },
      { label: 'Analytics Hub', href: '/analytics', description: 'Store, brand, and performance insights', icon: <BarChart3 className="h-4 w-4" /> },
      { label: 'Store Operations', href: '/store-dashboard', description: 'Alerts, sold products, and store KPIs', icon: <Store className="h-4 w-4" /> },
    );
  }

  if (hasRole(user?.roles, 'stylist')) {
    items.unshift(
      { label: 'Stylist Dashboard', href: '/stylist-dashboard', description: 'Clients, looks, and schedule', icon: <Sparkles className="h-4 w-4" /> },
      { label: 'Client Workspace', href: '/stylist-dashboard?tab=clients', description: 'Manage styling clients', icon: <Users className="h-4 w-4" /> },
    );
  }

  if (hasRole(user?.roles, 'admin')) {
    items.unshift(
      { label: 'Admin Dashboard', href: '/admin', description: 'Users, brands, and operations', icon: <Shield className="h-4 w-4" /> },
      { label: 'Analytics Hub', href: '/analytics', description: 'Platform-wide metrics and insights', icon: <BarChart3 className="h-4 w-4" /> },
      { label: 'Notification Analytics', href: '/notification-analytics', description: 'Delivery and engagement monitoring', icon: <Bell className="h-4 w-4" /> },
    );
  }

  return items;
}

function buildNavItems(user: UserProfile | null | undefined): NavItem[] {
  return BASE_NAV_ITEMS.map((item) => (
    item.id === 'my-space'
      ? { ...item, subItems: buildMySpaceItems(user) }
      : item
  ));
}

// ─── Desktop Mega Menu ───
function MegaMenu({
  item,
  isOpen,
  onClose,
}: {
  item: NavItem;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [expandedSecondary, setExpandedSecondary] = useState<string | null>(null);

  if (!item.subItems?.length) return null;

  const hasSecondary = item.subItems.some(s => s.secondaryItems?.length);
  const gridCols = hasSecondary ? 'grid-cols-1 lg:grid-cols-3' : 'grid-cols-2 lg:grid-cols-3';

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8 }}
          transition={createTransition({ duration: 0.2 })}
          className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-[90vw] max-w-5xl bg-card border border-border rounded-2xl shadow-2xl overflow-hidden z-50"
          onMouseLeave={onClose}
        >
          <div className={cn('grid gap-6 p-6', gridCols)}>
            <div className={cn('grid gap-3', hasSecondary ? 'grid-cols-1' : 'grid-cols-2 lg:grid-cols-3')}>
              {item.subItems.map((subItem) => (
                <div key={subItem.href} className="relative">
                  <Link
                    href={subItem.href}
                    onClick={onClose}
                    className="group flex items-start gap-3 p-3 rounded-xl hover:bg-muted/50 transition-colors"
                    onMouseEnter={() => subItem.secondaryItems && setExpandedSecondary(subItem.label)}
                    onMouseLeave={() => setExpandedSecondary(null)}
                  >
                    {subItem.icon && (
                      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                        {subItem.icon}
                      </div>
                    )}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm group-hover:text-accent transition-colors">
                          {subItem.label}
                        </span>
                        {subItem.secondaryItems && (
                          <ChevronRight className="h-3 w-3 text-muted-foreground" />
                        )}
                      </div>
                      {subItem.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">{subItem.description}</p>
                      )}
                    </div>
                  </Link>

                  {/* Secondary flyout */}
                  <AnimatePresence>
                    {subItem.secondaryItems && expandedSecondary === subItem.label && (
                      <motion.div
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        className="absolute left-full top-0 ml-2 bg-card border border-border rounded-xl shadow-lg p-3 min-w-[180px] z-10"
                      >
                        {subItem.secondaryItems.map((secondary) => (
                          <Link
                            key={secondary.href}
                            href={secondary.href}
                            onClick={onClose}
                            className="flex items-center gap-2 p-2 rounded-lg hover:bg-muted/50 transition-colors"
                          >
                            {secondary.icon}
                            <div>
                              <p className="text-sm font-medium">{secondary.label}</p>
                              {secondary.description && (
                                <p className="text-xs text-muted-foreground">{secondary.description}</p>
                              )}
                            </div>
                          </Link>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>

            {/* Style Me premium CTA */}
            {item.isPremium && (
              <div className="lg:col-span-1 p-4 bg-gradient-to-br from-violet-500/10 to-purple-500/10 rounded-xl border border-violet-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="h-5 w-5 text-violet-500" />
                  <span className="font-semibold text-sm">Smart Mode</span>
                </div>
                <p className="text-xs text-muted-foreground mb-3">
                  Select your preferences and let CONFIT create the perfect look for you.
                </p>
                <Link href="/ai-stylist" onClick={onClose}>
                  <Button size="sm" className="w-full bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600">
                    Start Styling
                  </Button>
                </Link>
              </div>
            )}
          </div>

          {/* Smart Mode CTA for Occasion */}
          {item.id === 'occasion' && (
            <div className="px-6 pb-4">
              <div className="smart-mode-prompt flex items-center gap-3">
                <Sparkles className="h-5 w-5 text-violet-400 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Would you like CONFIT to style this for you?</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Select an occasion and let AI find your perfect look</p>
                </div>
                <Link href="/ai-stylist" onClick={onClose}>
                  <Button size="sm" variant="outline" className="border-violet-500/30 text-violet-400 hover:bg-violet-500/10">
                    Style Me
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ─── Mobile Full-Screen Nav Sheet ───
function MobileNavSheet({ trigger }: { trigger: React.ReactNode }) {
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const router = useRouter();
  const { user, signOut } = useAuth();
  const { items: cartItems } = useCart();
  const { items: wishlistItems } = useWishlist();
  const navItems = useMemo(() => buildNavItems(user), [user]);

  const handleNavClick = useCallback((item: NavItem) => {
    if (item.href) {
      router.push(item.href);
      setActiveSection(null);
    } else if (item.subItems?.length) {
      setActiveSection(activeSection === item.id ? null : item.id);
    }
  }, [activeSection, router]);

  const handleSubItemClick = useCallback((href: string) => {
    router.push(href);
    setActiveSection(null);
  }, [router]);

  return (
    <Sheet>
      <SheetTrigger asChild>{trigger}</SheetTrigger>
      <SheetContent side="bottom" className="h-[85vh] rounded-t-3xl p-0">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
                <span className="text-white font-bold text-lg">C</span>
              </div>
              <div>
                {user ? (
                  <>
                    <p className="font-semibold text-sm">{user.name}</p>
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  </>
                ) : (
                  <p className="font-semibold text-sm">Welcome to CONFIT</p>
                )}
              </div>
            </div>
            <NotificationCenter />
          </div>

          {/* Scrollable icons row at top for quick access */}
          <div className="flex items-center gap-2 p-3 overflow-x-auto no-scrollbar border-b border-border/50">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => handleNavClick(item)}
                className={cn(
                  'flex flex-col items-center gap-1 px-3 py-2 rounded-xl min-w-[64px] transition-all',
                  activeSection === item.id
                    ? 'bg-accent/10 text-accent'
                    : 'hover:bg-muted/50',
                  item.isPremium && 'style-me-glow rounded-xl'
                )}
              >
                {item.icon}
                <span className="text-[10px] font-medium whitespace-nowrap">{item.label}</span>
              </button>
            ))}
          </div>

          {/* Navigation Items */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {navItems.map((item) => (
              <div key={item.id}>
                <button
                  onClick={() => handleNavClick(item)}
                  className={cn(
                    'w-full flex items-center justify-between p-4 rounded-xl transition-colors',
                    activeSection === item.id ? 'bg-accent/10 text-accent' : 'hover:bg-muted/50'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'h-10 w-10 rounded-xl bg-muted flex items-center justify-center',
                      item.isPremium && 'style-me-glow'
                    )}>
                      {item.icon}
                    </div>
                    <span className="font-medium">{item.label}</span>
                  </div>
                  {item.subItems && (
                    <motion.div
                      animate={{ rotate: activeSection === item.id ? 90 : 0 }}
                      transition={createTransition({ duration: 0.2 })}
                    >
                      <ChevronRight className="h-5 w-5 text-muted-foreground" />
                    </motion.div>
                  )}
                </button>

                <AnimatePresence>
                  {activeSection === item.id && item.subItems && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={createTransition({ duration: 0.2 })}
                      className="overflow-hidden"
                    >
                      <div className="pl-6 pr-4 py-2 space-y-1">
                        {item.subItems.map((subItem) => (
                          <button
                            key={subItem.href}
                            onClick={() => handleSubItemClick(subItem.href)}
                            className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-muted/30 transition-colors text-left"
                          >
                            <div className="flex items-center gap-3">
                              {subItem.icon && (
                                <div className="h-8 w-8 rounded-lg bg-muted/50 flex items-center justify-center flex-shrink-0">
                                  {subItem.icon}
                                </div>
                              )}
                              <div>
                                <p className="text-sm font-medium">{subItem.label}</p>
                                {subItem.description && (
                                  <p className="text-xs text-muted-foreground">{subItem.description}</p>
                                )}
                              </div>
                            </div>
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          </button>
                        ))}
                      </div>

                      {/* Smart Mode prompt in occasion section (mobile) */}
                      {item.id === 'occasion' && (
                        <div className="px-6 pb-3">
                          <div className="smart-mode-prompt flex items-center gap-3">
                            <Sparkles className="h-4 w-4 text-violet-400 flex-shrink-0" />
                            <p className="text-xs flex-1">Would you like CONFIT to style this for you?</p>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs h-7 border-violet-500/30 text-violet-400"
                              onClick={() => handleSubItemClick('/ai-stylist')}
                            >
                              Style Me
                            </Button>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-border space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Link href="/cart" className="relative">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <ShoppingBag className="h-4 w-4" />
                  Cart
                  {cartItems.length > 0 && (
                    <Badge className="ml-auto h-5 w-5 p-0 flex items-center justify-center">
                      {cartItems.length}
                    </Badge>
                  )}
                </Button>
              </Link>
              <Link href="/wishlist" className="relative">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Heart className="h-4 w-4" />
                  Wishlist
                  {wishlistItems.length > 0 && (
                    <Badge className="ml-auto h-5 w-5 p-0 flex items-center justify-center">
                      {wishlistItems.length}
                    </Badge>
                  )}
                </Button>
              </Link>
            </div>
            {user ? (
              <Button
                variant="ghost"
                className="w-full justify-center text-muted-foreground"
                onClick={signOut}
              >
                Sign Out
              </Button>
            ) : (
              <Link href="/login" className="block">
                <Button className="w-full">Sign In</Button>
              </Link>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ─── Main Primary Navigation ───
export function PrimaryNav() {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { user } = useAuth();
  const { items: cartItems } = useCart();
  const { items: wishlistItems } = useWishlist();
  const navItems = useMemo(() => buildNavItems(user), [user]);

  const handleMenuEnter = useCallback((id: string) => {
    setActiveMenu(id);
  }, []);

  const handleMenuLeave = useCallback(() => {
    setActiveMenu(null);
  }, []);

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/products?search=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
      setIsSearchOpen(false);
    }
  }, [searchQuery, router]);

  useEffect(() => {
    if (isSearchOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isSearchOpen]);

  return (
    <>
      {/* Background dim overlay when mega menu is open */}
      <AnimatePresence>
        {activeMenu && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="mega-menu-backdrop"
            onClick={handleMenuLeave}
          />
        )}
      </AnimatePresence>

      <header className="sticky top-0 z-50 w-full bg-background/80 backdrop-blur-lg border-b border-border/50">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
                <span className="text-white font-bold text-lg">C</span>
              </div>
              <span className="font-display font-bold text-xl tracking-tight hidden sm:block">
                CONFIT
              </span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-1">
              {navItems.map((item) => (
                <div
                  key={item.id}
                  className="relative"
                  onMouseEnter={() => item.subItems && handleMenuEnter(item.id)}
                  onMouseLeave={handleMenuLeave}
                >
                  {item.href ? (
                    <Link
                      href={item.href}
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all',
                        activeMenu === item.id
                          ? 'bg-accent/10 text-accent'
                          : 'hover:bg-muted/50',
                        item.isPremium && 'style-me-glow rounded-full'
                      )}
                    >
                      {item.icon}
                      <span>{item.label}</span>
                    </Link>
                  ) : (
                    <button
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all',
                        activeMenu === item.id
                          ? 'bg-accent/10 text-accent'
                          : 'hover:bg-muted/50',
                        item.isPremium && 'style-me-glow rounded-full'
                      )}
                    >
                      {item.icon}
                      <span>{item.label}</span>
                    </button>
                  )}
                  {item.subItems && (
                    <MegaMenu
                      item={item}
                      isOpen={activeMenu === item.id}
                      onClose={handleMenuLeave}
                    />
                  )}
                </div>
              ))}
            </nav>

            {/* Right Actions */}
            <div className="flex items-center gap-2">
              {/* Search Toggle */}
              <AnimatePresence mode="wait">
                {isSearchOpen ? (
                  <motion.form
                    key="search-input"
                    initial={{ width: 40, opacity: 0 }}
                    animate={{ width: 200, opacity: 1 }}
                    exit={{ width: 40, opacity: 0 }}
                    transition={createTransition({ duration: 0.2 })}
                    onSubmit={handleSearch}
                    className="relative"
                  >
                    <input
                      ref={searchInputRef}
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search..."
                      className="w-full h-9 pl-9 pr-3 rounded-full bg-muted border border-border text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                    />
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <button
                      type="button"
                      onClick={() => setIsSearchOpen(false)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-muted"
                      title="Close search"
                      aria-label="Close search"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </motion.form>
                ) : (
                  <motion.button
                    key="search-button"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setIsSearchOpen(true)}
                    className="p-2 rounded-full hover:bg-muted transition-colors"
                    title="Search"
                    aria-label="Search"
                  >
                    <Search className="h-5 w-5" />
                  </motion.button>
                )}
              </AnimatePresence>

              {/* Desktop Actions */}
              <div className="hidden md:flex items-center gap-1">
                <NotificationCenter />
                <Link href="/wishlist" className="relative p-2 rounded-full hover:bg-muted transition-colors">
                  <Heart className="h-5 w-5" />
                  {wishlistItems.length > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-accent text-accent-foreground text-[10px] font-bold flex items-center justify-center">
                      {wishlistItems.length > 9 ? '9+' : wishlistItems.length}
                    </span>
                  )}
                </Link>
                <Link href="/cart" className="relative p-2 rounded-full hover:bg-muted transition-colors">
                  <ShoppingBag className="h-5 w-5" />
                  {cartItems.length > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-accent text-accent-foreground text-[10px] font-bold flex items-center justify-center">
                      {cartItems.length > 9 ? '9+' : cartItems.length}
                    </span>
                  )}
                </Link>
                {user ? (
                  <Link href="/profile" className="p-2 rounded-full hover:bg-muted transition-colors">
                    {user.avatar ? (
                      <img src={user.avatar} alt={user.name} className="h-6 w-6 rounded-full object-cover" />
                    ) : (
                      <div className="h-6 w-6 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
                        <span className="text-white text-xs font-bold">{user.name?.[0]?.toUpperCase() || 'U'}</span>
                      </div>
                    )}
                  </Link>
                ) : (
                  <Link href="/login">
                    <Button size="sm" className="rounded-full">
                      Sign In
                    </Button>
                  </Link>
                )}
              </div>

              {/* Mobile Menu */}
              <div className="lg:hidden">
                <MobileNavSheet
                  trigger={
                    <button className="p-2 rounded-full hover:bg-muted transition-colors" title="Menu" aria-label="Open menu">
                      <Menu className="h-5 w-5" />
                    </button>
                  }
                />
              </div>
            </div>
          </div>
        </div>
      </header>
    </>
  );
}

export default PrimaryNav;
