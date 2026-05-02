/**
 * Create New Campaign Page
 * CONFIT CARE - Donation Campaign Creation
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { toast } from 'sonner';
import { ArrowLeft, Plus, Loader2 } from 'lucide-react';
import { careService } from '@/services/care.service';

export default function NewCampaignPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    target_amount: '',
    currency: 'USD',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.title.trim()) {
      toast.error('Campaign title is required');
      return;
    }
    
    const targetAmount = parseFloat(formData.target_amount);
    if (isNaN(targetAmount) || targetAmount <= 0) {
      toast.error('Please enter a valid target amount');
      return;
    }

    setIsSubmitting(true);
    
    try {
      const campaign = await careService.createCampaign({
        title: formData.title,
        description: formData.description,
        target_amount: targetAmount,
        currency: formData.currency,
      });
      
      toast.success('Campaign created successfully!');
      router.push(`/care/dashboard/campaigns/${campaign.id}`);
    } catch (error) {
      toast.error('Failed to create campaign. Please try again.');
      console.error('Campaign creation error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container py-8 max-w-2xl">
      <Link 
        href="/care/dashboard" 
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Dashboard
      </Link>

      <Card>
        <CardHeader>
          <CardTitle>Create New Campaign</CardTitle>
          <CardDescription>
            Set up a new donation campaign to help those in need shop for clothing.
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="title">Campaign Title *</Label>
              <Input
                id="title"
                placeholder="e.g., Winter Clothing Drive 2024"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe your campaign and its goals..."
                rows={4}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                disabled={isSubmitting}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="target_amount">Target Amount *</Label>
                <Input
                  id="target_amount"
                  type="number"
                  min="1"
                  step="0.01"
                  placeholder="1000"
                  value={formData.target_amount}
                  onChange={(e) => setFormData({ ...formData, target_amount: e.target.value })}
                  disabled={isSubmitting}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="currency">Currency</Label>
                <select
                  id="currency"
                  aria-label="Select currency"
                  title="Select currency"
                  className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  disabled={isSubmitting}
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="EGP">EGP (E£)</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/care/dashboard')}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="mr-2 h-4 w-4" />
                    Create Campaign
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
