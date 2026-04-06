/**
 * CONFIT — A/B Test Store
 * ========================
 * Zustand store for managing notification A/B tests.
 * Handles test lifecycle: draft → running → paused → completed → archived.
 * Includes statistical significance calculation via z-test for proportions.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  ABTest,
  ABTestStatus,
  ABTestVariable,
  ABTestSegment,
  ABTestVariant,
} from '@/types/notificationAnalyticsTypes';


// ─── Statistical Helpers ───

/** Standard normal CDF approximation (Abramowitz & Stegun) */
function normalCDF(z: number): number {
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const sign = z < 0 ? -1 : 1;
  const x = Math.abs(z) / Math.sqrt(2);
  const t = 1.0 / (1.0 + p * x);
  const y = 1.0 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
  return 0.5 * (1.0 + sign * y);
}

/** Two-proportion z-test. Returns { z, pValue }. */
function twoProportionZTest(
  p1: number,
  n1: number,
  p2: number,
  n2: number
): { z: number; pValue: number } {
  if (n1 === 0 || n2 === 0) return { z: 0, pValue: 1 };
  const pooled = (p1 * n1 + p2 * n2) / (n1 + n2);
  if (pooled === 0 || pooled === 1) return { z: 0, pValue: 1 };
  const se = Math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2));
  if (se === 0) return { z: 0, pValue: 1 };
  const z = (p1 - p2) / se;
  const pValue = 2 * (1 - normalCDF(Math.abs(z))); // two-tailed
  return { z, pValue };
}

// ─── Store ───

interface ABTestState {
  tests: ABTest[];
  initialized: boolean;

  // Lifecycle
  initialize: () => void;
  createTest: (config: {
    name: string;
    hypothesis: string;
    variable: ABTestVariable;
    segment: ABTestSegment;
    traffic_percentage: number;
    duration_days: number;
    variants: Array<Omit<ABTestVariant, 'sample_size' | 'metrics'>>;
  }) => ABTest;
  startTest: (id: string) => void;
  pauseTest: (id: string) => void;
  completeTest: (id: string) => void;
  archiveTest: (id: string) => void;

  // Selectors
  getActiveTests: () => ABTest[];
  getCompletedTests: () => ABTest[];
  getDraftTests: () => ABTest[];
  getTestById: (id: string) => ABTest | undefined;
  evaluateSignificance: (testId: string, metric: 'open_rate' | 'click_rate' | 'conversion_rate') => {
    z: number;
    pValue: number;
    isSignificant: boolean;
    winnerVariantId?: string;
  };
}

export const useABTestStore = create<ABTestState>()(
  persist(
    (set, get) => ({
      tests: [],
      initialized: false,

      initialize: () => {
        if (get().initialized) return;
        set({ initialized: true });
      },

      createTest: (config) => {
        const now = new Date().toISOString();
        const newTest: ABTest = {
          id: `ab-${Date.now()}`,
          name: config.name,
          hypothesis: config.hypothesis,
          variable: config.variable,
          status: 'draft',
          segment: config.segment,
          traffic_percentage: config.traffic_percentage,
          duration_days: config.duration_days,
          start_date: '',
          variants: config.variants.map((v) => ({
            ...v,
            sample_size: 0,
            metrics: { delivery_rate: 0, open_rate: 0, click_rate: 0, conversion_rate: 0 },
          })),
          is_significant: false,
          created_at: now,
          updated_at: now,
        };

        set((state) => ({ tests: [newTest, ...state.tests] }));
        return newTest;
      },

      startTest: (id) => {
        set((state) => ({
          tests: state.tests.map((t) =>
            t.id === id
              ? { ...t, status: 'running' as ABTestStatus, start_date: new Date().toISOString(), updated_at: new Date().toISOString() }
              : t
          ),
        }));
      },

      pauseTest: (id) => {
        set((state) => ({
          tests: state.tests.map((t) =>
            t.id === id
              ? { ...t, status: 'paused' as ABTestStatus, updated_at: new Date().toISOString() }
              : t
          ),
        }));
      },

      completeTest: (id) => {
        set((state) => ({
          tests: state.tests.map((t) =>
            t.id === id
              ? { ...t, status: 'completed' as ABTestStatus, end_date: new Date().toISOString(), updated_at: new Date().toISOString() }
              : t
          ),
        }));
      },

      archiveTest: (id) => {
        set((state) => ({
          tests: state.tests.map((t) =>
            t.id === id
              ? { ...t, status: 'archived' as ABTestStatus, updated_at: new Date().toISOString() }
              : t
          ),
        }));
      },

      getActiveTests: () => get().tests.filter((t) => t.status === 'running'),
      getCompletedTests: () => get().tests.filter((t) => t.status === 'completed'),
      getDraftTests: () => get().tests.filter((t) => t.status === 'draft'),

      getTestById: (id) => get().tests.find((t) => t.id === id),

      evaluateSignificance: (testId, metric) => {
        const test = get().tests.find((t) => t.id === testId);
        if (!test || test.variants.length < 2) {
          return { z: 0, pValue: 1, isSignificant: false };
        }

        const [v1, v2] = test.variants;
        const result = twoProportionZTest(
          v1.metrics[metric],
          v1.sample_size,
          v2.metrics[metric],
          v2.sample_size
        );

        const isSignificant = result.pValue < 0.05;
        const winnerVariantId = isSignificant
          ? (v1.metrics[metric] > v2.metrics[metric] ? v1.id : v2.id)
          : undefined;

        return {
          z: parseFloat(result.z.toFixed(3)),
          pValue: parseFloat(result.pValue.toFixed(4)),
          isSignificant,
          winnerVariantId,
        };
      },
    }),
    {
      name: 'confit-ab-tests',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        tests: state.tests,
        initialized: state.initialized,
      }),
    }
  )
);
