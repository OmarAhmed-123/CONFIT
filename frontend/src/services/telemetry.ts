import { api } from "@/lib/api";

export async function emitEcosystemEvent(
  event: string,
  data: Record<string, unknown> = {}
): Promise<void> {
  try {
    await api.post("/ecosystem/events/emit", {
      event,
      data,
    });
  } catch {
    // Telemetry must never break the UX.
  }
}

export async function trackBehaviorSignal(
  signalType: string,
  entityType: string,
  entityId: string,
  context: Record<string, unknown> = {},
  durationMs?: number
): Promise<void> {
  try {
    await api.post("/signals/track", {
      signal_type: signalType,
      entity_type: entityType,
      entity_id: entityId,
      context,
      duration_ms: durationMs,
    });
  } catch {
    // Telemetry must never break the UX.
  }
}


