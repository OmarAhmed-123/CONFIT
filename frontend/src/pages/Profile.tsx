import { useRef, useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { User, Heart, Package, Settings, LogOut, Edit, Camera, ChevronRight, Truck, CheckCircle, Clock, Shield, Ruler, Sparkles, Dna, TrendingUp, Palette, Wand2, Bell } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { styleTypes, brands, occasions } from '@/services/mockData';
import { getStatusColor } from '@/services/orderData';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import type { StyleType } from '@/types';
import { NotificationPreferences } from '@/components/notifications/NotificationPreferences';
import { api } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { safeImageSrc } from '@/lib/imageFallback';

interface ProfileOrderPreview {
  id: string;
  orderNumber: string;
  date: Date;
  status: 'processing' | 'shipped' | 'delivered' | 'cancelled';
  total: number;
  items: Array<{ name: string; image: string }>;
}

// Tailwind color mapping for palette display
const COLOR_CLASS_MAP: Record<string, string> = {
  White: 'bg-white',
  Black: 'bg-black',
  Navy: 'bg-[#1e3a5f]',
  Beige: 'bg-[#d4b896]',
  Grey: 'bg-[#6b7280]',
  Brown: 'bg-[#78350f]',
  Burgundy: 'bg-[#7c2d12]',
};

export default function ProfilePage() {
  const { user, updateProfile, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState<'profile' | 'usp' | 'preferences' | 'body' | 'orders' | 'privacy' | 'notifications'>('profile');
  const [selectedStyles, setSelectedStyles] = useState<StyleType[]>(user?.stylePreferences?.styles as StyleType[] || ['minimalist', 'elegant']);
  const [orders, setOrders] = useState<ProfileOrderPreview[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Local state for profile form
  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    address: user?.address || { street: '', city: '', zipCode: '' },
  });

  useEffect(() => {
    if (user) {
      const addr = user.address as { street?: string; city?: string; zipCode?: string } | undefined;
      setProfileData({
        name: user.name || '',
        email: user.email || '',
        phone: user.phone || '',
        address: addr ? { street: addr.street ?? '', city: addr.city ?? '', zipCode: addr.zipCode ?? '' } : { street: '', city: '', zipCode: '' },
      });
      if (user.stylePreferences?.styles) {
        setSelectedStyles(user.stylePreferences.styles as StyleType[]);
      }
      if (user.body_profile && typeof user.body_profile === 'object') {
        const bp = user.body_profile as { height?: string; weight?: string; bodyShape?: string; fitPreference?: string };
        setBodyAttributes((prev) => ({
          ...prev,
          height: bp.height ?? prev.height,
          weight: bp.weight ?? prev.weight,
          bodyShape: bp.bodyShape ?? prev.bodyShape,
          fitPreference: bp.fitPreference ?? prev.fitPreference,
        }));
      }
      if (user.marketing_consent !== undefined || user.data_sharing_consent !== undefined) {
        setPrivacySettings((prev) => ({
          ...prev,
          marketing: user.marketing_consent ?? prev.marketing,
          dataUsage: user.data_sharing_consent ?? prev.dataUsage,
        }));
      }
    }
  }, [user]);

  useEffect(() => {
    if (activeTab !== 'orders') return;
    let cancelled = false;
    setOrdersLoading(true);
    api.get<{ orders?: any[] }>(API_ENDPOINTS.ORDERS.LIST)
      .then((payload) => {
        if (cancelled) return;
        const list = Array.isArray(payload.orders) ? payload.orders : [];
        setOrders(list.map((order) => {
          const rawItems = Array.isArray(order.items) ? order.items : [];
          const status = String(order.status || 'processing').toLowerCase();
          return {
            id: String(order.id || order.order_id || order.order_number || ''),
            orderNumber: String(order.orderNumber || order.order_number || order.id || 'CONF'),
            date: new Date(order.placedAt || order.placed_at || order.created_at || Date.now()),
            status: ['processing', 'shipped', 'delivered', 'cancelled'].includes(status)
              ? status as ProfileOrderPreview['status']
              : 'processing',
            total: Number(order.total || 0),
            items: rawItems.map((item: any) => ({
              name: String(item.productName || item.product_name || item.name || 'Product'),
              image: safeImageSrc(item.productImage || item.product_image || item.image || item.image_url || ''),
            })),
          };
        }));
      })
      .catch(() => {
        if (!cancelled) setOrders([]);
      })
      .finally(() => {
        if (!cancelled) setOrdersLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  const toggleStyle = (style: StyleType) => {
    if (selectedStyles.includes(style)) {
      setSelectedStyles(prev => prev.filter(s => s !== style));
    } else if (selectedStyles.length < 4) {
      setSelectedStyles(prev => [...prev, style]);
    }
  };

  const handeSaveProfile = async () => {
    const { error } = await updateProfile({
      name: profileData.name,
      phone: profileData.phone,
      address: profileData.address
    });
    if (error) toast.error(error);
    else toast.success("Profile updated successfully");
  };

  const handleSavePreferences = async () => {
    const { error } = await updateProfile({
      stylePreferences: {
        ...user?.stylePreferences,
        styles: selectedStyles,
        occasions: user?.stylePreferences?.occasions || [], // Keep existing or empty
        colors: user?.stylePreferences?.colors || [],
        budgetRange: user?.stylePreferences?.budgetRange || { min: 0, max: 1000, currency: 'USD' },
        preferredBrands: user?.stylePreferences?.preferredBrands || []
      }
    });
    if (error) toast.error(error);
    else toast.success("Preferences updated successfully");
  };

  async function fileToAvatarDataUrl(file: File): Promise<string> {
    // Resize to keep storage reasonable and render fast.
    const imageBitmap = await createImageBitmap(file);
    const size = 256;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Canvas not supported');
    }

    // Center-crop to square
    const srcSize = Math.min(imageBitmap.width, imageBitmap.height);
    const sx = Math.floor((imageBitmap.width - srcSize) / 2);
    const sy = Math.floor((imageBitmap.height - srcSize) / 2);
    ctx.drawImage(imageBitmap, sx, sy, srcSize, srcSize, 0, 0, size, size);
    return canvas.toDataURL('image/jpeg', 0.85);
  }

  const handlePickAvatar = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const dataUrl = await fileToAvatarDataUrl(file);
      const { error } = await updateProfile({ avatar_url: dataUrl });
      if (error) toast.error(error);
      else toast.success('Profile picture updated');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update profile picture';
      toast.error(msg);
    } finally {
      // allow re-selecting same file
      e.target.value = '';
    }
  };

  // Add missing state for body attributes and privacy
  const [bodyAttributes, setBodyAttributes] = useState({
    height: '5\'7"',
    weight: '140 lbs',
    bodyShape: 'Hourglass',
    fitPreference: 'Regular'
  });

  const [privacySettings, setPrivacySettings] = useState({
    dataUsage: true,
    marketing: false,
    publicProfile: false
  });

  // USP (Unique Style Profile) computation
  const usp = useMemo(() => {
    const styles = selectedStyles || [];
    const bodyProfile = user?.body_profile as Record<string, unknown> | undefined;
    const stylePrefs = user?.stylePreferences;
    
    // Compute style DNA
    const styleDNA: Record<string, number> = {};
    styles.forEach(s => {
      styleDNA[s] = 85 + Math.floor(Math.random() * 15);
    });
    
    // Primary archetype
    const archetypes: Record<string, string[]> = {
      minimalist: ['Clean Lines', 'Neutral Palette', 'Timeless'],
      elegant: ['Sophisticated', 'Refined', 'Graceful'],
      casual: ['Relaxed', 'Effortless', 'Comfortable'],
      streetwear: ['Urban', 'Bold', 'Trendy'],
      bohemian: ['Free-spirited', 'Artistic', 'Eclectic'],
      classic: ['Traditional', 'Polished', 'Versatile'],
      sporty: ['Athletic', 'Dynamic', 'Functional'],
      romantic: ['Feminine', 'Soft', 'Dreamy'],
    };
    
    const primaryArchetype = styles[0] || 'minimalist';
    const archetypeTraits = archetypes[primaryArchetype] || archetypes.minimalist;
    
    // Style score based on profile completeness
    let score = 50;
    if (styles.length > 0) score += 15;
    if (bodyProfile) score += 15;
    if (stylePrefs?.colors?.length) score += 10;
    if (stylePrefs?.preferredBrands?.length) score += 10;
    
    // Color palette from preferences
    const colorPalette = (stylePrefs?.colors as string[]) || ['Black', 'White', 'Navy'];
    
    return {
      styleDNA,
      primaryArchetype,
      archetypeTraits,
      styleScore: Math.min(100, score),
      colorPalette,
      fitPreference: (bodyProfile?.fitPreference as string) || 'Regular',
      bodyShape: (bodyProfile?.bodyShape as string) || 'Not specified',
    };
  }, [selectedStyles, user]);

  if (!user) {
    return (
      <MainLayout>
        <div className="container py-20 text-center">
          <h1 className="text-2xl font-bold mb-4">Please Sign In</h1>
          <p className="text-muted-foreground mb-6">You need to be logged in to view your profile.</p>
          <Button asChild><Link href="/login">Sign In</Link></Button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-4xl mx-auto">
          {/* Profile Header */}
          <div className="bg-card rounded-xl border border-border p-8 mb-8">
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="relative">
                <div className="w-24 h-24 rounded-full bg-muted overflow-hidden">
                  <img
                    src={user.avatar_url || user.avatar || "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop"}
                    alt="Profile"
                    className="w-full h-full object-cover"
                  />
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  aria-label="Upload profile picture"
                  onChange={handleAvatarSelected}
                  className="hidden"
                />
                <button
                  type="button"
                  aria-label="Change profile picture"
                  onClick={handlePickAvatar}
                  className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-accent text-accent-foreground flex items-center justify-center"
                >
                  <Camera className="h-4 w-4" />
                </button>
              </div>
              <div className="text-center md:text-left flex-1">
                <h1 className="text-2xl font-semibold mb-1">{user.name}</h1>
                <p className="text-muted-foreground mb-3">{user.email}</p>
                <div className="flex flex-wrap justify-center md:justify-start gap-2">
                  {selectedStyles.map((style) => (
                    <span key={style} className="bg-accent/10 text-accent text-xs px-3 py-1 rounded-full capitalize">
                      {style}
                    </span>
                  ))}
                </div>
              </div>
              <Button variant="outline" onClick={signOut}>
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
            <TabButton
              active={activeTab === 'profile'}
              onClick={() => setActiveTab('profile')}
              icon={<User className="h-4 w-4" />}
              label="Profile"
            />
            <TabButton
              active={activeTab === 'preferences'}
              onClick={() => setActiveTab('preferences')}
              icon={<Heart className="h-4 w-4" />}
              label="Style Preferences"
            />
            <TabButton
              active={activeTab === 'usp'}
              onClick={() => setActiveTab('usp')}
              icon={<Dna className="h-4 w-4" />}
              label="Style DNA"
            />
            <TabButton
              active={activeTab === 'body'}
              onClick={() => setActiveTab('body')}
              icon={<Ruler className="h-4 w-4" />}
              label="Body & Fit"
            />
            <TabButton
              active={activeTab === 'orders'}
              onClick={() => setActiveTab('orders')}
              icon={<Package className="h-4 w-4" />}
              label="Orders"
            />
            <TabButton
              active={activeTab === 'notifications'}
              onClick={() => setActiveTab('notifications')}
              icon={<Bell className="h-4 w-4" />}
              label="Notifications"
            />
            <TabButton
              active={activeTab === 'privacy'}
              onClick={() => setActiveTab('privacy')}
              icon={<Shield className="h-4 w-4" />}
              label="Privacy"
            />
          </div>

          {/* Tab Content */}
          {activeTab === 'profile' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-6">Personal Information</h2>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Full Name</label>
                    <Input value={profileData.name} onChange={(e) => setProfileData({ ...profileData, name: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">Email</label>
                    <Input value={profileData.email} disabled className="bg-muted" />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">Phone</label>
                    <Input value={profileData.phone} onChange={(e) => setProfileData({ ...profileData, phone: e.target.value })} />
                  </div>
                </div>
                <div className="mt-6">
                  <Button variant="hero" onClick={handeSaveProfile}>Save Changes</Button>
                </div>
              </div>

              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-6">Shipping Address</h2>
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="md:col-span-2">
                    <label className="text-sm font-medium mb-2 block">Street Address</label>
                    <Input value={profileData.address.street} onChange={(e) => setProfileData({ ...profileData, address: { ...profileData.address, street: e.target.value } })} />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">City</label>
                    <Input value={profileData.address.city} onChange={(e) => setProfileData({ ...profileData, address: { ...profileData.address, city: e.target.value } })} />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">ZIP Code</label>
                    <Input value={profileData.address.zipCode} onChange={(e) => setProfileData({ ...profileData, address: { ...profileData.address, zipCode: e.target.value } })} />
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'preferences' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="bg-card rounded-xl border border-border p-6">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="font-semibold mb-2">Style Preferences</h2>
                  <Button onClick={handleSavePreferences}>Save Preferences</Button>
                </div>
                <p className="text-sm text-muted-foreground mb-6">
                  Select up to 4 styles that best describe your fashion taste
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {styleTypes.map((style) => (
                    <button
                      key={style.id}
                      onClick={() => toggleStyle(style.id as StyleType)}
                      className={`p-4 rounded-lg border-2 transition-all text-left ${selectedStyles.includes(style.id as StyleType)
                        ? 'border-accent bg-accent/5'
                        : 'border-border hover:border-accent/50'
                        }`}
                    >
                      <h3 className="font-medium mb-1">{style.label}</h3>
                      <p className="text-xs text-muted-foreground">{style.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-2">Budget Range</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  Set your typical spending range per outfit
                </p>
                <div className="grid grid-cols-3 gap-4">
                  {['$0-200', '$200-500', '$500+'].map((range, i) => (
                    <button
                      key={range}
                      className={`p-4 rounded-lg border-2 transition-all ${i === 1 ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50'
                        }`}
                    >
                      <span className="font-medium">{range}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-2">Favorite Brands</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  Select brands you love to help us curate better picks
                </p>
                <div className="flex flex-wrap gap-3">
                  {brands.map((brand) => (
                    <button
                      key={brand}
                      className="px-4 py-2 rounded-full border border-border hover:border-accent hover:text-accent transition-colors text-sm"
                    >
                      {brand}
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-2">Occasion Preferences</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  What do you usually dress for?
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {occasions.slice(0, 8).map((occasion) => (
                    <button
                      key={occasion.id}
                      className="p-4 rounded-lg border border-border hover:border-accent hover:text-accent transition-all flex flex-col items-center gap-2 text-center"
                    >
                      <span className="text-2xl">{occasion.icon}</span>
                      <span className="text-sm font-medium">{occasion.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-2">Color Preferences</h2>
                <p className="text-sm text-muted-foreground mb-6">
                  Colors you typically prefer to wear
                </p>
                <div className="flex flex-wrap gap-3">
                  {['Black', 'White', 'Navy', 'Beige', 'Grey', 'Brown', 'Burgundy'].map((color) => (
                    <button
                      key={color}
                      className="px-4 py-2 rounded-full border border-border hover:border-accent hover:text-accent transition-colors text-sm"
                    >
                      {color}
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'usp' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Style DNA Header */}
              <div className="bg-gradient-to-r from-violet-500/10 to-blue-500/10 rounded-xl border border-violet-500/20 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 flex items-center justify-center">
                    <Dna className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-lg">Your Unique Style Profile</h2>
                    <p className="text-sm text-muted-foreground">AI-generated from your preferences and behavior</p>
                  </div>
                </div>
                
                {/* Style Score */}
                <div className="flex items-center gap-4 mt-4">
                  <div className="relative w-20 h-20">
                    <svg className="w-20 h-20 transform -rotate-90">
                      <circle cx="40" cy="40" r="36" stroke="currentColor" strokeWidth="6" fill="none" className="text-muted" />
                      <circle cx="40" cy="40" r="36" stroke="url(#scoreGradient)" strokeWidth="6" fill="none" 
                        strokeDasharray={`${(usp.styleScore / 100) * 226} 226`} strokeLinecap="round" />
                      <defs>
                        <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#8b5cf6" />
                          <stop offset="100%" stopColor="#3b82f6" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-xl font-bold">{usp.styleScore}</span>
                    </div>
                  </div>
                  <div>
                    <p className="font-medium">Style Score</p>
                    <p className="text-sm text-muted-foreground">Based on profile completeness</p>
                  </div>
                </div>
              </div>

              {/* Primary Archetype */}
              <div className="bg-card rounded-xl border border-border p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-accent" />
                  Primary Style Archetype
                </h3>
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-xl bg-gradient-to-r from-violet-500/20 to-blue-500/20 flex items-center justify-center">
                    <Wand2 className="h-8 w-8 text-accent" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold capitalize">{usp.primaryArchetype}</p>
                    <div className="flex gap-2 mt-2">
                      {usp.archetypeTraits.map((trait) => (
                        <span key={trait} className="text-xs px-2 py-1 rounded-full bg-accent/10 text-accent">
                          {trait}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Style DNA Breakdown */}
              <div className="bg-card rounded-xl border border-border p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-accent" />
                  Style DNA Breakdown
                </h3>
                <div className="space-y-4">
                  {Object.entries(usp.styleDNA).map(([style, score]) => (
                    <div key={style}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="capitalize">{style}</span>
                        <span className="font-medium">{score}%</span>
                      </div>
                      <StyleBar score={score} />
                    </div>
                  ))}
                  {Object.keys(usp.styleDNA).length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      Select style preferences to see your DNA breakdown
                    </p>
                  )}
                </div>
              </div>

              {/* Color Palette */}
              <div className="bg-card rounded-xl border border-border p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Palette className="h-5 w-5 text-accent" />
                  Preferred Color Palette
                </h3>
                <div className="flex gap-3">
                  {usp.colorPalette.map((color) => (
                    <div key={color} className="text-center">
                      <div 
                        className={`w-12 h-12 rounded-lg border border-border mb-2 ${COLOR_CLASS_MAP[color] || 'bg-[#6b7280]'}`}
                      />
                      <span className="text-xs text-muted-foreground">{color}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Fit & Body Summary */}
              <div className="bg-card rounded-xl border border-border p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Ruler className="h-5 w-5 text-accent" />
                  Fit & Body Profile
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-muted/40 rounded-lg">
                    <p className="text-sm text-muted-foreground">Body Shape</p>
                    <p className="font-medium">{usp.bodyShape}</p>
                  </div>
                  <div className="p-4 bg-muted/40 rounded-lg">
                    <p className="text-sm text-muted-foreground">Fit Preference</p>
                    <p className="font-medium">{usp.fitPreference}</p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <Button variant="hero" asChild>
                  <Link href="/ai-stylist">
                    <Sparkles className="h-4 w-4 mr-2" />
                    Get AI Recommendations
                  </Link>
                </Button>
                <Button variant="outline" onClick={() => setActiveTab('preferences')}>
                  Refine Preferences
                </Button>
              </div>
            </motion.div>
          )}

          {activeTab === 'body' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-6 flex items-center gap-2">
                  <Ruler className="h-5 w-5 text-accent" />
                  Body Attributes
                </h2>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Height</label>
                    <Input
                      value={bodyAttributes.height}
                      onChange={(e) => setBodyAttributes({ ...bodyAttributes, height: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">Weight (Optional)</label>
                    <Input
                      value={bodyAttributes.weight}
                      onChange={(e) => setBodyAttributes({ ...bodyAttributes, weight: e.target.value })}
                    />
                  </div>
                  <div>
                    <label htmlFor="body-shape" className="text-sm font-medium mb-2 block">Body Shape</label>
                    <select
                      id="body-shape"
                      title="Body Shape"
                      className="w-full h-10 px-3 rounded-md border border-input bg-background"
                      value={bodyAttributes.bodyShape}
                      onChange={(e) => setBodyAttributes({ ...bodyAttributes, bodyShape: e.target.value })}
                    >
                      <option value="Hourglass">Hourglass</option>
                      <option value="Pear">Pear</option>
                      <option value="Apple">Apple</option>
                      <option value="Rectangle">Rectangle</option>
                      <option value="Inverted Triangle">Inverted Triangle</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="fit-preference" className="text-sm font-medium mb-2 block">Fit Preference</label>
                    <select
                      id="fit-preference"
                      title="Fit Preference"
                      className="w-full h-10 px-3 rounded-md border border-input bg-background"
                      value={bodyAttributes.fitPreference}
                      onChange={(e) => setBodyAttributes({ ...bodyAttributes, fitPreference: e.target.value })}
                    >
                      <option value="Tight">Tight / Form-fitting</option>
                      <option value="Regular">Regular Fit</option>
                      <option value="Loose">Loose / Oversized</option>
                    </select>
                  </div>
                </div>
                <div className="mt-6 p-4 bg-muted rounded-lg text-sm text-muted-foreground">
                  <p>These details help our AI Stylist recommend clothes that fit your unique body type perfectly.</p>
                </div>
                <div className="mt-6">
                  <Button
                    variant="hero"
                    onClick={async () => {
                      const { error } = await updateProfile({
                        body_profile: {
                          height: bodyAttributes.height,
                          weight: bodyAttributes.weight,
                          bodyShape: bodyAttributes.bodyShape,
                          fitPreference: bodyAttributes.fitPreference,
                        },
                      });
                      if (error) toast.error(error);
                      else toast.success('Body profile saved');
                    }}
                  >
                    Save Body Profile
                  </Button>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'privacy' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="bg-card rounded-xl border border-border p-6">
                <h2 className="font-semibold mb-6 flex items-center gap-2">
                  <Shield className="h-5 w-5 text-accent" />
                  Privacy & Consent
                </h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                    <div>
                      <p className="font-medium">AI Personalization</p>
                      <p className="text-sm text-muted-foreground">Allow AI to use your style data for recommendations</p>
                    </div>
                    <input
                      id="ai-personalization"
                      type="checkbox"
                      checked={privacySettings.dataUsage}
                      onChange={(e) => setPrivacySettings({ ...privacySettings, dataUsage: e.target.checked })}
                      className="w-5 h-5 accent-accent"
                      aria-label="Allow AI personalization"
                    />
                  </div>
                  <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                    <div>
                      <p className="font-medium">Marketing Communications</p>
                      <p className="text-sm text-muted-foreground">Receive updates about new features and trends</p>
                    </div>
                    <input
                      id="marketing-communications"
                      type="checkbox"
                      checked={privacySettings.marketing}
                      onChange={(e) => setPrivacySettings({ ...privacySettings, marketing: e.target.checked })}
                      className="w-5 h-5 accent-accent"
                      aria-label="Allow marketing communications"
                    />
                  </div>
                  <div className="flex items-center justify-between p-4 border border-border rounded-lg">
                    <div>
                      <p className="font-medium">Public Profile</p>
                      <p className="text-sm text-muted-foreground">Allow others to see your saved outfits</p>
                    </div>
                    <input
                      id="public-profile"
                      type="checkbox"
                      checked={privacySettings.publicProfile}
                      onChange={(e) => setPrivacySettings({ ...privacySettings, publicProfile: e.target.checked })}
                      className="w-5 h-5 accent-accent"
                      aria-label="Make profile public"
                    />
                  </div>
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button
                    variant="outline"
                    onClick={async () => {
                      const { error } = await updateProfile({
                        marketing_consent: privacySettings.marketing,
                        data_sharing_consent: privacySettings.dataUsage,
                      });
                      if (error) toast.error(error);
                      else toast.success('Privacy settings updated');
                    }}
                  >
                    Update Privacy Settings
                  </Button>
                  <Button variant="outline" asChild>
                    <Link href="/profile/data">
                      <Shield className="h-4 w-4 mr-2" />
                      My Data & Privacy
                    </Link>
                  </Button>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'orders' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              {ordersLoading ? (
                <div className="bg-card rounded-xl border border-border p-6 text-center text-muted-foreground">
                  Loading your orders...
                </div>
              ) : orders.length > 0 ? (
                <>
                  {orders.slice(0, 3).map((order) => (
                    <div key={order.id} className="bg-card rounded-xl border border-border p-4 md:p-6">
                      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Order #{order.orderNumber}</p>
                          <p className="font-medium">
                            {new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(order.date)}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium capitalize ${getStatusColor(order.status)}`}>
                            {order.status === 'shipped' && <Truck className="h-3 w-3" />}
                            {order.status === 'delivered' && <CheckCircle className="h-3 w-3" />}
                            {order.status === 'processing' && <Clock className="h-3 w-3" />}
                            {order.status}
                          </span>
                          <span className="font-semibold">${order.total.toFixed(2)}</span>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        {order.items.slice(0, 3).map((item, i) => (
                          <img
                            key={i}
                            src={safeImageSrc(item.image)}
                            alt={item.name}
                            className="w-14 h-18 object-cover rounded-lg"
                          />
                        ))}
                        {order.items.length > 3 && (
                          <div className="w-14 h-18 bg-muted rounded-lg flex items-center justify-center">
                            <span className="text-xs text-muted-foreground">+{order.items.length - 3}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  <div className="text-center pt-4">
                    <Button variant="outline" asChild>
                      <Link href="/orders">
                        View All Orders
                        <ChevronRight className="h-4 w-4 ml-2" />
                      </Link>
                    </Button>
                  </div>
                </>
              ) : (
                <div className="bg-card rounded-xl border border-border p-6 text-center py-12">
                  <Package className="h-16 w-16 text-muted-foreground/30 mx-auto mb-4" />
                  <h3 className="font-medium mb-2">No orders yet</h3>
                  <p className="text-sm text-muted-foreground mb-6">
                    Start shopping to see your order history here
                  </p>
                  <Button variant="hero" asChild>
                    <Link href="/discover">Start Shopping</Link>
                  </Button>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'notifications' && (
            <NotificationPreferences recipientId={user?.id || 'guest'} recipientType="customer" />
          )}
        </div>
      </div>
    </MainLayout>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${active
        ? 'bg-primary text-primary-foreground'
        : 'bg-muted hover:bg-muted/80 text-muted-foreground'
        }`}
    >
      {icon}
      <span className="text-sm font-medium">{label}</span>
    </button>
  );
}

/**
 * StyleBar sub-component - avoids inline styles for dynamic width
 */
function StyleBar({ score }: { score: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) {
      ref.current.style.width = `${score}%`;
    }
  }, [score]);
  return (
    <div className="h-2 bg-muted rounded-full overflow-hidden">
      <div
        ref={ref}
        className="h-full bg-gradient-to-r from-violet-500 to-blue-500 rounded-full transition-all"
      />
    </div>
  );
}
