/**
 * CONFIT — User Style Profile (USP) Editor
 * ==========================================
 * Lets users define/edit their style DNA used for personalized recommendations.
 * Categories: Body type, preferred colors, style preferences, occasion preferences,
 * budget range, and brand affinities.
 */

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  User,
  Palette,
  Heart,
  Target,
  DollarSign,
  Tag,
  Save,
  Sparkles,
  Check,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import { createTransition } from '@/motion';

// ─── Types ───

interface StyleProfile {
  body_type: string;
  height_cm: number;
  preferred_colors: string[];
  avoided_colors: string[];
  style_preferences: string[];
  occasion_preferences: string[];
  budget_range: [number, number]; // min, max in EGP
  brand_affinities: string[];
  size_top: string;
  size_bottom: string;
  shoe_size: string;
}

const DEFAULT_PROFILE: StyleProfile = {
  body_type: '',
  height_cm: 170,
  preferred_colors: [],
  avoided_colors: [],
  style_preferences: [],
  occasion_preferences: [],
  budget_range: [500, 5000],
  brand_affinities: [],
  size_top: '',
  size_bottom: '',
  shoe_size: '',
};

// ─── Data ───

const BODY_TYPES = ['Slim', 'Athletic', 'Average', 'Curvy', 'Plus Size', 'Petite', 'Tall'];

const COLORS = [
  { name: 'Black', hex: '#000000' },
  { name: 'White', hex: '#FFFFFF' },
  { name: 'Navy', hex: '#1E3A5F' },
  { name: 'Burgundy', hex: '#722F37' },
  { name: 'Olive', hex: '#556B2F' },
  { name: 'Beige', hex: '#C8B68E' },
  { name: 'Grey', hex: '#808080' },
  { name: 'Blush', hex: '#DE5D83' },
  { name: 'Camel', hex: '#C19A6B' },
  { name: 'Emerald', hex: '#50C878' },
  { name: 'Royal Blue', hex: '#4169E1' },
  { name: 'Coral', hex: '#FF7F50' },
];

const STYLE_PREFS = [
  'Minimalist', 'Classic', 'Streetwear', 'Bohemian', 'Preppy',
  'Romantic', 'Edgy', 'Sporty', 'Luxury', 'Smart Casual',
  'Modest', 'Vintage', 'Avant-Garde', 'Athleisure',
];

const OCCASIONS = [
  'Work', 'Casual', 'Party', 'Wedding', 'Date Night',
  'Travel', 'Sport', 'Formal Event', 'Beach', 'Smart Casual',
];

const BRANDS = ['Zahra', 'Town Team', 'Tie House', 'Tomato', 'Zara', 'H&M', 'Nike', 'Adidas'];

// ─── Chip Selector ───

function ChipGroup({
  label,
  options,
  selected,
  onToggle,
  max,
  isColor,
}: {
  label: string;
  options: (string | { name: string; hex: string })[];
  selected: string[];
  onToggle: (val: string) => void;
  max?: number;
  isColor?: boolean;
}) {
  return (
    <div>
      <Label className="text-sm font-medium mb-2 block">{label}</Label>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const name = typeof opt === 'string' ? opt : opt.name;
          const hex = typeof opt === 'string' ? undefined : opt.hex;
          const isSelected = selected.includes(name);
          const isDisabled = !isSelected && max !== undefined && selected.length >= max;

          return (
            <button
              key={name}
              type="button"
              onClick={() => !isDisabled && onToggle(name)}
              disabled={isDisabled}
              className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all',
                isSelected
                  ? 'bg-accent/20 border-accent/40 text-accent'
                  : 'border-border hover:border-accent/30 text-muted-foreground hover:text-foreground',
                isDisabled && 'opacity-40 cursor-not-allowed'
              )}
            >
              {isColor && hex && (
                <span
                  className="h-3 w-3 rounded-full border border-white/20 flex-shrink-0"
                  style={{ background: hex }}
                />
              )}
              {isSelected && <Check className="h-3 w-3" />}
              {name}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Section Card ───

function Section({
  icon,
  title,
  subtitle,
  children,
  index = 0,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={createTransition({ delay: index * 0.08 })}
      className="glass-card rounded-2xl p-6 space-y-4"
    >
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
          {icon}
        </div>
        <div>
          <h3 className="font-semibold text-sm">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      {children}
    </motion.div>
  );
}

// ─── Main Component ───

interface UserStyleProfileProps {
  initialProfile?: Partial<StyleProfile>;
  onSave?: (profile: StyleProfile) => void;
  className?: string;
}

export function UserStyleProfile({ initialProfile, onSave, className }: UserStyleProfileProps) {
  const [profile, setProfile] = useState<StyleProfile>({
    ...DEFAULT_PROFILE,
    ...initialProfile,
  });
  const [isSaving, setIsSaving] = useState(false);

  const toggleArrayField = useCallback((field: keyof StyleProfile, value: string) => {
    setProfile((prev) => {
      const arr = prev[field] as string[];
      return {
        ...prev,
        [field]: arr.includes(value)
          ? arr.filter((v) => v !== value)
          : [...arr, value],
      };
    });
  }, []);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      // Save to backend if callback provided
      if (onSave) {
        onSave(profile);
      }
      // Also persist to localStorage as fallback
      localStorage.setItem('confit_style_profile', JSON.stringify(profile));
      toast.success('Style Profile Saved', {
        description: 'Your preferences will be used across the platform.',
      });
    } catch {
      toast.error('Failed to save profile');
    } finally {
      setIsSaving(false);
    }
  }, [profile, onSave]);

  return (
    <div className={cn('space-y-6 max-w-3xl mx-auto', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight" style={{ fontFamily: "'Playfair Display', serif" }}>
              Your Style DNA
            </h2>
            <p className="text-xs text-muted-foreground">Tell CONFIT what you love — get better recommendations</p>
          </div>
        </div>
        <Button
          onClick={handleSave}
          disabled={isSaving}
          className="gap-2"
          variant="hero"
        >
          <Save className="h-4 w-4" />
          {isSaving ? 'Saving...' : 'Save Profile'}
        </Button>
      </div>

      {/* Body & Sizing */}
      <Section icon={<User className="h-4 w-4" />} title="Body & Sizing" subtitle="Helps us find the right fit" index={0}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <Label className="text-xs">Body Type</Label>
            <Select value={profile.body_type} onValueChange={(v) => setProfile({ ...profile, body_type: v })}>
              <SelectTrigger className="h-9 text-xs mt-1"><SelectValue placeholder="Select..." /></SelectTrigger>
              <SelectContent>
                {BODY_TYPES.map(b => <SelectItem key={b} value={b}>{b}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Height (cm)</Label>
            <Input
              type="number"
              value={profile.height_cm}
              onChange={(e) => setProfile({ ...profile, height_cm: parseInt(e.target.value) || 170 })}
              className="h-9 text-xs mt-1"
              min={120}
              max={220}
            />
          </div>
          <div>
            <Label className="text-xs">Top Size</Label>
            <Select value={profile.size_top} onValueChange={(v) => setProfile({ ...profile, size_top: v })}>
              <SelectTrigger className="h-9 text-xs mt-1"><SelectValue placeholder="Size..." /></SelectTrigger>
              <SelectContent>
                {['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'].map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Bottom Size</Label>
            <Select value={profile.size_bottom} onValueChange={(v) => setProfile({ ...profile, size_bottom: v })}>
              <SelectTrigger className="h-9 text-xs mt-1"><SelectValue placeholder="Size..." /></SelectTrigger>
              <SelectContent>
                {['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'].map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      </Section>

      {/* Colors */}
      <Section icon={<Palette className="h-4 w-4" />} title="Color Preferences" subtitle="Select colors you love" index={1}>
        <ChipGroup
          label="Preferred Colors"
          options={COLORS}
          selected={profile.preferred_colors}
          onToggle={(v) => toggleArrayField('preferred_colors', v)}
          max={8}
          isColor
        />
        <ChipGroup
          label="Colors to Avoid"
          options={COLORS}
          selected={profile.avoided_colors}
          onToggle={(v) => toggleArrayField('avoided_colors', v)}
          max={4}
          isColor
        />
      </Section>

      {/* Style Preferences */}
      <Section icon={<Heart className="h-4 w-4" />} title="Style Preferences" subtitle="What describes your aesthetic?" index={2}>
        <ChipGroup
          label=""
          options={STYLE_PREFS}
          selected={profile.style_preferences}
          onToggle={(v) => toggleArrayField('style_preferences', v)}
          max={5}
        />
      </Section>

      {/* Occasions */}
      <Section icon={<Target className="h-4 w-4" />} title="Occasion Preferences" subtitle="When do you usually dress up?" index={3}>
        <ChipGroup
          label=""
          options={OCCASIONS}
          selected={profile.occasion_preferences}
          onToggle={(v) => toggleArrayField('occasion_preferences', v)}
          max={6}
        />
      </Section>

      {/* Budget */}
      <Section icon={<DollarSign className="h-4 w-4" />} title="Budget Range" subtitle="Per-item budget in EGP" index={4}>
        <div className="px-2">
          <Slider
            value={profile.budget_range}
            onValueChange={(v) => setProfile({ ...profile, budget_range: v as [number, number] })}
            min={100}
            max={20000}
            step={100}
            className="my-4"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>EGP {profile.budget_range[0].toLocaleString()}</span>
            <span>EGP {profile.budget_range[1].toLocaleString()}</span>
          </div>
        </div>
      </Section>

      {/* Brand Affinities */}
      <Section icon={<Tag className="h-4 w-4" />} title="Brand Affinities" subtitle="Brands you love" index={5}>
        <ChipGroup
          label=""
          options={BRANDS}
          selected={profile.brand_affinities}
          onToggle={(v) => toggleArrayField('brand_affinities', v)}
          max={6}
        />
      </Section>
    </div>
  );
}

export default UserStyleProfile;
