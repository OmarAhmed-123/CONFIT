/**
 * CONFIT CARE - Create Campaign Wizard
 * ======================================
 * Multi-step wizard for creating a new donation campaign.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Heart,
  ArrowRight,
  ArrowLeft,
  Users,
  DollarSign,
  Calendar,
  Gift,
  Upload,
  CheckCircle,
  AlertCircle,
  Plus,
  X,
  FileText,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Progress } from '../ui/progress';

interface CreateCampaignWizardProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CampaignFormData) => Promise<any>;
}

interface CampaignFormData {
  campaign_name: string;
  campaign_type: string;
  description: string;
  budget_per_person: number;
  currency: string;
  allowed_categories: string[];
  excluded_brands: string[];
  end_date: string;
  voucher_expiry_days: number;
  invitation_message: string;
  confirmation_message: string;
  beneficiaries: BeneficiaryData[];
  send_invitations: boolean;
}

interface BeneficiaryData {
  name: string;
  email: string;
  phone: string;
  age_group: string;
  size_preference: string;
}

const STEPS = [
  { id: 1, title: 'Campaign Details', icon: Gift },
  { id: 2, title: 'Budget & Restrictions', icon: DollarSign },
  { id: 3, title: 'Beneficiaries', icon: Users },
  { id: 4, title: 'Review & Launch', icon: CheckCircle },
];

const CATEGORIES = [
  'Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Footwear', 'Accessories', 'Bags'
];

const AGE_GROUPS = ['18-25', '26-35', '36-45', '46-55', '55+'];

export const CreateCampaignWizard: React.FC<CreateCampaignWizardProps> = ({
  open,
  onClose,
  onSubmit,
}) => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<Partial<CampaignFormData>>({
    campaign_name: '',
    campaign_type: 'individual',
    description: '',
    budget_per_person: 1500,
    currency: 'EGP',
    allowed_categories: [],
    excluded_brands: [],
    end_date: '',
    voucher_expiry_days: 30,
    invitation_message: '',
    confirmation_message: '',
    beneficiaries: [],
    send_invitations: true,
  });

  const updateForm = (updates: Partial<CampaignFormData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
  };

  const addBeneficiary = () => {
    const newBeneficiary: BeneficiaryData = {
      name: '',
      email: '',
      phone: '',
      age_group: '',
      size_preference: '',
    };
    updateForm({
      beneficiaries: [...(formData.beneficiaries || []), newBeneficiary],
    });
  };

  const removeBeneficiary = (index: number) => {
    updateForm({
      beneficiaries: formData.beneficiaries?.filter((_, i) => i !== index),
    });
  };

  const updateBeneficiary = (index: number, updates: Partial<BeneficiaryData>) => {
    const updated = formData.beneficiaries?.map((b, i) =>
      i === index ? { ...b, ...updates } : b
    );
    updateForm({ beneficiaries: updated });
  };

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await onSubmit(formData as CampaignFormData);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create campaign');
    } finally {
      setLoading(false);
    }
  };

  const progress = (step / STEPS.length) * 100;

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Heart className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Create Campaign</h2>
                <p className="text-sm text-gray-500">Step {step} of {STEPS.length}</p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>
          
          {/* Progress */}
          <Progress value={progress} className="h-2" />
          
          {/* Step Indicators */}
          <div className="flex justify-between mt-4">
            {STEPS.map((s, index) => (
              <div
                key={s.id}
                className={`flex items-center gap-2 ${
                  index + 1 <= step ? 'text-purple-600' : 'text-gray-400'
                }`}
              >
                <s.icon className="w-4 h-4" />
                <span className="text-sm hidden sm:block">{s.title}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          <AnimatePresence mode="wait">
            {/* Step 1: Campaign Details */}
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <div>
                  <Label htmlFor="name">Campaign Name *</Label>
                  <Input
                    id="name"
                    placeholder="e.g., Ramadan Clothing Drive"
                    value={formData.campaign_name}
                    onChange={(e) => updateForm({ campaign_name: e.target.value })}
                  />
                </div>

                <div>
                  <Label htmlFor="type">Campaign Type</Label>
                  <select
                    id="type"
                    value={formData.campaign_type}
                    onChange={(e) => updateForm({ campaign_type: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-gray-200"
                    aria-label="Select campaign type"
                    title="Campaign type"
                  >
                    <option value="individual">Individual</option>
                    <option value="organization">Organization</option>
                    <option value="seasonal">Seasonal</option>
                    <option value="corporate">Corporate</option>
                    <option value="emergency">Emergency</option>
                  </select>
                </div>

                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Describe the purpose of your campaign..."
                    value={formData.description}
                    onChange={(e) => updateForm({ description: e.target.value })}
                    rows={3}
                  />
                </div>

                <div>
                  <Label htmlFor="end_date">End Date (Optional)</Label>
                  <Input
                    id="end_date"
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => updateForm({ end_date: e.target.value })}
                  />
                </div>
              </motion.div>
            )}

            {/* Step 2: Budget & Restrictions */}
            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <div>
                  <Label htmlFor="budget">Budget Per Person (EGP) *</Label>
                  <Input
                    id="budget"
                    type="number"
                    min={500}
                    max={5000}
                    value={formData.budget_per_person}
                    onChange={(e) => updateForm({ budget_per_person: parseInt(e.target.value) })}
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Min: 500 EGP · Max: 5,000 EGP
                  </p>
                </div>

                <div>
                  <Label htmlFor="expiry">Voucher Expiry (Days)</Label>
                  <Input
                    id="expiry"
                    type="number"
                    min={1}
                    max={365}
                    value={formData.voucher_expiry_days}
                    onChange={(e) => updateForm({ voucher_expiry_days: parseInt(e.target.value) })}
                  />
                </div>

                <div>
                  <Label>Allowed Categories (Optional)</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {CATEGORIES.map((cat) => (
                      <button
                        key={cat}
                        onClick={() => {
                          const current = formData.allowed_categories || [];
                          const updated = current.includes(cat)
                            ? current.filter((c) => c !== cat)
                            : [...current, cat];
                          updateForm({ allowed_categories: updated });
                        }}
                        className={`px-3 py-1 rounded-full text-sm transition-colors ${
                          formData.allowed_categories?.includes(cat)
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Leave empty to allow all categories
                  </p>
                </div>

                <div>
                  <Label htmlFor="invitation">Custom Invitation Message</Label>
                  <Textarea
                    id="invitation"
                    placeholder="Add a personal message for beneficiaries..."
                    value={formData.invitation_message}
                    onChange={(e) => updateForm({ invitation_message: e.target.value })}
                    rows={2}
                  />
                </div>
              </motion.div>
            )}

            {/* Step 3: Beneficiaries */}
            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">Beneficiaries</h3>
                    <p className="text-sm text-gray-500">
                      Add people who will receive shopping vouchers
                    </p>
                  </div>
                  <Button onClick={addBeneficiary} variant="outline" size="sm">
                    <Plus className="w-4 h-4 mr-1" />
                    Add
                  </Button>
                </div>

                {formData.beneficiaries?.length === 0 && (
                  <div className="text-center py-8 bg-gray-50 rounded-xl">
                    <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">No beneficiaries added yet</p>
                    <Button onClick={addBeneficiary} className="mt-3">
                      Add First Beneficiary
                    </Button>
                  </div>
                )}

                <div className="space-y-3">
                  {formData.beneficiaries?.map((beneficiary, index) => (
                    <Card key={index} className="bg-gray-50">
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-sm font-medium text-gray-500">
                            Beneficiary {index + 1}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeBeneficiary(index)}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <Label className="text-xs">Name *</Label>
                            <Input
                              value={beneficiary.name}
                              onChange={(e) =>
                                updateBeneficiary(index, { name: e.target.value })
                              }
                              placeholder="Full name"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Phone</Label>
                            <Input
                              value={beneficiary.phone}
                              onChange={(e) =>
                                updateBeneficiary(index, { phone: e.target.value })
                              }
                              placeholder="+20..."
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Email</Label>
                            <Input
                              type="email"
                              value={beneficiary.email}
                              onChange={(e) =>
                                updateBeneficiary(index, { email: e.target.value })
                              }
                              placeholder="email@example.com"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">Age Group</Label>
                            <select
                              value={beneficiary.age_group}
                              onChange={(e) =>
                                updateBeneficiary(index, { age_group: e.target.value })
                              }
                              className="w-full px-2 py-1.5 rounded border border-gray-200 text-sm"
                              aria-label="Select age group"
                              title="Age group"
                            >
                              <option value="">Select</option>
                              {AGE_GROUPS.map((age) => (
                                <option key={age} value={age}>{age}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {formData.beneficiaries && formData.beneficiaries.length > 0 && (
                  <div className="flex items-center gap-2 p-3 bg-purple-50 rounded-lg">
                    <input
                      type="checkbox"
                      id="send-invitations"
                      checked={formData.send_invitations}
                      onChange={(e) => updateForm({ send_invitations: e.target.checked })}
                      className="rounded"
                      aria-label="Send invitations immediately"
                      title="Send invitations immediately after creating campaign"
                    />
                    <Label htmlFor="send-invitations" className="text-sm">
                      Send invitations immediately after creating campaign
                    </Label>
                  </div>
                )}
              </motion.div>
            )}

            {/* Step 4: Review */}
            {step === 4 && (
              <motion.div
                key="step4"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <Card className="bg-gradient-to-r from-purple-50 to-pink-50">
                  <CardContent className="p-4">
                    <h3 className="font-bold text-lg mb-2">{formData.campaign_name}</h3>
                    <p className="text-gray-600 text-sm">{formData.description}</p>
                  </CardContent>
                </Card>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-50 rounded-xl">
                    <p className="text-sm text-gray-500">Budget Per Person</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {formData.budget_per_person?.toLocaleString()} EGP
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-xl">
                    <p className="text-sm text-gray-500">Beneficiaries</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {formData.beneficiaries?.length || 0}
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-xl">
                    <p className="text-sm text-gray-500">Total Budget</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {((formData.budget_per_person || 0) * (formData.beneficiaries?.length || 0)).toLocaleString()} EGP
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-xl">
                    <p className="text-sm text-gray-500">Voucher Expiry</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {formData.voucher_expiry_days} days
                    </p>
                  </div>
                </div>

                {formData.allowed_categories && formData.allowed_categories.length > 0 && (
                  <div>
                    <p className="text-sm text-gray-500 mb-2">Allowed Categories</p>
                    <div className="flex flex-wrap gap-2">
                      {formData.allowed_categories.map((cat) => (
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

                {error && (
                  <div className="p-3 bg-red-50 rounded-lg flex items-center gap-2 text-red-600">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-100 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={step === 1}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>

          {step < 4 ? (
            <Button
              onClick={handleNext}
              className="bg-gradient-to-r from-purple-600 to-pink-600"
            >
              Next
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              className="bg-gradient-to-r from-purple-600 to-pink-600"
              disabled={loading || !formData.beneficiaries?.length}
            >
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Launch Campaign
                </>
              )}
            </Button>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default CreateCampaignWizard;
