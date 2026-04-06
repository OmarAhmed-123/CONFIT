/**
 * CONFIT Brand - CSR Dashboard ViewModel
 * =======================================
 * ViewModel for brand CSR dashboard functionality.
 */

import { useState, useCallback, useEffect } from 'react';

interface Brand {
  id: string;
  name: string;
  logo_url?: string;
  csr_level: string;
}

interface CSRStats {
  impact_score: number;
  impact_level: string;
  next_level: string;
  progress_to_next: number;
  next_level_points: number;
  total_campaigns: number;
  active_campaigns: number;
  total_beneficiaries: number;
  total_donated: number;
  budget_utilization: number;
  engagement_rate: number;
  completion_rate: number;
  impact_distribution: Record<string, number>;
}

interface CSRCampaign {
  id: string;
  campaign_name: string;
  status: string;
  total_beneficiaries: number;
  total_budget_allocated: number;
  total_budget_used: number;
  impact_score: number;
  start_date: string;
  end_date?: string;
}

interface ImpactReport {
  total_people_helped: number;
  regions_served: number;
  items_donated: number;
  hours_contributed: number;
  monthly_impact: Record<string, number>;
  category_distribution: Record<string, number>;
}

interface UseBrandCSRViewModel {
  // State
  brand: Brand | null;
  csrStats: CSRStats | null;
  campaigns: CSRCampaign[];
  impactReport: ImpactReport | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchBrandCSRData: () => Promise<void>;
  createCSRCampaign: (data: any) => Promise<CSRCampaign>;
  generateImpactReport: () => Promise<void>;
  downloadCertificate: () => Promise<void>;
}

export const useBrandCSRViewModel = (): UseBrandCSRViewModel => {
  const [brand, setBrand] = useState<Brand | null>(null);
  const [csrStats, setCSRStats] = useState<CSRStats | null>(null);
  const [campaigns, setCampaigns] = useState<CSRCampaign[]>([]);
  const [impactReport, setImpactReport] = useState<ImpactReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBrandCSRData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch brand CSR data
      const response = await fetch('/api/brand/csr/stats');
      if (response.ok) {
        const data = await response.json();
        setBrand(data.brand);
        setCSRStats(data.stats);
        setCampaigns(data.campaigns || []);
      } else {
        // Use mock data for development
        setBrand(getMockBrand());
        setCSRStats(getMockCSRStats());
        setCampaigns(getMockCampaigns());
      }
      
      // Fetch impact report
      setImpactReport(getMockImpactReport());
    } catch (err: any) {
      console.error('Error fetching brand CSR data:', err);
      setBrand(getMockBrand());
      setCSRStats(getMockCSRStats());
      setCampaigns(getMockCampaigns());
    } finally {
      setLoading(false);
    }
  }, []);

  const createCSRCampaign = useCallback(async (data: any): Promise<CSRCampaign> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/brand/csr/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      
      if (response.ok) {
        const campaign = await response.json();
        setCampaigns(prev => [...prev, campaign]);
        return campaign;
      } else {
        throw new Error('Failed to create CSR campaign');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create CSR campaign');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const generateImpactReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/brand/csr/reports/impact');
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `csr-impact-report-${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        // For development, show alert
        alert('CSR Impact Report would be downloaded as PDF in production');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate impact report');
    } finally {
      setLoading(false);
    }
  }, []);

  const downloadCertificate = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/brand/csr/certificate');
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `csr-certificate-${brand?.name || 'brand'}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        // For development, show alert
        alert('CSR Certificate would be downloaded as PDF in production');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to download certificate');
    } finally {
      setLoading(false);
    }
  }, [brand]);

  return {
    brand,
    csrStats,
    campaigns,
    impactReport,
    loading,
    error,
    fetchBrandCSRData,
    createCSRCampaign,
    generateImpactReport,
    downloadCertificate,
  };
};

// Mock data functions
function getMockBrand(): Brand {
  return {
    id: 'brand-1',
    name: 'TechCorp Egypt',
    logo_url: 'https://images.unsplash.com/photo-1560472354-b33ff0c674c5?w=100',
    csr_level: 'Bronze',
  };
}

function getMockCSRStats(): CSRStats {
  return {
    impact_score: 72,
    impact_level: 'Bronze',
    next_level: 'Silver',
    progress_to_next: 70,
    next_level_points: 28,
    total_campaigns: 5,
    active_campaigns: 3,
    total_beneficiaries: 150,
    total_donated: 225000,
    budget_utilization: 68,
    engagement_rate: 82,
    completion_rate: 75,
    impact_distribution: {
      Clothing: 45,
      Footwear: 25,
      Accessories: 15,
      Outerwear: 15,
    },
  };
}

function getMockCampaigns(): CSRCampaign[] {
  return [
    {
      id: '1',
      campaign_name: 'Q1 2024 CSR Initiative',
      status: 'active',
      total_beneficiaries: 50,
      total_budget_allocated: 75000,
      total_budget_used: 45000,
      impact_score: 78,
      start_date: '2024-01-01T00:00:00Z',
    },
    {
      id: '2',
      campaign_name: 'Employee Matching Program',
      status: 'active',
      total_beneficiaries: 75,
      total_budget_allocated: 100000,
      total_budget_used: 72000,
      impact_score: 85,
      start_date: '2024-02-15T00:00:00Z',
    },
    {
      id: '3',
      campaign_name: 'Winter Clothing Drive',
      status: 'completed',
      total_beneficiaries: 25,
      total_budget_allocated: 50000,
      total_budget_used: 48500,
      impact_score: 92,
      start_date: '2023-11-01T00:00:00Z',
      end_date: '2024-01-31T23:59:59Z',
    },
  ];
}

function getMockImpactReport(): ImpactReport {
  return {
    total_people_helped: 150,
    regions_served: 8,
    items_donated: 450,
    hours_contributed: 120,
    monthly_impact: {
      Jan: 25,
      Feb: 35,
      Mar: 45,
      Apr: 30,
      May: 15,
    },
    category_distribution: {
      Tops: 150,
      Bottoms: 100,
      Footwear: 120,
      Accessories: 50,
      Outerwear: 30,
    },
  };
}

export default useBrandCSRViewModel;
