/**
 * CONFIT CARE - Beneficiary Manager Component
 * ===========================================
 * Component for managing beneficiaries within a campaign.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Plus,
  Search,
  Edit,
  Trash2,
  Phone,
  Mail,
  Gift,
  CheckCircle,
  Clock,
  AlertCircle,
  X,
  Upload,
  Download,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';

interface Beneficiary {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  budget_allocated: number;
  budget_used: number;
  budget_remaining: number;
  is_active: boolean;
  invitation_sent_at?: string;
  first_access_at?: string;
  completed_at?: string;
}

interface BeneficiaryManagerProps {
  campaignId: string;
  beneficiaries: Beneficiary[];
  onAdd: (data: BeneficiaryFormData) => Promise<any>;
  onUpdate: (id: string, data: Partial<BeneficiaryFormData>) => Promise<any>;
  onRemove: (id: string) => Promise<void>;
  onBulkImport: (beneficiaries: BeneficiaryFormData[]) => Promise<any>;
}

interface BeneficiaryFormData {
  name: string;
  email: string;
  phone: string;
  age_group?: string;
  size_preference?: string;
}

export const BeneficiaryManager: React.FC<BeneficiaryManagerProps> = ({
  campaignId,
  beneficiaries,
  onAdd,
  onUpdate,
  onRemove,
  onBulkImport,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  const [formData, setFormData] = useState<BeneficiaryFormData>({
    name: '',
    email: '',
    phone: '',
  });

  const filteredBeneficiaries = beneficiaries.filter((b) =>
    b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.phone?.includes(searchQuery)
  );

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-EG', {
      style: 'currency',
      currency: 'EGP',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getStatusBadge = (beneficiary: Beneficiary) => {
    if (beneficiary.completed_at) {
      return <Badge className="bg-green-500/10 text-green-500">Completed</Badge>;
    }
    if (beneficiary.first_access_at) {
      return <Badge className="bg-blue-500/10 text-blue-500">Shopping</Badge>;
    }
    if (beneficiary.invitation_sent_at) {
      return <Badge className="bg-yellow-500/10 text-yellow-500">Invited</Badge>;
    }
    return <Badge className="bg-gray-500/10 text-gray-400">Pending</Badge>;
  };

  const handleSubmit = async () => {
    if (!formData.name) return;
    
    setLoading(true);
    try {
      if (editingId) {
        await onUpdate(editingId, formData);
      } else {
        await onAdd(formData);
      }
      setShowAddModal(false);
      setEditingId(null);
      setFormData({ name: '', email: '', phone: '' });
    } catch (err) {
      console.error('Error saving beneficiary:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (beneficiary: Beneficiary) => {
    setEditingId(beneficiary.id);
    setFormData({
      name: beneficiary.name,
      email: beneficiary.email || '',
      phone: beneficiary.phone || '',
    });
    setShowAddModal(true);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search beneficiaries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 w-64"
            />
          </div>
          <span className="text-sm text-gray-500">
            {beneficiaries.length} total
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Upload className="w-4 h-4 mr-1" />
            Import CSV
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="w-4 h-4 mr-1" />
            Add Beneficiary
          </Button>
        </div>
      </div>

      {/* Beneficiaries List */}
      <div className="space-y-3">
        <AnimatePresence>
          {filteredBeneficiaries.map((beneficiary) => (
            <motion.div
              key={beneficiary.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <Card className="hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-medium">
                        {beneficiary.name.charAt(0).toUpperCase()}
                      </div>
                      
                      <div>
                        <h4 className="font-medium text-gray-900">{beneficiary.name}</h4>
                        <div className="flex items-center gap-3 text-sm text-gray-500">
                          {beneficiary.email && (
                            <span className="flex items-center gap-1">
                              <Mail className="w-3 h-3" />
                              {beneficiary.email}
                            </span>
                          )}
                          {beneficiary.phone && (
                            <span className="flex items-center gap-1">
                              <Phone className="w-3 h-3" />
                              {beneficiary.phone}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      {/* Budget Progress */}
                      <div className="w-40">
                        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                          <span>Budget</span>
                          <span>
                            {formatCurrency(beneficiary.budget_remaining)} left
                          </span>
                        </div>
                        <Progress
                          value={
                            (beneficiary.budget_used / beneficiary.budget_allocated) * 100
                          }
                          className="h-2"
                        />
                      </div>

                      {/* Status */}
                      {getStatusBadge(beneficiary)}

                      {/* Actions */}
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(beneficiary)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => {
                            if (confirm('Remove this beneficiary?')) {
                              onRemove(beneficiary.id);
                            }
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>

        {filteredBeneficiaries.length === 0 && (
          <div className="text-center py-12 bg-gray-50 rounded-xl">
            <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">
              {searchQuery ? 'No beneficiaries found' : 'No beneficiaries added yet'}
            </p>
            {!searchQuery && (
              <Button onClick={() => setShowAddModal(true)} className="mt-3">
                Add First Beneficiary
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Add/Edit Modal */}
      <AnimatePresence>
        {showAddModal && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-xl shadow-xl w-full max-w-md"
            >
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold">
                    {editingId ? 'Edit Beneficiary' : 'Add Beneficiary'}
                  </h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setShowAddModal(false);
                      setEditingId(null);
                      setFormData({ name: '', email: '', phone: '' });
                    }}
                  >
                    <X className="w-5 h-5" />
                  </Button>
                </div>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Name *
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="Full name"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Email
                  </label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) =>
                      setFormData({ ...formData, email: e.target.value })
                    }
                    placeholder="email@example.com"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Phone
                  </label>
                  <Input
                    value={formData.phone}
                    onChange={(e) =>
                      setFormData({ ...formData, phone: e.target.value })
                    }
                    placeholder="+20..."
                  />
                </div>
              </div>

              <div className="p-6 border-t border-gray-100 flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowAddModal(false);
                    setEditingId(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={!formData.name || loading}
                  className="bg-gradient-to-r from-purple-600 to-pink-600"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  ) : editingId ? (
                    'Save Changes'
                  ) : (
                    'Add Beneficiary'
                  )}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default BeneficiaryManager;
