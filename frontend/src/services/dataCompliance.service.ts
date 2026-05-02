/**
 * CONFIT — Data Compliance (GDPR) Service
 * Egypt Law 151/2020 — Personal Data Protection Law
 */

import { api } from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';

// ═══════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════

export interface DataExportRequest {
  format: 'json' | 'csv' | 'pdf';
  include_tryon_photos?: boolean;
}

export interface DataExportResponse {
  export_id: string;
  status: string;
  download_url?: string;
  expires_at?: string;
  estimated_size_mb: number;
  data_categories: string[];
}

export interface DataExportStatus {
  export_id: string;
  status: 'processing' | 'ready' | 'expired';
  progress_percent: number;
  estimated_completion: string;
}

export interface UserDataSummary {
  profile: Record<string, unknown>;
  style_dna?: Record<string, unknown> | null;
  orders_count: number;
  tryon_sessions_count: number;
  photos_count: number;
  wardrobe_items_count: number;
  notifications_count: number;
  donation_history_count: number;
  data_retention_policy: Record<string, string>;
  last_updated: string;
}

export interface DataDeletionRequest {
  reason?: string;
  confirm_deletion: boolean;
  keep_order_history: boolean;
}

export interface DataDeletionResponse {
  request_id: string;
  status: string;
  deletion_date: string;
  retained_data: string[];
  retention_reason: string;
  grace_period_days: number;
}

export interface RetentionPolicy {
  data_type: string;
  retention_period: string;
  legal_basis: string;
  auto_delete: boolean;
  next_purge_date?: string;
}

export interface DpoContact {
  organization: string;
  dpo_name: string;
  email: string;
  phone: string;
  address: string;
  response_time: string;
  languages: string[];
  authority: string;
  law_reference: string;
}

// ═══════════════════════════════════════════════════════════════════
// Service Functions
// ═══════════════════════════════════════════════════════════════════

export async function getDataSummary(): Promise<UserDataSummary> {
  return api.get<UserDataSummary>(API_ENDPOINTS.DATA_COMPLIANCE.SUMMARY);
}

export async function requestDataExport(
  request: DataExportRequest
): Promise<DataExportResponse> {
  return api.post<DataExportResponse>(
    API_ENDPOINTS.DATA_COMPLIANCE.EXPORT,
    request
  );
}

export async function getExportStatus(exportId: string): Promise<DataExportStatus> {
  return api.get<DataExportStatus>(
    API_ENDPOINTS.DATA_COMPLIANCE.EXPORT_STATUS(exportId)
  );
}

export async function requestAccountDeletion(
  request: DataDeletionRequest
): Promise<DataDeletionResponse> {
  return api.delete<DataDeletionResponse>(
    API_ENDPOINTS.DATA_COMPLIANCE.DELETE,
    { body: JSON.stringify(request) }
  );
}

export async function getRetentionPolicies(): Promise<RetentionPolicy[]> {
  return api.get<RetentionPolicy[]>(
    API_ENDPOINTS.DATA_COMPLIANCE.RETENTION_POLICIES
  );
}

export async function getDpoContact(): Promise<DpoContact> {
  return api.get<DpoContact>(API_ENDPOINTS.DATA_COMPLIANCE.DPO_CONTACT);
}

export default {
  getDataSummary,
  requestDataExport,
  getExportStatus,
  requestAccountDeletion,
  getRetentionPolicies,
  getDpoContact,
};
