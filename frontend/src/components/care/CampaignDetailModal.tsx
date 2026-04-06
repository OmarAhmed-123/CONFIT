/**
 * CONFIT CARE - Campaign Detail Modal
 * ====================================
 * Modal for viewing and managing campaign details.
 */

import React from 'react';
import { motion } from 'framer-motion';
import {
  X,
  Edit,
  Trash2,
  Download,
  Users,
  DollarSign,
  Calendar,
  Gift,
  BarChart3,
  Clock,
  CheckCircle,
  AlertCircle,
  Pause,
  Play,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { ImpactChart } from './ImpactChart';

interface Campaign {
  id: string;
  campaign_name: string;
  campaign_type: string;
  status: string;
  total_beneficiaries: number;
  total_budget_allocated: number;
  total_budget_used: number;
  engagement_rate: number;
  completion_rate: number;
  created_at: string;
  end_date?: string;
  description?: string;
  currency?: string;
  allowed_categories?: string[];
}

interface CampaignDetailModalProps {
  campaign: Campaign | null;
  onClose: () => void;
  onUpdate: (id: string, data: any) => Promise<any>;
  onDelete: (id: string) => Promise<void>;
}

export const CampaignDetailModal: React.FC<CampaignDetailModalProps> = ({
  campaign,
  onClose,
  onUpdate,
  onDelete,
}) => {
  if (!campaign) return null;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-EG', {
      style: 'currency',
      currency: 'EGP',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-4 h-4" />;
      case 'paused':
        return <Pause className="w-4 h-4" />;
      case 'completed':
        return <Gift className="w-4 h-4" />;
      case 'cancelled':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-500/10 text-green-500 border-green-500/20',
      draft: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
      paused: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
      completed: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
      cancelled: 'bg-red-500/10 text-red-500 border-red-500/20',
    };
    return colors[status] || colors.draft;
  };

  const utilizationRate = campaign.total_budget_allocated > 0
    ? (campaign.total_budget_used / campaign.total_budget_allocated) * 100
    : 0;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-purple-50 to-pink-50">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-xl font-bold text-gray-900">
                  {campaign.campaign_name}
                </h2>
                <Badge className={getStatusColor(campaign.status)}>
                  {getStatusIcon(campaign.status)}
                  <span className="ml-1 capitalize">{campaign.status}</span>
                </Badge>
              </div>
              <p className="text-gray-500 text-sm">{campaign.description}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card className="bg-gray-50">
              <CardContent className="p-4 text-center">
                <Users className="w-5 h-5 mx-auto mb-2 text-purple-600" />
                <p className="text-2xl font-bold text-gray-900">
                  {campaign.total_beneficiaries}
                </p>
                <p className="text-xs text-gray-500">Beneficiaries</p>
              </CardContent>
            </Card>

            <Card className="bg-gray-50">
              <CardContent className="p-4 text-center">
                <DollarSign className="w-5 h-5 mx-auto mb-2 text-green-600" />
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(campaign.total_budget_allocated)}
                </p>
                <p className="text-xs text-gray-500">Allocated</p>
              </CardContent>
            </Card>

            <Card className="bg-gray-50">
              <CardContent className="p-4 text-center">
                <BarChart3 className="w-5 h-5 mx-auto mb-2 text-blue-600" />
                <p className="text-2xl font-bold text-gray-900">
                  {formatCurrency(campaign.total_budget_used)}
                </p>
                <p className="text-xs text-gray-500">Used</p>
              </CardContent>
            </Card>

            <Card className="bg-gray-50">
              <CardContent className="p-4 text-center">
                <Gift className="w-5 h-5 mx-auto mb-2 text-pink-600" />
                <p className="text-2xl font-bold text-gray-900">
                  {campaign.engagement_rate}%
                </p>
                <p className="text-xs text-gray-500">Engagement</p>
              </CardContent>
            </Card>
          </div>

          {/* Progress */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Budget Utilization</span>
              <span className="text-sm text-gray-500">{Math.round(utilizationRate)}%</span>
            </div>
            <Progress value={utilizationRate} className="h-3" />
          </div>

          {/* Timeline */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Timeline</h3>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                <span>Started {new Date(campaign.created_at).toLocaleDateString()}</span>
              </div>
              {campaign.end_date && (
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  <span>Ends {new Date(campaign.end_date).toLocaleDateString()}</span>
                </div>
              )}
            </div>
          </div>

          {/* Categories */}
          {campaign.allowed_categories && campaign.allowed_categories.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Allowed Categories</h3>
              <div className="flex flex-wrap gap-2">
                {campaign.allowed_categories.map((cat) => (
                  <span
                    key={cat}
                    className="px-3 py-1 bg-purple-100 text-purple-600 rounded-full text-sm"
                  >
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Impact Chart */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">Spending Distribution</h3>
            <ImpactChart
              data={{
                Tops: campaign.total_budget_used * 0.3,
                Bottoms: campaign.total_budget_used * 0.25,
                Footwear: campaign.total_budget_used * 0.2,
                Accessories: campaign.total_budget_used * 0.15,
                Outerwear: campaign.total_budget_used * 0.1,
              }}
              type="bar"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {campaign.status === 'active' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onUpdate(campaign.id, { status: 'paused' })}
              >
                <Pause className="w-4 h-4 mr-1" />
                Pause
              </Button>
            )}
            {campaign.status === 'paused' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onUpdate(campaign.id, { status: 'active' })}
              >
                <Play className="w-4 h-4 mr-1" />
                Resume
              </Button>
            )}
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-1" />
              Report
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={() => {
                if (confirm('Are you sure you want to delete this campaign?')) {
                  onDelete(campaign.id);
                }
              }}
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Delete
            </Button>
            <Button
              className="bg-gradient-to-r from-purple-600 to-pink-600"
              onClick={onClose}
            >
              Close
            </Button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default CampaignDetailModal;
