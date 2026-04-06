/**
 * CONFIT Admin - CARE Management ViewModel
 * =========================================
 * ViewModel for admin CARE dashboard functionality.
 */

import { useState, useCallback, useEffect } from 'react';
import { careService } from '../services/care.service';

interface AdminStats {
  total_campaigns: number;
  active_campaigns: number;
  paused_campaigns: number;
  completed_campaigns: number;
  draft_campaigns: number;
  total_donated: number;
  total_beneficiaries: number;
  avg_engagement: number;
  spending_by_category: Record<string, number>;
  monthly_trends: Record<string, number>;
  campaign_types: Record<string, number>;
}

interface AdminCampaign {
  id: string;
  campaign_name: string;
  donor_name: string;
  donor_id: string;
  campaign_type: string;
  status: string;
  total_beneficiaries: number;
  total_budget_allocated: number;
  total_budget_used: number;
  engagement_rate: number;
  completion_rate: number;
  created_at: string;
  end_date?: string;
}

interface ActivityLog {
  id: string;
  type: 'success' | 'warning' | 'info';
  description: string;
  campaign_name: string;
  timestamp: string;
}

interface UseAdminCareViewModel {
  // State
  stats: AdminStats | null;
  campaigns: AdminCampaign[];
  recentActivity: ActivityLog[];
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchStats: () => Promise<void>;
  fetchCampaigns: (filters?: { status?: string }) => Promise<void>;
  updateCampaignStatus: (id: string, status: string) => Promise<void>;
  exportReport: (type: string, format: string) => Promise<void>;
}

export const useAdminCareViewModel = (): UseAdminCareViewModel => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [campaigns, setCampaigns] = useState<AdminCampaign[]>([]);
  const [recentActivity, setRecentActivity] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch admin CARE stats
      const response = await fetch('/api/admin/care/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        // Use mock data for development
        setStats(getMockStats());
      }
    } catch (err: any) {
      console.error('Error fetching admin stats:', err);
      setStats(getMockStats());
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCampaigns = useCallback(async (filters?: { status?: string }) => {
    setLoading(true);
    setError(null);
    
    try {
      const query = filters?.status ? `?status=${filters.status}` : '';
      const response = await fetch(`/api/admin/care/campaigns${query}`);
      if (response.ok) {
        const data = await response.json();
        setCampaigns(data.campaigns || data);
      } else {
        // Use mock data for development
        setCampaigns(getMockCampaigns());
      }
      
      // Fetch activity log
      setRecentActivity(getMockActivity());
    } catch (err: any) {
      console.error('Error fetching campaigns:', err);
      setCampaigns(getMockCampaigns());
    } finally {
      setLoading(false);
    }
  }, []);

  const updateCampaignStatus = useCallback(async (id: string, status: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/admin/care/campaigns/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      
      if (response.ok) {
        // Update local state
        setCampaigns(prev =>
          prev.map(c => c.id === id ? { ...c, status } : c)
        );
      } else {
        throw new Error('Failed to update campaign status');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update campaign status');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const exportReport = useCallback(async (type: string, format: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/admin/care/reports/export?type=${type}&format=${format}`);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `care-report-${type}-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        // For development, show alert
        alert(`Report export: ${type} in ${format} format (would download in production)`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to export report');
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    stats,
    campaigns,
    recentActivity,
    loading,
    error,
    fetchStats,
    fetchCampaigns,
    updateCampaignStatus,
    exportReport,
  };
};

// Mock data for development
function getMockStats(): AdminStats {
  return {
    total_campaigns: 45,
    active_campaigns: 28,
    paused_campaigns: 5,
    completed_campaigns: 10,
    draft_campaigns: 2,
    total_donated: 1250000,
    total_beneficiaries: 850,
    avg_engagement: 72,
    spending_by_category: {
      Tops: 125000,
      Bottoms: 98000,
      Footwear: 145000,
      Accessories: 45000,
      Outerwear: 87000,
    },
    monthly_trends: {
      Jan: 85000,
      Feb: 92000,
      Mar: 110000,
      Apr: 125000,
      May: 98000,
      Jun: 115000,
    },
    campaign_types: {
      individual: 25,
      organization: 12,
      seasonal: 5,
      corporate: 3,
    },
  };
}

function getMockCampaigns(): AdminCampaign[] {
  return [
    {
      id: '1',
      campaign_name: 'Ramadan Clothing Drive 2024',
      donor_name: 'Ahmed Mohamed',
      donor_id: 'user-1',
      campaign_type: 'seasonal',
      status: 'active',
      total_beneficiaries: 50,
      total_budget_allocated: 75000,
      total_budget_used: 45000,
      engagement_rate: 85,
      completion_rate: 60,
      created_at: '2024-03-01T10:00:00Z',
      end_date: '2024-04-15T23:59:59Z',
    },
    {
      id: '2',
      campaign_name: 'Back to School Initiative',
      donor_name: 'Fatima Ali',
      donor_id: 'user-2',
      campaign_type: 'individual',
      status: 'active',
      total_beneficiaries: 25,
      total_budget_allocated: 37500,
      total_budget_used: 22000,
      engagement_rate: 72,
      completion_rate: 45,
      created_at: '2024-02-15T14:30:00Z',
    },
    {
      id: '3',
      campaign_name: 'Corporate CSR Program',
      donor_name: 'TechCorp Egypt',
      donor_id: 'brand-1',
      campaign_type: 'corporate',
      status: 'paused',
      total_beneficiaries: 100,
      total_budget_allocated: 150000,
      total_budget_used: 85000,
      engagement_rate: 68,
      completion_rate: 55,
      created_at: '2024-01-20T09:00:00Z',
    },
    {
      id: '4',
      campaign_name: 'Winter Warmth Campaign',
      donor_name: 'Sara Hassan',
      donor_id: 'user-3',
      campaign_type: 'seasonal',
      status: 'completed',
      total_beneficiaries: 30,
      total_budget_allocated: 45000,
      total_budget_used: 44500,
      engagement_rate: 95,
      completion_rate: 100,
      created_at: '2023-11-01T08:00:00Z',
      end_date: '2024-02-28T23:59:59Z',
    },
    {
      id: '5',
      campaign_name: 'Orphan Support Program',
      donor_name: 'Al-Nour Foundation',
      donor_id: 'org-1',
      campaign_type: 'organization',
      status: 'active',
      total_beneficiaries: 75,
      total_budget_allocated: 112500,
      total_budget_used: 67000,
      engagement_rate: 78,
      completion_rate: 58,
      created_at: '2024-02-01T12:00:00Z',
    },
  ];
}

function getMockActivity(): ActivityLog[] {
  return [
    {
      id: '1',
      type: 'success',
      description: 'Campaign "Ramadan Clothing Drive" reached 50% completion',
      campaign_name: 'Ramadan Clothing Drive 2024',
      timestamp: '2024-03-20T14:30:00Z',
    },
    {
      id: '2',
      type: 'info',
      description: 'New beneficiary added to "Back to School Initiative"',
      campaign_name: 'Back to School Initiative',
      timestamp: '2024-03-20T12:15:00Z',
    },
    {
      id: '3',
      type: 'warning',
      description: 'Campaign "Corporate CSR Program" was paused by admin',
      campaign_name: 'Corporate CSR Program',
      timestamp: '2024-03-19T16:45:00Z',
    },
    {
      id: '4',
      type: 'success',
      description: 'Order completed for beneficiary in "Winter Warmth Campaign"',
      campaign_name: 'Winter Warmth Campaign',
      timestamp: '2024-03-19T11:20:00Z',
    },
    {
      id: '5',
      type: 'info',
      description: 'New campaign "Orphan Support Program" was created',
      campaign_name: 'Orphan Support Program',
      timestamp: '2024-03-18T09:00:00Z',
    },
  ];
}

export default useAdminCareViewModel;
