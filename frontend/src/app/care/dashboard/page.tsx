/**
 * CONFIT CARE Donor Dashboard
 * Manage campaigns, beneficiaries, and vouchers
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { careService, type DonorDashboard } from '@/services/care.service';
import type { DonationCampaign } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { toast } from 'sonner';
import { Plus, Users, Gift, TrendingUp, Settings } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export default function CareDashboardPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [dashboard, setDashboard] = useState<DonorDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.push('/login?redirect=/care/dashboard');
      return;
    }
    loadDashboard();
  }, [isAuthenticated, authLoading, router]);

  const loadDashboard = async () => {
    try {
      const data = await careService.getDonorDashboard();
      setDashboard(data);
    } catch (error) {
      toast.error('Failed to load dashboard');
    } finally {
      setDashboardLoading(false);
    }
  };

  if (authLoading || dashboardLoading || !isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--color-gold-400)] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="container">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-display font-semibold">CONFIT CARE</h1>
            <p className="text-[var(--color-gray-600)] mt-1">
              Manage your donation campaigns
            </p>
          </div>
          <Link href="/care/dashboard/campaigns/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Campaign
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            icon={<TrendingUp className="h-5 w-5" />}
            label="Total Donated"
            value={formatCurrency(dashboard?.total_donated || 0)}
          />
          <StatCard
            icon={<Gift className="h-5 w-5" />}
            label="Total Impact"
            value={formatCurrency(dashboard?.total_impact || 0)}
          />
          <StatCard
            icon={<Users className="h-5 w-5" />}
            label="Beneficiaries"
            value={dashboard?.active_beneficiaries || 0}
          />
          <StatCard
            icon={<Settings className="h-5 w-5" />}
            label="Campaigns"
            value={dashboard?.total_campaigns || 0}
          />
        </div>

        {/* Campaigns */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Your Campaigns</h2>
          {dashboard?.campaigns.length === 0 ? (
            <div className="text-center py-12 bg-[var(--color-beige-50)] rounded-xl">
              <p className="text-[var(--color-gray-600)] mb-4">
                You haven&apos;t created any campaigns yet
              </p>
              <Link href="/care/dashboard/campaigns/new">
                <Button>Create Your First Campaign</Button>
              </Link>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {dashboard?.campaigns.map((campaign) => (
                <CampaignCard key={campaign.id} campaign={campaign} />
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        {dashboard?.recent_activity && dashboard.recent_activity.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
            <div className="bg-white rounded-xl border border-[var(--color-beige-200)] overflow-hidden">
              <table className="w-full">
                <thead className="bg-[var(--color-beige-50)]">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium">Type</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Amount</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-beige-200)]">
                  {dashboard.recent_activity.map((activity) => (
                    <tr key={activity.id}>
                      <td className="px-4 py-3 text-sm capitalize">{activity.type}</td>
                      <td className="px-4 py-3 text-sm">
                        {formatCurrency(activity.amount, activity.currency)}
                      </td>
                      <td className="px-4 py-3 text-sm text-[var(--color-gray-600)]">
                        {formatDate(activity.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="bg-white rounded-xl border border-[var(--color-beige-200)] p-4">
      <div className="flex items-center gap-2 text-[var(--color-gray-500)] mb-2">
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}

function CampaignCard({ campaign }: { campaign: DonationCampaign }) {
  const progress = (campaign.current_amount / campaign.target_amount) * 100;

  return (
    <Link
      href={`/care/dashboard/campaigns/${campaign.id}`}
      className="block bg-white rounded-xl border border-[var(--color-beige-200)] p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold">{campaign.title}</h3>
        <span
          className={`text-xs px-2 py-1 rounded-full ${
            campaign.status === 'active'
              ? 'bg-green-100 text-green-700'
              : campaign.status === 'draft'
              ? 'bg-gray-100 text-gray-700'
              : 'bg-yellow-100 text-yellow-700'
          }`}
        >
          {campaign.status}
        </span>
      </div>
      <p className="text-sm text-[var(--color-gray-600)] mb-4 line-clamp-2">
        {campaign.description || 'No description'}
      </p>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>{formatCurrency(campaign.current_amount, campaign.currency)}</span>
          <span className="text-[var(--color-gray-500)]">
            of {formatCurrency(campaign.target_amount, campaign.currency)}
          </span>
        </div>
        <div className="h-2 bg-[var(--color-beige-100)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[var(--color-gold-400)] rounded-full"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>
    </Link>
  );
}
