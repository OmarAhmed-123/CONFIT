/**
 * CONFIT Brand - CSR Dashboard
 * =============================
 * Dashboard for brands to manage their corporate social responsibility campaigns.
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Heart,
  Users,
  DollarSign,
  TrendingUp,
  Gift,
  Calendar,
  Download,
  Plus,
  BarChart3,
  PieChart,
  FileText,
  Award,
  Target,
  Globe,
  Building2,
  ArrowRight,
  CheckCircle,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Progress } from '../../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { ImpactChart } from '../../components/care/ImpactChart';
import { useBrandCSRViewModel } from '../../viewmodels/useBrandCSRViewModel';

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

export const BrandCSRDashboard: React.FC = () => {
  const {
    brand,
    csrStats,
    campaigns,
    impactReport,
    loading,
    fetchBrandCSRData,
    createCSRCampaign,
    generateImpactReport,
    downloadCertificate,
  } = useBrandCSRViewModel();

  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchBrandCSRData();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-EG', {
      style: 'currency',
      currency: 'EGP',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  if (loading && !brand) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-blue-100 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">CSR Dashboard</h1>
                <p className="text-sm text-gray-500">{brand?.name || 'Your Brand'} · Corporate Impact</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={() => generateImpactReport()}>
                <FileText className="w-4 h-4 mr-2" />
                Impact Report
              </Button>
              <Button onClick={() => downloadCertificate()}>
                <Award className="w-4 h-4 mr-2" />
                CSR Certificate
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Impact Score Banner */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Card className="bg-gradient-to-r from-blue-600 to-purple-600 text-white border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Award className="w-6 h-6" />
                    <span className="text-white/80 text-sm">Your CSR Impact Score</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-5xl font-bold">{csrStats?.impact_score || 0}</span>
                    <span className="text-white/80">/ 100</span>
                  </div>
                  <p className="text-white/70 mt-2">
                    {csrStats?.impact_level || 'Bronze'} Level CSR Partner
                  </p>
                </div>
                <div className="text-right">
                  <div className="grid grid-cols-3 gap-6">
                    <div>
                      <p className="text-white/70 text-sm">People Helped</p>
                      <p className="text-2xl font-bold">{csrStats?.total_beneficiaries || 0}</p>
                    </div>
                    <div>
                      <p className="text-white/70 text-sm">Total Donated</p>
                      <p className="text-2xl font-bold">{formatCurrency(csrStats?.total_donated || 0)}</p>
                    </div>
                    <div>
                      <p className="text-white/70 text-sm">Campaigns</p>
                      <p className="text-2xl font-bold">{csrStats?.total_campaigns || 0}</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="bg-white/80 backdrop-blur-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-500">Active Campaigns</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {csrStats?.active_campaigns || 0}
                    </p>
                  </div>
                  <Gift className="w-8 h-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="bg-white/80 backdrop-blur-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-500">Budget Utilized</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {csrStats?.budget_utilization || 0}%
                    </p>
                  </div>
                  <Target className="w-8 h-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="bg-white/80 backdrop-blur-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-500">Engagement Rate</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {csrStats?.engagement_rate || 0}%
                    </p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="bg-white/80 backdrop-blur-sm">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-500">Completion Rate</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {csrStats?.completion_rate || 0}%
                    </p>
                  </div>
                  <CheckCircle className="w-8 h-8 text-teal-500" />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
            <TabsTrigger value="impact">Impact Report</TabsTrigger>
            <TabsTrigger value="badges">CSR Badges</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Active Campaigns */}
              <div className="lg:col-span-2">
                <Card className="bg-white/80 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Active CSR Campaigns</span>
                      <Button variant="outline" size="sm">
                        <Plus className="w-4 h-4 mr-1" />
                        New Campaign
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {campaigns.map((campaign: CSRCampaign) => (
                        <div
                          key={campaign.id}
                          className="p-4 rounded-xl border border-gray-200 hover:border-blue-200 hover:bg-blue-50/50 transition-all cursor-pointer"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <h4 className="font-medium text-gray-900">{campaign.campaign_name}</h4>
                              <p className="text-sm text-gray-500">
                                Started {new Date(campaign.start_date).toLocaleDateString()}
                              </p>
                            </div>
                            <Badge className={
                              campaign.status === 'active' 
                                ? 'bg-green-500/10 text-green-500'
                                : 'bg-gray-500/10 text-gray-400'
                            }>
                              {campaign.status}
                            </Badge>
                          </div>
                          
                          <div className="grid grid-cols-3 gap-4 text-sm mb-3">
                            <div>
                              <p className="text-gray-500">Beneficiaries</p>
                              <p className="font-medium">{campaign.total_beneficiaries}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Budget Used</p>
                              <p className="font-medium">{formatCurrency(campaign.total_budget_used)}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Impact Score</p>
                              <p className="font-medium text-blue-600">{campaign.impact_score}/100</p>
                            </div>
                          </div>
                          
                          <div>
                            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                              <span>Budget Utilization</span>
                              <span>
                                {Math.round((campaign.total_budget_used / campaign.total_budget_allocated) * 100)}%
                              </span>
                            </div>
                            <Progress
                              value={(campaign.total_budget_used / campaign.total_budget_allocated) * 100}
                              className="h-2"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Quick Stats */}
              <div className="space-y-6">
                <Card className="bg-white/80 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle>Impact Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ImpactChart
                      data={csrStats?.impact_distribution || {}}
                      type="pie"
                    />
                  </CardContent>
                </Card>

                <Card className="bg-white/80 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle>CSR Level Progress</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Current Level</span>
                        <Badge className="bg-blue-500/10 text-blue-500">
                          {csrStats?.impact_level || 'Bronze'}
                        </Badge>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                          <span>Progress to {csrStats?.next_level || 'Silver'}</span>
                          <span>{csrStats?.progress_to_next || 0}%</span>
                        </div>
                        <Progress value={csrStats?.progress_to_next || 0} className="h-2" />
                      </div>

                      <div className="p-3 bg-blue-50 rounded-lg">
                        <p className="text-xs text-blue-600">
                          {csrStats?.next_level_points || 100 - (csrStats?.impact_score || 0)} points needed for {csrStats?.next_level || 'Silver'} level
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="campaigns">
            <Card className="bg-white/80 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>All CSR Campaigns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {campaigns.map((campaign: CSRCampaign) => (
                    <div
                      key={campaign.id}
                      className="p-4 rounded-xl border border-gray-200 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                          <Gift className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900">{campaign.campaign_name}</h4>
                          <p className="text-sm text-gray-500">
                            {campaign.total_beneficiaries} beneficiaries · {formatCurrency(campaign.total_budget_allocated)} allocated
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <Badge className={
                          campaign.status === 'active' 
                            ? 'bg-green-500/10 text-green-500'
                            : campaign.status === 'completed'
                            ? 'bg-blue-500/10 text-blue-500'
                            : 'bg-gray-500/10 text-gray-400'
                        }>
                          {campaign.status}
                        </Badge>
                        <Button variant="outline" size="sm">
                          View Details
                          <ArrowRight className="w-4 h-4 ml-1" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="impact">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-white/80 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Monthly Impact
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ImpactChart
                    data={impactReport?.monthly_impact || {}}
                    type="bar"
                  />
                </CardContent>
              </Card>

              <Card className="bg-white/80 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="w-5 h-5" />
                    Category Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ImpactChart
                    data={impactReport?.category_distribution || {}}
                    type="pie"
                  />
                </CardContent>
              </Card>

              <Card className="bg-white/80 backdrop-blur-sm lg:col-span-2">
                <CardHeader>
                  <CardTitle>Impact Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div className="p-4 bg-blue-50 rounded-xl text-center">
                      <Users className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-gray-900">
                        {impactReport?.total_people_helped || 0}
                      </p>
                      <p className="text-sm text-gray-500">People Helped</p>
                    </div>
                    <div className="p-4 bg-green-50 rounded-xl text-center">
                      <Globe className="w-8 h-8 text-green-500 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-gray-900">
                        {impactReport?.regions_served || 0}
                      </p>
                      <p className="text-sm text-gray-500">Regions Served</p>
                    </div>
                    <div className="p-4 bg-purple-50 rounded-xl text-center">
                      <Heart className="w-8 h-8 text-purple-500 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-gray-900">
                        {impactReport?.items_donated || 0}
                      </p>
                      <p className="text-sm text-gray-500">Items Donated</p>
                    </div>
                    <div className="p-4 bg-teal-50 rounded-xl text-center">
                      <Award className="w-8 h-8 text-teal-500 mx-auto mb-2" />
                      <p className="text-2xl font-bold text-gray-900">
                        {impactReport?.hours_contributed || 0}
                      </p>
                      <p className="text-sm text-gray-500">Hours Contributed</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="badges">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { name: 'Bronze CSR Partner', description: 'Starting your CSR journey', earned: true },
                { name: 'Silver CSR Partner', description: '50+ people helped', earned: false, progress: 70 },
                { name: 'Gold CSR Partner', description: '100+ people helped', earned: false, progress: 35 },
                { name: 'Platinum CSR Partner', description: '500+ people helped', earned: false, progress: 10 },
                { name: 'Community Hero', description: '10+ active campaigns', earned: false, progress: 60 },
                { name: 'Impact Leader', description: '90%+ engagement rate', earned: false, progress: 45 },
              ].map((badge) => (
                <Card
                  key={badge.name}
                  className={`bg-white/80 backdrop-blur-sm ${
                    badge.earned ? 'border-2 border-blue-500' : 'opacity-75'
                  }`}
                >
                  <CardContent className="p-6 text-center">
                    <div className={`w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center ${
                      badge.earned
                        ? 'bg-gradient-to-br from-blue-500 to-purple-500'
                        : 'bg-gray-200'
                    }`}>
                      <Award className={`w-8 h-8 ${badge.earned ? 'text-white' : 'text-gray-400'}`} />
                    </div>
                    <h3 className="font-bold text-gray-900 mb-1">{badge.name}</h3>
                    <p className="text-sm text-gray-500 mb-4">{badge.description}</p>
                    
                    {badge.earned ? (
                      <Badge className="bg-green-500/10 text-green-500">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Earned
                      </Badge>
                    ) : (
                      <div>
                        <Progress value={badge.progress} className="h-2 mb-2" />
                        <p className="text-xs text-gray-400">{badge.progress}% complete</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default BrandCSRDashboard;
