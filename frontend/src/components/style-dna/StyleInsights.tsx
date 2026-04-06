/**
 * Style Insights Component
 * Displays personalized style insights and recommendations
 */

import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';
import {
  Star,
  Compass,
  Shirt,
  TrendingUp,
  Lightbulb,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

interface StyleInsight {
  type: string;
  title: string;
  message: string;
  icon: string;
}

interface StyleInsightsProps {
  insights: StyleInsight[];
  className?: string;
}

const iconMap: Record<string, React.ReactNode> = {
  star: <Star className="h-5 w-5" />,
  compass: <Compass className="h-5 w-5" />,
  shirt: <Shirt className="h-5 w-5" />,
  trending: <TrendingUp className="h-5 w-5" />,
  lightbulb: <Lightbulb className="h-5 w-5" />,
  alert: <AlertCircle className="h-5 w-5" />,
  check: <CheckCircle className="h-5 w-5" />,
};

const typeColors: Record<string, string> = {
  confidence: 'bg-primary/10 border-primary/30',
  wardrobe: 'bg-blue-500/10 border-blue-500/30',
  evolution: 'bg-purple-500/10 border-purple-500/30',
  recommendation: 'bg-green-500/10 border-green-500/30',
};

export const StyleInsights: React.FC<StyleInsightsProps> = ({
  insights,
  className,
}) => {
  if (!insights || insights.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-4', className)}>
      <h3 className="text-lg font-semibold">Style Insights</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {insights.map((insight, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={createTransition({ delay: index * 0.1 })}
            className={cn(
              'rounded-lg border p-4',
              typeColors[insight.type] || 'bg-card border-border'
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                {iconMap[insight.icon] || <Lightbulb className="h-5 w-5" />}
              </div>
              <div>
                <h4 className="font-medium">{insight.title}</h4>
                <p className="text-sm text-muted-foreground mt-1">
                  {insight.message}
                </p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default StyleInsights;
