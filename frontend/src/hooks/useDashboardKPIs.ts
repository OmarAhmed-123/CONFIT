/**
 * CONFIT — Dashboard KPI Computation Hook
 * =========================================
 * Computes KPI values from filtered sales data with trend deltas.
 */

import { useMemo } from 'react';
import type { SaleRecord, KPIData, KPIValue } from '@/types/dashboard';

function computeKPI(
  label: string,
  current: number,
  previous: number,
  format: (v: number) => string
): KPIValue {
  const delta = previous === 0 ? (current > 0 ? 100 : 0) : ((current - previous) / previous) * 100;
  return {
    current,
    previous,
    delta: Math.round(delta * 10) / 10,
    formatted: format(current),
  };
}

export function useDashboardKPIs(filteredData: SaleRecord[], allData: SaleRecord[]): KPIData {
  return useMemo(() => {
    // Current period data
    const activeSales = filteredData.filter(r => r.returnStatus !== 'Returned');
    const totalRevenue = activeSales.reduce((sum, r) => sum + r.price * r.quantity, 0);
    const totalOrders = filteredData.length;
    const returnedOrders = filteredData.filter(r => r.returnStatus === 'Returned').length;
    const avgOrder = totalOrders > 0 ? totalRevenue / totalOrders : 0;
    // Simulated sessions (1.4x–1.8x orders for conversion rate)
    const sessions = Math.max(1, Math.round(totalOrders * (1.4 + Math.random() * 0.4)));
    const conversionRate = sessions > 0 ? (totalOrders / sessions) * 100 : 0;
    const returnRate = totalOrders > 0 ? (returnedOrders / totalOrders) * 100 : 0;

    // Previous period — use full dataset minus filtered as rough comparison
    const prevSales = allData.filter(r => !filteredData.includes(r));
    const prevActive = prevSales.filter(r => r.returnStatus !== 'Returned');
    const prevRevenue = prevActive.reduce((sum, r) => sum + r.price * r.quantity, 0);
    const prevOrders = prevSales.length;
    const prevReturned = prevSales.filter(r => r.returnStatus === 'Returned').length;
    const prevAvg = prevOrders > 0 ? prevRevenue / prevOrders : 0;
    const prevSessions = Math.max(1, Math.round(prevOrders * 1.6));
    const prevConv = prevSessions > 0 ? (prevOrders / prevSessions) * 100 : 0;
    const prevReturn = prevOrders > 0 ? (prevReturned / prevOrders) * 100 : 0;

    return {
      totalSales: computeKPI(
        'Total Sales',
        totalRevenue,
        prevRevenue,
        v => `EGP ${v.toLocaleString()}`
      ),
      conversionRate: computeKPI(
        'Conversion Rate',
        conversionRate,
        prevConv,
        v => `${v.toFixed(1)}%`
      ),
      returnRate: computeKPI(
        'Return Rate',
        returnRate,
        prevReturn,
        v => `${v.toFixed(1)}%`
      ),
      avgOrderValue: computeKPI(
        'Avg Order Value',
        avgOrder,
        prevAvg,
        v => `EGP ${Math.round(v).toLocaleString()}`
      ),
    };
  }, [filteredData, allData]);
}
