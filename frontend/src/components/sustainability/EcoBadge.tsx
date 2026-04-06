import { motion } from 'framer-motion';
import { 
  Leaf, Recycle, Handshake, Cloud, Droplet, TreePine, 
  Heart, Palette, Sprout, RefreshCw, Award, ShieldCheck, 
  Infinity, BadgeCheck
} from 'lucide-react';
import { createTransition } from '@/motion';
import {
  Tooltip, 
  TooltipContent, 
  TooltipProvider, 
  TooltipTrigger 
} from '@/components/ui/tooltip';

export type EcoBadgeType = 
  | 'organic'
  | 'recycled'
  | 'fair_trade'
  | 'carbon_neutral'
  | 'water_saved'
  | 'sustainable_materials'
  | 'ethical_manufacturing'
  | 'low_impact_dye'
  | 'biodegradable'
  | 'upcycled'
  | 'gots_certified'
  | 'bluesign'
  | 'cradle_to_cradle';

interface EcoBadgeProps {
  type: EcoBadgeType;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  animated?: boolean;
}

const BADGE_CONFIG: Record<EcoBadgeType, {
  icon: React.ElementType;
  label: string;
  description: string;
  color: string;
  bgColor: string;
}> = {
  organic: {
    icon: Leaf,
    label: 'Organic',
    description: 'Made with certified organic materials',
    color: '#22c55e',
    bgColor: 'rgba(34, 197, 94, 0.15)',
  },
  recycled: {
    icon: Recycle,
    label: 'Recycled',
    description: 'Contains recycled materials',
    color: '#3b82f6',
    bgColor: 'rgba(59, 130, 246, 0.15)',
  },
  fair_trade: {
    icon: Handshake,
    label: 'Fair Trade',
    description: 'Fair trade certified',
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.15)',
  },
  carbon_neutral: {
    icon: Cloud,
    label: 'Carbon Neutral',
    description: 'Carbon neutral production and shipping',
    color: '#06b6d4',
    bgColor: 'rgba(6, 182, 212, 0.15)',
  },
  water_saved: {
    icon: Droplet,
    label: 'Water Saved',
    description: 'Low water usage in production',
    color: '#0ea5e9',
    bgColor: 'rgba(14, 165, 233, 0.15)',
  },
  sustainable_materials: {
    icon: TreePine,
    label: 'Sustainable Materials',
    description: 'Made with sustainable materials',
    color: '#84cc16',
    bgColor: 'rgba(132, 204, 22, 0.15)',
  },
  ethical_manufacturing: {
    icon: Heart,
    label: 'Ethical Manufacturing',
    description: 'Ethically manufactured with fair labor practices',
    color: '#ec4899',
    bgColor: 'rgba(236, 72, 153, 0.15)',
  },
  low_impact_dye: {
    icon: Palette,
    label: 'Low Impact Dye',
    description: 'Uses eco-friendly dyes',
    color: '#8b5cf6',
    bgColor: 'rgba(139, 92, 246, 0.15)',
  },
  biodegradable: {
    icon: Sprout,
    label: 'Biodegradable',
    description: 'Made from biodegradable materials',
    color: '#10b981',
    bgColor: 'rgba(16, 185, 129, 0.15)',
  },
  upcycled: {
    icon: RefreshCw,
    label: 'Upcycled',
    description: 'Made from upcycled materials',
    color: '#f97316',
    bgColor: 'rgba(249, 115, 22, 0.15)',
  },
  gots_certified: {
    icon: Award,
    label: 'GOTS Certified',
    description: 'Global Organic Textile Standard certified',
    color: '#14b8a6',
    bgColor: 'rgba(20, 184, 166, 0.15)',
  },
  bluesign: {
    icon: ShieldCheck,
    label: 'Bluesign',
    description: 'Bluesign certified for sustainable textiles',
    color: '#6366f1',
    bgColor: 'rgba(99, 102, 241, 0.15)',
  },
  cradle_to_cradle: {
    icon: Infinity,
    label: 'Cradle to Cradle',
    description: 'Cradle to Cradle certified',
    color: '#a855f7',
    bgColor: 'rgba(168, 85, 247, 0.15)',
  },
};

const SIZE_CONFIG = {
  sm: {
    container: 'gap-1 px-2 py-0.5 text-xs',
    icon: 'h-3 w-3',
  },
  md: {
    container: 'gap-1.5 px-3 py-1 text-sm',
    icon: 'h-4 w-4',
  },
  lg: {
    container: 'gap-2 px-4 py-1.5 text-base',
    icon: 'h-5 w-5',
  },
};

export function EcoBadge({ 
  type, 
  size = 'md', 
  showLabel = true,
  animated = true 
}: EcoBadgeProps) {
  const config = BADGE_CONFIG[type];
  const sizeConfig = SIZE_CONFIG[size];
  const Icon = config.icon;

  const BadgeContent = (
    <motion.div
      initial={animated ? { scale: 0.8, opacity: 0 } : false}
      animate={animated ? { scale: 1, opacity: 1 } : false}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.98 }}
      className={`
        inline-flex items-center rounded-full font-medium
        transition-colors duration-200 cursor-pointer
        ${sizeConfig.container}
      `}
      style={{
        backgroundColor: config.bgColor,
        color: config.color,
      }}
    >
      <Icon 
        className={sizeConfig.icon} 
        style={{ color: config.color }}
        strokeWidth={2.5}
      />
      {showLabel && (
        <span className="font-semibold">{config.label}</span>
      )}
    </motion.div>
  );

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          {BadgeContent}
        </TooltipTrigger>
        <TooltipContent 
          side="top" 
          className="max-w-xs bg-charcoal/95 text-white border-border"
        >
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4" style={{ color: config.color }} />
            <span className="font-semibold">{config.label}</span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {config.description}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface EcoBadgeGroupProps {
  badges: EcoBadgeType[];
  size?: 'sm' | 'md' | 'lg';
  maxVisible?: number;
  className?: string;
}

export function EcoBadgeGroup({ 
  badges, 
  size = 'sm',
  maxVisible = 3,
  className = ''
}: EcoBadgeGroupProps) {
  const visibleBadges = badges.slice(0, maxVisible);
  const remainingCount = badges.length - maxVisible;

  if (badges.length === 0) return null;

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      {visibleBadges.map((badge, index) => (
        <motion.div
          key={badge}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={createTransition({ delay: index * 0.1 })}
        >
          <EcoBadge type={badge} size={size} showLabel={size !== 'sm'} />
        </motion.div>
      ))}
      
      {remainingCount > 0 && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={createTransition({ delay: maxVisible * 0.1 })}
                className="inline-flex items-center justify-center rounded-full bg-muted text-muted-foreground text-xs font-medium px-2 py-0.5 cursor-pointer hover:bg-muted/80"
              >
                +{remainingCount}
              </motion.div>
            </TooltipTrigger>
            <TooltipContent side="top" className="bg-charcoal/95 text-white">
              <div className="flex flex-wrap gap-1 max-w-xs">
                {badges.slice(maxVisible).map(badge => (
                  <EcoBadge 
                    key={badge} 
                    type={badge} 
                    size="sm" 
                    showLabel={false}
                    animated={false}
                  />
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}

export default EcoBadge;
