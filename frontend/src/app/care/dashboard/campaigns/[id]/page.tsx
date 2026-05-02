/**
 * Campaign Detail Page
 * View and manage a specific donation campaign
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { ArrowLeft, Users, Gift, TrendingUp, Plus, Loader2 } from 'lucide-react';
import { careService } from '@/services/care.service';
import type { DonationCampaign, Beneficiary } from '@/types';
import type { Voucher } from '@/services/care.service';
import { formatCurrency, formatDate } from '@/lib/utils';

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params?.id as string;
  
  const [campaign, setCampaign] = useState<DonationCampaign | null>(null);
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const progressBarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (campaignId) {
      loadCampaignData();
    }
  }, [campaignId]);

  const loadCampaignData = async () => {
    setIsLoading(true);
    try {
      const [campaignData, beneficiariesData, vouchersData] = await Promise.all([
        careService.getCampaign(campaignId),
        careService.getBeneficiaries(campaignId),
        careService.getVouchers(campaignId),
      ]);
      setCampaign(campaignData);
      setBeneficiaries(beneficiariesData);
      setVouchers(vouchersData);
    } catch (error) {
      toast.error('Failed to load campaign data');
      console.error('Campaign load error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const progress = campaign ? (campaign.current_amount / campaign.target_amount) * 100 : 0;

  useEffect(() => {
    if (progressBarRef.current) {
      progressBarRef.current.style.width = `${Math.min(progress, 100)}%`;
    }
  }, [progress]);

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="container py-8 text-center">
        <p className="text-muted-foreground">Campaign not found</p>
        <Link href="/care/dashboard">
          <Button variant="outline" className="mt-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-700';
      case 'draft': return 'bg-gray-100 text-gray-700';
      case 'completed': return 'bg-blue-100 text-blue-700';
      case 'paused': return 'bg-yellow-100 text-yellow-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="container py-8">
      <Link 
        href="/care/dashboard" 
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Dashboard
      </Link>

      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">{campaign.title}</h1>
          <p className="text-muted-foreground mt-1">{campaign.description}</p>
          <Badge className={`mt-2 ${getStatusColor(campaign.status)}`}>
            {campaign.status}
          </Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadCampaignData}>
            Refresh
          </Button>
          {campaign.status === 'draft' && (
            <Button onClick={() => router.push(`/care/dashboard/campaigns/${campaignId}/edit`)}>
              Edit Campaign
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <TrendingUp className="h-5 w-5" />
              <span className="text-sm">Progress</span>
            </div>
            <div className="text-2xl font-semibold">
              {formatCurrency(campaign.current_amount, campaign.currency)}
            </div>
            <p className="text-sm text-muted-foreground">
              of {formatCurrency(campaign.target_amount, campaign.currency)} goal
            </p>
            <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
              <div 
                ref={progressBarRef}
                className="h-full bg-primary rounded-full transition-all"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Users className="h-5 w-5" />
              <span className="text-sm">Beneficiaries</span>
            </div>
            <div className="text-2xl font-semibold">{beneficiaries.length}</div>
            <p className="text-sm text-muted-foreground">
              {beneficiaries.filter(b => b.is_active).length} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Gift className="h-5 w-5" />
              <span className="text-sm">Vouchers</span>
            </div>
            <div className="text-2xl font-semibold">{vouchers.length}</div>
            <p className="text-sm text-muted-foreground">
              {vouchers.filter(v => v.status === 'active').length} active
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="beneficiaries">
            Beneficiaries ({beneficiaries.length})
          </TabsTrigger>
          <TabsTrigger value="vouchers">
            Vouchers ({vouchers.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Campaign Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p>{formatDate(campaign.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge className={getStatusColor(campaign.status)}>
                    {campaign.status}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Target Amount</p>
                  <p>{formatCurrency(campaign.target_amount, campaign.currency)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Current Amount</p>
                  <p>{formatCurrency(campaign.current_amount, campaign.currency)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="beneficiaries" className="mt-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Beneficiaries</h3>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Beneficiary
            </Button>
          </div>
          {beneficiaries.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <p className="text-muted-foreground">No beneficiaries yet</p>
                <Button className="mt-4" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add First Beneficiary
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {beneficiaries.map((beneficiary) => (
                <Card key={beneficiary.id}>
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold">{beneficiary.name}</p>
                        {beneficiary.email && (
                          <p className="text-sm text-muted-foreground">{beneficiary.email}</p>
                        )}
                      </div>
                      <Badge variant={beneficiary.is_active ? 'default' : 'secondary'}>
                        {beneficiary.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="vouchers" className="mt-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Vouchers</h3>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Create Voucher
            </Button>
          </div>
          {vouchers.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <p className="text-muted-foreground">No vouchers created yet</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {vouchers.map((voucher) => (
                <Card key={voucher.id}>
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-mono text-sm">{voucher.code || voucher.voucher_token}</p>
                        <p className="text-sm text-muted-foreground">
                          Balance: {formatCurrency(voucher.balance || voucher.budget_remaining, voucher.currency)}
                        </p>
                      </div>
                      <Badge variant={voucher.status === 'active' ? 'default' : 'secondary'}>
                        {voucher.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
