import { motion } from 'framer-motion';
import { Leaf, Award, Shield, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  SustainabilityRating, 
  SustainabilityBadge,
  SustainabilityComparison 
} from './SustainabilityRating';
import { EcoBadgeGroup, type EcoBadgeType } from './EcoBadge';
import { ImpactBreakdown } from './ImpactBreakdown';
import { useSustainabilityScore, type SustainabilityScore } from '@/hooks/useSustainability';
import { createTransition } from '@/motion';

interface ProductSustainabilityProps {
  productId: string;
  brandId?: string;
  className?: string;
}

export function ProductSustainability({ 
  productId, 
  brandId,
  className = '' 
}: ProductSustainabilityProps) {
  const { score, loading, error } = useSustainabilityScore(productId);

  if (loading) {
    return <ProductSustainabilitySkeleton />;
  }

  if (error || !score) {
    return null; // Don't show if no data available
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={createTransition({ duration: 0.5 })}
      className={className}
    >
      <Card className="overflow-hidden border-green-500/20">
        <CardHeader className="bg-gradient-to-r from-green-500/5 to-emerald-500/5 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Leaf className="h-5 w-5 text-green-500" />
              <CardTitle className="text-lg font-semibold">
                Sustainability Score
              </CardTitle>
            </div>
            {score.verified && (
              <div className="flex items-center gap-1.5 text-xs text-green-600 bg-green-500/10 px-2 py-1 rounded-full">
                <Shield className="h-3 w-3" />
                <span>Verified</span>
              </div>
            )}
          </div>
        </CardHeader>
        
        <CardContent className="pt-4 space-y-4">
          {/* Main Rating */}
          <SustainabilityRating
            score={score.overall_score}
            tier={score.tier}
            showBreakdown
            materialScore={score.material_score}
            brandScore={score.brand_score}
            manufacturingScore={score.manufacturing_score}
            shippingScore={score.shipping_score}
          />

          {/* Category Comparison */}
          {score.category_average && (
            <SustainabilityComparison
              score={score.overall_score}
              categoryAverage={score.category_average}
            />
          )}

          {/* Eco Badges */}
          {score.eco_badges.length > 0 && (
            <div className="pt-2">
              <h4 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                <Award className="h-4 w-4" />
                Eco Certifications
              </h4>
              <EcoBadgeGroup 
                badges={score.eco_badges as EcoBadgeType[]} 
                size="sm"
                maxVisible={4}
              />
            </div>
          )}

          {/* Impact Breakdown */}
          {Object.keys(score.impact_breakdown).length > 0 && (
            <div className="pt-2">
              <h4 className="text-sm font-medium text-muted-foreground mb-3">
                Environmental Impact
              </h4>
              <ImpactBreakdown breakdown={score.impact_breakdown} />
            </div>
          )}

          {/* Learn More Link */}
          <motion.a
            href="/sustainability"
            className="flex items-center gap-1.5 text-sm text-green-600 hover:text-green-700 transition-colors pt-2"
            whileHover={{ x: 2 }}
          >
            <span>Learn about our sustainability standards</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </motion.a>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Compact version for product cards
interface ProductSustainabilityBadgeProps {
  productId: string;
  className?: string;
}

export function ProductSustainabilityBadge({ 
  productId,
  className = '' 
}: ProductSustainabilityBadgeProps) {
  const { score, loading } = useSustainabilityScore(productId);

  if (loading || !score) {
    return null;
  }

  return (
    <SustainabilityBadge
      score={score.overall_score}
      tier={score.tier}
      className={className}
    />
  );
}

// Skeleton for loading state
export function ProductSustainabilitySkeleton() {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded-full" />
          <Skeleton className="h-5 w-32" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-4 w-16" />
          </div>
        </div>
        <Skeleton className="h-2 w-full" />
        <div className="grid grid-cols-2 gap-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </CardContent>
    </Card>
  );
}

// Summary widget for product listing
interface SustainabilitySummaryProps {
  productId: string;
  className?: string;
}

export function SustainabilitySummary({ 
  productId,
  className = '' 
}: SustainabilitySummaryProps) {
  const { score, loading } = useSustainabilityScore(productId);

  if (loading || !score) {
    return null;
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <SustainabilityBadge score={score.overall_score} tier={score.tier} />
      {score.eco_badges.length > 0 && (
        <EcoBadgeGroup 
          badges={score.eco_badges.slice(0, 2) as EcoBadgeType[]} 
          size="sm"
        />
      )}
    </div>
  );
}

export default ProductSustainability;
