export interface ApiEnvelope<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export function unwrapApiData<T>(payload: unknown): T {
  if (payload && typeof payload === 'object' && 'success' in (payload as Record<string, unknown>)) {
    const envelope = payload as ApiEnvelope<T>;
    if (!envelope.success) {
      throw new Error(envelope.error || 'Request failed');
    }
    return envelope.data as T;
  }
  return payload as T;
}

