/**
 * CONFIT CARE - Impact Chart Component
 * =====================================
 * Visualizes campaign impact and spending data.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { PieChart, BarChart3, TrendingUp } from 'lucide-react';

interface ImpactChartProps {
  data: Record<string, number>;
  type?: 'pie' | 'bar';
}

interface ChartData {
  name: string;
  value: number;
  color: string;
}

const COLORS = [
  '#8B5CF6', // purple
  '#EC4899', // pink
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // amber
  '#EF4444', // red
  '#6366F1', // indigo
  '#14B8A6', // teal
];

export const ImpactChart: React.FC<ImpactChartProps> = ({ data, type = 'pie' }) => {
  const chartData: ChartData[] = Object.entries(data)
    .filter(([_, value]) => value > 0)
    .map(([name, value], index) => ({
      name,
      value,
      color: COLORS[index % COLORS.length],
    }))
    .sort((a, b) => b.value - a.value);

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  if (chartData.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-gray-400">
        <PieChart className="w-12 h-12 mb-2" />
        <p className="text-sm">No data to display</p>
      </div>
    );
  }

  if (type === 'bar') {
    return (
      <div className="space-y-3">
        {chartData.map((item, index) => (
          <motion.div
            key={item.name}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center gap-3"
          >
            <div className="w-24 text-sm text-gray-600 truncate">{item.name}</div>
            <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(item.value / total) * 100}%` }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="h-full rounded-full"
                style={{ backgroundColor: item.color }}
              />
            </div>
            <div className="w-16 text-right text-sm font-medium text-gray-700">
              {item.value.toLocaleString()}
            </div>
          </motion.div>
        ))}
      </div>
    );
  }

  // Pie chart representation (simplified for non-SVG)
  return (
    <div className="flex items-center gap-4">
      {/* Visual representation */}
      <div className="w-32 h-32 relative">
        <div className="w-full h-full rounded-full overflow-hidden" style={{
          background: `conic-gradient(${chartData
            .map((item, index) => {
              const prevTotal = chartData
                .slice(0, index)
                .reduce((sum, i) => sum + i.value, 0);
              const startAngle = (prevTotal / total) * 360;
              const endAngle = ((prevTotal + item.value) / total) * 360;
              return `${item.color} ${startAngle}deg ${endAngle}deg`;
            })
            .join(', ')})`
        }} />
      </div>

      {/* Legend */}
      <div className="flex-1 space-y-2">
        {chartData.slice(0, 5).map((item, index) => (
          <motion.div
            key={item.name}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center gap-2"
          >
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-sm text-gray-600 flex-1 truncate">{item.name}</span>
            <span className="text-sm font-medium text-gray-700">
              {Math.round((item.value / total) * 100)}%
            </span>
          </motion.div>
        ))}
        {chartData.length > 5 && (
          <p className="text-xs text-gray-400">
            +{chartData.length - 5} more categories
          </p>
        )}
      </div>
    </div>
  );
};

export default ImpactChart;
