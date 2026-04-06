/**
 * CONFIT CARE - Donor ViewModel
 * ==============================
 * ViewModel for donor dashboard functionality.
 */

import { useState, useCallback, useEffect } from 'react';
import { careService, Campaign, Beneficiary, DashboardStats, CareOrder } from '../services/care.service';

interface UseCareDonorViewModel {
  // State
  dashboard: DashboardStats | null;
  campaigns: Campaign[];
  recentOrders: CareOrder[];
  analytics: any;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchDashboard: () => Promise<void>;
  fetchCampaigns: (status?: string) => Promise<void>;
  createCampaign: (data: CampaignCreateData) => Promise<Campaign>;
  updateCampaign: (id: string, data: Partial<CampaignCreateData>) => Promise<Campaign>;
  deleteCampaign: (id: string) => Promise<void>;
  addBeneficiary: (campaignId: string, data: BeneficiaryCreateData) => Promise<Beneficiary>;
  removeBeneficiary: (campaignId: string, beneficiaryId: string) => Promise<void>;
  generateReport: (campaignId: string, type: string, format: string) => Promise<void>;
}

interface CampaignCreateData {
  campaign_name: string;
  campaign_type: string;
  description?: string;
  budget_per_person: number;
  currency: string;
  allowed_categories?: string[];
  excluded_brands?: string[];
  occasion_filter?: string;
  end_date?: string;
  voucher_expiry_days: number;
  invitation_message?: string;
  confirmation_message?: string;
  beneficiaries: BeneficiaryCreateData[];
  send_invitations: boolean;
}

interface BeneficiaryCreateData {
  name: string;
  email?: string;
  phone?: string;
  age_group?: string;
  size_preference?: string;
  style_preference?: string[];
  occasion_needs?: string[];
}

export const useCareDonorViewModel = (): UseCareDonorViewModel => {
  const [dashboard, setDashboard] = useState<DashboardStats | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [recentOrders, setRecentOrders] = useState<CareOrder[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await careService.getDonorDashboard();
      setDashboard(data);
      setRecentOrders(data.recent_orders || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard');
      console.error('Error fetching dashboard:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCampaigns = useCallback(async (status?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await careService.getCampaigns({ status });
      setCampaigns(response.campaigns);
    } catch (err: any) {
      setError(err.message || 'Failed to load campaigns');
      console.error('Error fetching campaigns:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createCampaign = useCallback(async (data: CampaignCreateData): Promise<Campaign> => {
    setLoading(true);
    setError(null);
    
    try {
      // First create the campaign
      const campaign = await careService.createCampaign({
        campaign_name: data.campaign_name,
        campaign_type: data.campaign_type,
        description: data.description,
        budget_per_person: data.budget_per_person,
        currency: data.currency,
        allowed_categories: data.allowed_categories,
        excluded_brands: data.excluded_brands,
        occasion_filter: data.occasion_filter,
        end_date: data.end_date,
        voucher_expiry_days: data.voucher_expiry_days,
        invitation_message: data.invitation_message,
        confirmation_message: data.confirmation_message,
      });
      
      // Then activate with beneficiaries
      if (data.beneficiaries && data.beneficiaries.length > 0) {
        await careService.activateCampaign(campaign.id, {
          beneficiaries: data.beneficiaries,
          send_invitations: data.send_invitations,
        });
      }
      
      // Refresh campaigns list
      await fetchCampaigns();
      
      return campaign;
    } catch (err: any) {
      setError(err.message || 'Failed to create campaign');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchCampaigns]);

  const updateCampaign = useCallback(async (id: string, data: Partial<CampaignCreateData>): Promise<Campaign> => {
    setLoading(true);
    setError(null);
    
    try {
      const campaign = await careService.updateCampaign(id, data);
      
      // Update local state
      setCampaigns(prev => 
        prev.map(c => c.id === id ? { ...c, ...campaign } : c)
      );
      
      return campaign;
    } catch (err: any) {
      setError(err.message || 'Failed to update campaign');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteCampaign = useCallback(async (id: string): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      await careService.deleteCampaign(id);
      
      // Remove from local state
      setCampaigns(prev => prev.filter(c => c.id !== id));
    } catch (err: any) {
      setError(err.message || 'Failed to delete campaign');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const addBeneficiary = useCallback(async (campaignId: string, data: BeneficiaryCreateData): Promise<Beneficiary> => {
    setLoading(true);
    setError(null);
    
    try {
      const beneficiary = await careService.addBeneficiary(campaignId, data);
      
      // Refresh dashboard to update counts
      await fetchDashboard();
      
      return beneficiary;
    } catch (err: any) {
      setError(err.message || 'Failed to add beneficiary');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchDashboard]);

  const removeBeneficiary = useCallback(async (campaignId: string, beneficiaryId: string): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      await careService.removeBeneficiary(campaignId, beneficiaryId);
      
      // Refresh dashboard
      await fetchDashboard();
    } catch (err: any) {
      setError(err.message || 'Failed to remove beneficiary');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchDashboard]);

  const generateReport = useCallback(async (campaignId: string, type: string, format: string): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      const report = await careService.generateReport(campaignId, {
        report_type: type,
        format: format,
      });
      
      // Download the report
      if (report.download_url) {
        window.open(report.download_url, '_blank');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate report');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    dashboard,
    campaigns,
    recentOrders,
    analytics,
    loading,
    error,
    fetchDashboard,
    fetchCampaigns,
    createCampaign,
    updateCampaign,
    deleteCampaign,
    addBeneficiary,
    removeBeneficiary,
    generateReport,
  };
};

export default useCareDonorViewModel;
