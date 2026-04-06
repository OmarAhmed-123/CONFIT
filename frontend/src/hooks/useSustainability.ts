import { useState, useEffect } from 'react';
import { api } from '@/lib/api/client';

export type SustainabilityTier = 
  | 'excellent'
  | 'very_good'
  | 'good'
  | 'fair'
  | 'moderate'
  | 'low'
  | 'poor';

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

export interface ImpactMetric {
  value: number | string;
  unit: string;
  rating: 'excellent' | 'good' | 'moderate' | 'poor' | 'very_poor';
  description?: string;
}

export interface SustainabilityScore {
  product_id: string;
  overall_score: number;
  tier: SustainabilityTier;
  material_score: number;
  brand_score: number;
  manufacturing_score: number;
  shipping_score: number;
  eco_badges: EcoBadgeType[];
  certifications: string[];
  impact_breakdown: {
    carbon?: ImpactMetric;
    water?: ImpactMetric;
    chemicals?: ImpactMetric;
    waste?: ImpactMetric;
  };
  category_average?: number;
  percentile_rank?: number;
  verified: boolean;
  last_updated: string;
}

export interface BrandSustainability {
  brand_id: string;
  overall_score: number;
  environmental_score: number;
  social_score: number;
  governance_score: number;
  certifications: string[];
  eco_badges: EcoBadgeType[];
  sustainable_materials_pct: number;
  recycled_materials_pct: number;
  renewable_energy_usage: number;
  carbon_offset_program: boolean;
  living_wage_commitment: boolean;
  supply_chain_transparency: number;
  verification_status: string;
}

interface UseSustainabilityScoreResult {
  score: SustainabilityScore | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useSustainabilityScore(productId: string | null): UseSustainabilityScoreResult {
  const [score, setScore] = useState<SustainabilityScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchScore = async () => {
    if (!productId) {
      setScore(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await api.get<SustainabilityScore>(`/sustainability/products/${productId}`);
      setScore(data);
    } catch (err) {
      if (err instanceof Error && err.message.includes('404')) {
        // No sustainability data available for this product
        setScore(null);
      } else {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScore();
  }, [productId]);

  return {
    score,
    loading,
    error,
    refetch: fetchScore,
  };
}

interface UseBrandSustainabilityResult {
  brand: BrandSustainability | null;
  loading: boolean;
  error: Error | null;
}

export function useBrandSustainability(brandId: string | null): UseBrandSustainabilityResult {
  const [brand, setBrand] = useState<BrandSustainability | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!brandId) {
      setBrand(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.get<BrandSustainability | null>(`/sustainability/brands/${brandId}`)
      .then(data => {
        setBrand(data);
        setLoading(false);
      })
      .catch(err => {
        if (err instanceof Error && err.message.includes('404')) {
          setBrand(null);
        } else {
          setError(err instanceof Error ? err : new Error('Unknown error'));
        }
        setLoading(false);
      });
  }, [brandId]);

  return {
    brand,
    loading,
    error,
  };
}

interface UseTopSustainableProductsResult {
  products: SustainabilityScore[];
  loading: boolean;
  error: Error | null;
}

export function useTopSustainableProducts(
  category?: string,
  limit: number = 10
): UseTopSustainableProductsResult {
  const [products, setProducts] = useState<SustainabilityScore[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    api.get<SustainabilityScore[]>('/sustainability/top', { category, limit })
      .then(data => {
        setProducts(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err instanceof Error ? err : new Error('Unknown error'));
        setLoading(false);
      });
  }, [category, limit]);

  return {
    products,
    loading,
    error,
  };
}

// Hook for calculating sustainability score for a new product
interface MaterialComposition {
  material_type: string;
  percentage: number;
  certified_organic?: boolean;
  certified_recycled?: boolean;
  source_country?: string;
}

interface ManufacturingInfo {
  region?: string;
  country?: string;
  factory_certified?: boolean;
  factory_certifications?: string[];
  energy_source?: string;
  water_treatment?: boolean;
  chemical_management_system?: boolean;
}

interface ShippingInfo {
  origin_country?: string;
  origin_city?: string;
  shipping_method?: string;
  packaging_type?: string;
  packaging_recycled_content?: number;
}

export function useCalculateSustainability() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const calculate = async (
    productId: string,
    options: {
      brandId?: string;
      materials?: MaterialComposition[];
      manufacturing?: ManufacturingInfo;
      shipping?: ShippingInfo;
      category?: string;
      existingCertifications?: string[];
    }
  ): Promise<SustainabilityScore | null> => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.post<SustainabilityScore>(
        `/sustainability/products/${productId}/calculate`,
        {
          brand_id: options.brandId,
          materials: options.materials || [],
          manufacturing: options.manufacturing,
          shipping: options.shipping,
          category: options.category,
          existing_certifications: options.existingCertifications || [],
        }
      );
      setLoading(false);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setLoading(false);
      return null;
    }
  };

  return {
    calculate,
    loading,
    error,
  };
}
