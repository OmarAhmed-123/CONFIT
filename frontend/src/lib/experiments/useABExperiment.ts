import { useEffect, useMemo, useRef, useState } from "react";
import { apiUrl } from "@/lib/api";

export type ABVariant = string;

type UseABExperimentOptions<TVariantValue> = {
  experimentId: string;
  variants: Array<{ id: ABVariant; value: TVariantValue }>;
  exposureEvent?: string;
  weights?: number[];
};

type TrackPayload = {
  experimentId: string;
  variant: ABVariant;
  event: string;
  metadata?: Record<string, unknown>;
};

async function trackExperimentEvent(payload: TrackPayload): Promise<void> {
  try {
    await fetch(apiUrl("/api/experiments/track"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        experimentId: payload.experimentId,
        variant: payload.variant,
        event: payload.event,
        metadata: payload.metadata ?? {},
      }),
    });
  } catch {
    // Tracking must never break UX.
  }
}

function getStorageKey(experimentId: string) {
  return `confit_exp_${experimentId}`;
}

function pickWeightedVariant(variants: Array<{ id: ABVariant; value: unknown }>, weights?: number[]) {
  const ids = variants.map((v) => v.id);
  if (!weights || weights.length !== variants.length) {
    // Uniform
    return ids[Math.floor(Math.random() * ids.length)] ?? ids[0] ?? "A";
  }

  const total = weights.reduce((a, b) => a + Math.max(0, b), 0);
  if (!Number.isFinite(total) || total <= 0) return ids[0] ?? "A";

  const r = Math.random() * total;
  let acc = 0;
  for (let i = 0; i < ids.length; i += 1) {
    acc += Math.max(0, weights[i] ?? 0);
    if (r <= acc) return ids[i] ?? ids[0];
  }
  return ids[ids.length - 1] ?? "A";
}

export function useABExperiment<TVariantValue>(options: UseABExperimentOptions<TVariantValue>) {
  const { experimentId, variants, exposureEvent = "exposure" } = options;

  const [variantId, setVariantId] = useState<ABVariant>("A");
  const didExposeRef = useRef(false);

  useEffect(() => {
    const key = getStorageKey(experimentId);
    try {
      const existing = window.localStorage.getItem(key);
      if (existing) {
        setVariantId(existing);
        return;
      }

      const picked = pickWeightedVariant(variants, options.weights);
      setVariantId(picked);
      window.localStorage.setItem(key, picked);
    } catch {
      // Storage might be blocked. Fall back to a random pick.
      setVariantId(pickWeightedVariant(variants, options.weights));
    }
  }, [experimentId, variants, options.weights]);

  useEffect(() => {
    if (didExposeRef.current) return;
    if (!variantId) return;
    didExposeRef.current = true;
    void trackExperimentEvent({
      experimentId,
      variant: variantId,
      event: exposureEvent,
      metadata: {},
    });
  }, [experimentId, variantId, exposureEvent]);

  const variantValue = useMemo(() => {
    return variants.find((v) => v.id === variantId)?.value ?? variants[0]?.value;
  }, [variantId, variants]);

  const track = useMemo(() => {
    return (event: string, metadata?: Record<string, unknown>) => {
      void trackExperimentEvent({ experimentId, variant: variantId, event, metadata });
    };
  }, [experimentId, variantId]);

  return { variantId, variantValue, track };
}

