/**
 * CONFIT — A/B Test Config Panel
 * ================================
 * Test creation form with variant configuration,
 * recipient segment selector, and traffic slider.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, FlaskConical, X } from 'lucide-react';
import { useABTestStore } from '@/stores/abTestStore';
import type {
  ABTestVariable,
  ABTestSegment,
} from '@/types/notificationAnalyticsTypes';

interface ABTestConfigPanelProps {
  onClose: () => void;
}

const VARIABLE_OPTIONS: { value: ABTestVariable; label: string; description: string }[] = [
  { value: 'channel', label: 'Channel', description: 'Test different notification channels' },
  { value: 'timing', label: 'Timing', description: 'Test delivery timing (immediate vs delayed)' },
  { value: 'content', label: 'Content', description: 'Test notification content formats' },
  { value: 'frequency', label: 'Frequency', description: 'Test delivery frequency settings' },
];

const SEGMENT_OPTIONS: { value: ABTestSegment; label: string }[] = [
  { value: 'all_customers', label: 'All Customers' },
  { value: 'all_owners', label: 'All Store Owners' },
  { value: 'new_customers', label: 'New Customers' },
  { value: 'repeat_customers', label: 'Repeat Customers' },
  { value: 'specific_stores', label: 'Specific Stores' },
];

export function ABTestConfigPanel({ onClose }: ABTestConfigPanelProps) {
  const { createTest } = useABTestStore();
  const [name, setName] = useState('');
  const [hypothesis, setHypothesis] = useState('');
  const [variable, setVariable] = useState<ABTestVariable>('channel');
  const [segment, setSegment] = useState<ABTestSegment>('all_customers');
  const [trafficPct, setTrafficPct] = useState(50);
  const [durationDays, setDurationDays] = useState(14);
  const [variantAName, setVariantAName] = useState('Control');
  const [variantADesc, setVariantADesc] = useState('');
  const [variantBName, setVariantBName] = useState('Variant B');
  const [variantBDesc, setVariantBDesc] = useState('');

  const handleCreate = () => {
    if (!name.trim() || !hypothesis.trim()) return;

    createTest({
      name: name.trim(),
      hypothesis: hypothesis.trim(),
      variable,
      segment,
      traffic_percentage: trafficPct,
      duration_days: durationDays,
      variants: [
        { id: `var-${Date.now()}-a`, name: variantAName, description: variantADesc, config: {} },
        { id: `var-${Date.now()}-b`, name: variantBName, description: variantBDesc, config: {} },
      ],
    });
    onClose();
  };

  const isValid = name.trim().length > 0 && hypothesis.trim().length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-white/[0.08] bg-[hsl(220,22%,9%)] p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-foreground font-sans">
            Create A/B Test
          </h3>
        </div>
        <button
          onClick={onClose}
          className="h-8 w-8 rounded-lg bg-white/[0.04] flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-5">
        {/* Test Name */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-1.5">
            Test Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Email vs Push for Order Confirmations"
            className="w-full px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-foreground text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
          />
        </div>

        {/* Hypothesis */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-1.5">
            Hypothesis *
          </label>
          <textarea
            value={hypothesis}
            onChange={(e) => setHypothesis(e.target.value)}
            placeholder="e.g., Push notifications will achieve higher open rates than email"
            rows={2}
            className="w-full px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-foreground text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-amber-500/50 resize-none"
          />
        </div>

        {/* Variable & Segment */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-1.5">
              Variable to Test
            </label>
            <select
              value={variable}
              onChange={(e) => setVariable(e.target.value as ABTestVariable)}
              className="w-full px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            >
              {VARIABLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-[hsl(220,22%,12%)]">
                  {opt.label} — {opt.description}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-1.5">
              Recipient Segment
            </label>
            <select
              value={segment}
              onChange={(e) => setSegment(e.target.value as ABTestSegment)}
              className="w-full px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            >
              {SEGMENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-[hsl(220,22%,12%)]">
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Traffic % and Duration */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-1.5">
              Traffic Percentage: {trafficPct}%
            </label>
            <input
              type="range"
              min={5}
              max={100}
              step={5}
              value={trafficPct}
              onChange={(e) => setTrafficPct(parseInt(e.target.value))}
              className="w-full accent-amber-500"
            />
            <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
              <span>5%</span>
              <span>100%</span>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-1.5">
              Duration (days)
            </label>
            <input
              type="number"
              value={durationDays}
              onChange={(e) => setDurationDays(Math.max(1, parseInt(e.target.value) || 1))}
              min={1}
              max={90}
              className="w-full px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
        </div>

        {/* Variants */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block mb-2">
            Variants
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <input
                type="text"
                value={variantAName}
                onChange={(e) => setVariantAName(e.target.value)}
                className="w-full px-2 py-1.5 rounded bg-white/[0.04] border border-white/[0.06] text-foreground text-sm mb-2 focus:outline-none"
                placeholder="Variant A name"
              />
              <input
                type="text"
                value={variantADesc}
                onChange={(e) => setVariantADesc(e.target.value)}
                className="w-full px-2 py-1.5 rounded bg-white/[0.04] border border-white/[0.06] text-muted-foreground text-xs focus:outline-none"
                placeholder="Description"
              />
            </div>
            <div className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <input
                type="text"
                value={variantBName}
                onChange={(e) => setVariantBName(e.target.value)}
                className="w-full px-2 py-1.5 rounded bg-white/[0.04] border border-white/[0.06] text-foreground text-sm mb-2 focus:outline-none"
                placeholder="Variant B name"
              />
              <input
                type="text"
                value={variantBDesc}
                onChange={(e) => setVariantBDesc(e.target.value)}
                className="w-full px-2 py-1.5 rounded bg-white/[0.04] border border-white/[0.06] text-muted-foreground text-xs focus:outline-none"
                placeholder="Description"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!isValid}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              isValid
                ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-[hsl(220,25%,8%)] hover:shadow-lg hover:shadow-amber-500/20'
                : 'bg-white/[0.06] text-muted-foreground cursor-not-allowed'
            }`}
          >
            <Plus className="h-4 w-4" />
            Create Test
          </button>
        </div>
      </div>
    </motion.div>
  );
}
