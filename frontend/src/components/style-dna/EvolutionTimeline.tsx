/**
 * Evolution Timeline Component
 * Shows how user's style has evolved over time
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { TrendingUp, Palette, Shirt, Target } from 'lucide-react';
import { createTransition } from '@/motion';

interface EvolutionEvent {
  id: string;
  user_id: string;
  change_type: string;
  previous_value: Record<string, unknown> | null;
  new_value: Record<string, unknown>;
  drift_magnitude: number | null;
  trigger_source: string;
  created_at: string;
}

interface EvolutionTimelineProps {
  events: EvolutionEvent[];
  className?: string;
}

const changeTypeIcons: Record<string, React.ReactNode> = {
  primary_style: <Shirt className="h-4 w-4" />,
  primary_style_detected: <Shirt className="h-4 w-4" />,
  color_preferences: <Palette className="h-4 w-4" />,
  budget_level: <Target className="h-4 w-4" />,
  vector_update: <TrendingUp className="h-4 w-4" />,
};

const changeTypeLabels: Record<string, string> = {
  primary_style: 'Style Updated',
  primary_style_detected: 'Style Detected',
  color_preferences: 'Colors Changed',
  budget_level: 'Budget Updated',
  vector_update: 'Style Vector Recalculated',
};

export const EvolutionTimeline: React.FC<EvolutionTimelineProps> = ({
  events,
  className,
}) => {
  if (!events || events.length === 0) {
    return (
      <div className={cn('h-64 flex items-center justify-center', className)}>
        <div className="text-center text-muted-foreground">
          <TrendingUp className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No style evolution yet</p>
          <p className="text-sm mt-1">
            Your style journey will be tracked here as you update your preferences
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('relative', className)}>
      {/* Timeline line */}
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />

      {/* Events */}
      <div className="space-y-4">
        {events.map((event, index) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={createTransition({ delay: index * 0.1 })}
            className="relative pl-10"
          >
            {/* Event marker */}
            <div
              className={cn(
                'absolute left-2 top-1 w-5 h-5 rounded-full',
                'bg-card border-2 border-primary flex items-center justify-center'
              )}
            >
              {changeTypeIcons[event.change_type] || (
                <TrendingUp className="h-3 w-3" />
              )}
            </div>

            {/* Event content */}
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium">
                  {changeTypeLabels[event.change_type] || event.change_type}
                </h4>
                <span className="text-xs text-muted-foreground">
                  {format(new Date(event.created_at), 'MMM d, yyyy')}
                </span>
              </div>

              {/* Change details */}
              <div className="flex items-center gap-4 text-sm">
                {event.previous_value && (
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <span className="line-through">
                      {formatValue(event.previous_value)}
                    </span>
                  </div>
                )}
                <span className="text-primary">→</span>
                <div className="font-medium">
                  {formatValue(event.new_value)}
                </div>
              </div>

              {/* Drift magnitude */}
              {event.drift_magnitude !== null && event.drift_magnitude > 0 && (
                <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                  <TrendingUp className="h-3 w-3" />
                  <span>
                    Style drift: {(event.drift_magnitude * 100).toFixed(1)}%
                  </span>
                </div>
              )}

              {/* Trigger source */}
              <div className="mt-2 text-xs text-muted-foreground">
                Source: {event.trigger_source.replace('_', ' ')}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

function formatValue(value: Record<string, unknown>): string {
  if (value.style) {
    return String(value.style).replace('_', ' ');
  }
  if (value.color) {
    return String(value.color);
  }
  if (value.budget_level) {
    return String(value.budget_level).replace('_', ' ');
  }
  return JSON.stringify(value).slice(0, 30);
}

export default EvolutionTimeline;
