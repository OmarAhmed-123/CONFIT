/**
 * GDPR Data Compliance Page
 * /profile/data — Export my data, delete my account
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useMutation, useQuery } from '@tanstack/react-query';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Download,
  Trash2,
  Shield,
  FileJson,
  FileSpreadsheet,
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle,
  Database,
  Shirt,
  Camera,
  Package,
  Bell,
  Heart,
} from 'lucide-react';
import {
  getDataSummary,
  requestDataExport,
  getExportStatus,
  requestAccountDeletion,
  getRetentionPolicies,
  getDpoContact,
} from '@/services/dataCompliance.service';

// ═══════════════════════════════════════════════════════════════════
// Helper Components
// ═══════════════════════════════════════════════════════════════════

const DataCategoryCard = ({
  icon,
  label,
  count,
  retention,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  retention: string;
}) => (
  <Card className="border-border/60">
    <CardContent className="p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">{icon}</div>
          <div>
            <p className="font-medium">{label}</p>
            <p className="text-xs text-muted-foreground">{retention}</p>
          </div>
        </div>
        <Badge variant="secondary">{count} items</Badge>
      </div>
    </CardContent>
  </Card>
);

// ═══════════════════════════════════════════════════════════════════
// Main Page Component
// ═══════════════════════════════════════════════════════════════════

export default function DataCompliancePage() {
  const [exportFormat, setExportFormat] = useState<'json' | 'csv' | 'pdf'>('json');
  const [includePhotos, setIncludePhotos] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [keepOrders, setKeepOrders] = useState(true);
  const [deleteReason, setDeleteReason] = useState('');

  // Data queries
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['data-summary'],
    queryFn: getDataSummary,
  });

  const { data: policies } = useQuery({
    queryKey: ['retention-policies'],
    queryFn: getRetentionPolicies,
  });

  const { data: dpo } = useQuery({
    queryKey: ['dpo-contact'],
    queryFn: getDpoContact,
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: requestDataExport,
    onSuccess: (data) => {
      toast.success(`Export requested! ID: ${data.export_id}`);
      if (data.status === 'ready' && data.download_url) {
        window.open(data.download_url, '_blank');
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to request export');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: requestAccountDeletion,
    onSuccess: (data) => {
      toast.success(
        `Account deletion scheduled. Your data will be deleted on ${new Date(data.deletion_date).toLocaleDateString()}.`
      );
      setShowDeleteDialog(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to request account deletion');
    },
  });

  const handleExport = () => {
    exportMutation.mutate({
      format: exportFormat,
      include_tryon_photos: includePhotos,
    });
  };

  const handleDeleteAccount = () => {
    if (!deleteConfirm) {
      toast.error('Please confirm account deletion');
      return;
    }
    deleteMutation.mutate({
      reason: deleteReason,
      confirm_deletion: true,
      keep_order_history: keepOrders,
    });
  };

  return (
    <MainLayout>
      <div className="container py-8 max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Link
            href="/profile"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Profile
          </Link>
          <div className="flex items-center gap-3 mb-2">
            <Shield className="h-6 w-6 text-primary" />
            <h1 className="text-3xl font-bold">My Data & Privacy</h1>
          </div>
          <p className="text-muted-foreground">
            Manage your personal data, export your information, or delete your account.
            Compliant with Egypt Law 151/2020.
          </p>
        </motion.div>

        {/* Data Summary */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Data Stored About You
              </CardTitle>
              <CardDescription>
                Overview of all data categories stored in our system
              </CardDescription>
            </CardHeader>
            <CardContent>
              {summaryLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="h-20 bg-muted rounded-lg" />
                  ))}
                </div>
              ) : summary ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <DataCategoryCard
                    icon={<UserIcon />}
                    label="Profile"
                    count={1}
                    retention={summary.data_retention_policy?.general || 'Account lifetime + 30 days'}
                  />
                  <DataCategoryCard
                    icon={<Package className="h-4 w-4" />}
                    label="Orders"
                    count={summary.orders_count}
                    retention={summary.data_retention_policy?.orders || '7 years (tax compliance)'}
                  />
                  <DataCategoryCard
                    icon={<Camera className="h-4 w-4" />}
                    label="Try-On Sessions"
                    count={summary.tryon_sessions_count}
                    retention={summary.data_retention_policy?.ai_photos || '7 days (auto-delete)'}
                  />
                  <DataCategoryCard
                    icon={<Shirt className="h-4 w-4" />}
                    label="Wardrobe Items"
                    count={summary.wardrobe_items_count}
                    retention="Account lifetime + 30 days"
                  />
                  <DataCategoryCard
                    icon={<Bell className="h-4 w-4" />}
                    label="Notifications"
                    count={summary.notifications_count}
                    retention="1 year"
                  />
                  <DataCategoryCard
                    icon={<Heart className="h-4 w-4" />}
                    label="Donations"
                    count={summary.donation_history_count}
                    retention="5 years"
                  />
                </div>
              ) : (
                <p className="text-muted-foreground">Failed to load data summary</p>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Export Data */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-8"
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-5 w-5" />
                Export My Data
              </CardTitle>
              <CardDescription>
                Download a copy of all your personal data (Article 8, Law 151/2020)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(['json', 'csv', 'pdf'] as const).map((format) => (
                  <button
                    key={format}
                    onClick={() => setExportFormat(format)}
                    className={`flex flex-col items-center gap-3 p-6 rounded-lg border-2 transition-all ${
                      exportFormat === format
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    {format === 'json' && <FileJson className="h-8 w-8 text-blue-500" />}
                    {format === 'csv' && <FileSpreadsheet className="h-8 w-8 text-green-500" />}
                    {format === 'pdf' && <FileText className="h-8 w-8 text-red-500" />}
                    <span className="font-medium uppercase">{format}</span>
                  </button>
                ))}
              </div>

              <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/50">
                <Checkbox
                  id="include-photos"
                  checked={includePhotos}
                  onCheckedChange={(checked) => setIncludePhotos(checked as boolean)}
                />
                <div>
                  <label htmlFor="include-photos" className="font-medium cursor-pointer">
                    Include Try-On Photos
                  </label>
                  <p className="text-sm text-muted-foreground">
                    Adds ~50MB to the export. Photos are automatically deleted after 7 days.
                  </p>
                </div>
              </div>

              <Button
                onClick={handleExport}
                disabled={exportMutation.isPending}
                className="w-full md:w-auto"
                size="lg"
              >
                {exportMutation.isPending ? (
                  <>
                    <Clock className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Request Data Export
                  </>
                )}
              </Button>

              {exportMutation.isSuccess && (
                <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 p-3 rounded-lg">
                  <CheckCircle className="h-4 w-4" />
                  Export request submitted! You will receive an email when it is ready.
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Retention Policies */}
        {policies && policies.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-8"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Data Retention Policies
                </CardTitle>
                <CardDescription>
                  How long we keep each type of data and why
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {policies.map((policy) => (
                    <div
                      key={policy.data_type}
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/30"
                    >
                      <div>
                        <p className="font-medium capitalize">
                          {policy.data_type.replace(/_/g, ' ')}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {policy.legal_basis}
                        </p>
                      </div>
                      <div className="text-right">
                        <Badge variant={policy.auto_delete ? 'default' : 'secondary'}>
                          {policy.retention_period}
                        </Badge>
                        {policy.auto_delete && (
                          <p className="text-xs text-muted-foreground mt-1">
                            Auto-delete enabled
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Delete Account */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mb-8"
        >
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <Trash2 className="h-5 w-5" />
                Delete My Account
              </CardTitle>
              <CardDescription>
                Request complete deletion of your personal data (Article 10, Law 151/2020)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-destructive">This action cannot be undone</p>
                    <ul className="text-sm text-muted-foreground mt-2 space-y-1 list-disc list-inside">
                      <li>Your profile and preferences will be deleted</li>
                      <li>Your wardrobe items and try-on photos will be removed</li>
                      <li>Your style DNA and AI models will be purged</li>
                      <li>Order history is retained for 7 years per Egyptian Tax Law</li>
                      <li>You have a 30-day grace period to cancel this request</li>
                    </ul>
                  </div>
                </div>
              </div>
              <Button
                variant="destructive"
                onClick={() => setShowDeleteDialog(true)}
                className="w-full md:w-auto"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Request Account Deletion
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        {/* DPO Contact */}
        {dpo && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Data Protection Officer
                </CardTitle>
                <CardDescription>
                  Contact our DPO for data protection inquiries or complaints
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Organization</p>
                    <p className="font-medium">{dpo.organization}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Email</p>
                    <p className="font-medium">{dpo.email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Response Time</p>
                    <p className="font-medium">{dpo.response_time}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Authority</p>
                    <p className="font-medium">{dpo.authority}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Delete Account Dialog */}
        <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Confirm Account Deletion
              </DialogTitle>
              <DialogDescription>
                This will schedule your account for deletion. You have 30 days to cancel.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="flex items-start gap-3">
                <Checkbox
                  id="keep-orders"
                  checked={keepOrders}
                  onCheckedChange={(checked) => setKeepOrders(checked as boolean)}
                />
                <div>
                  <label htmlFor="keep-orders" className="font-medium cursor-pointer">
                    Keep order history for tax compliance
                  </label>
                  <p className="text-xs text-muted-foreground">
                    Required by Egyptian Tax Law — Article 35
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Reason (optional)</label>
                <Select value={deleteReason} onValueChange={setDeleteReason}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a reason" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="no_longer_needed">No longer needed</SelectItem>
                    <SelectItem value="privacy_concerns">Privacy concerns</SelectItem>
                    <SelectItem value="too_many_notifications">Too many notifications</SelectItem>
                    <SelectItem value="better_alternative">Found a better alternative</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-start gap-3 p-3 rounded-lg bg-destructive/5">
                <Checkbox
                  id="confirm-delete"
                  checked={deleteConfirm}
                  onCheckedChange={(checked) => setDeleteConfirm(checked as boolean)}
                />
                <label
                  htmlFor="confirm-delete"
                  className="text-sm font-medium text-destructive cursor-pointer"
                >
                  I understand that this action is irreversible after the 30-day grace period
                </label>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteAccount}
                disabled={deleteMutation.isPending || !deleteConfirm}
              >
                {deleteMutation.isPending ? 'Processing...' : 'Delete My Account'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </MainLayout>
  );
}

function UserIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  );
}
