/**
 * CONFIT — Analytics Export Component
 * =====================================
 * PDF export functionality for notification analytics dashboard.
 * Generates branded reports with charts, KPIs, and recommendations.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileDown,
  Loader2,
  CheckCircle2,
  XCircle,
  FileText,
  Image,
  Table,
} from 'lucide-react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import type {
  AnalyticsKPI,
  ChannelMetrics,
  HeatmapCell,
  ConversionDataPoint,
  OwnerResponseTime,
  DashboardPeriod,
} from '@/types/notificationAnalyticsTypes';
import { periodToDays } from '@/types/notificationAnalyticsTypes';
import { notificationAnalyticsApi } from '@/services/notificationAnalyticsApi';

interface AnalyticsExportProps {
  kpis: AnalyticsKPI | null;
  channelMetrics: ChannelMetrics[];
  heatmap?: HeatmapCell[];
  conversions?: ConversionDataPoint[];
  ownerResponseTimes?: OwnerResponseTime[];
  period: DashboardPeriod;
  timezone?: string;
}

type ExportFormat = 'pdf' | 'csv';

interface ExportState {
  isExporting: boolean;
  success: boolean;
  error: string | null;
}

const BRAND_COLORS = {
  primary: [245, 158, 11] as [number, number, number], // amber-500
  secondary: [168, 85, 247] as [number, number, number], // purple-500
  text: [31, 41, 55] as [number, number, number], // gray-700
  light: [243, 244, 246] as [number, number, number], // gray-100
};

export function AnalyticsExport({
  kpis,
  channelMetrics,
  heatmap,
  conversions,
  ownerResponseTimes,
  period,
  timezone = 'UTC',
}: AnalyticsExportProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [state, setState] = useState<ExportState>({
    isExporting: false,
    success: false,
    error: null,
  });

  const generatePDF = useCallback(async () => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 20;
    let y = 20;

    // ── Header ────────────────────────────────────────────────────────
    doc.setFillColor(...BRAND_COLORS.primary);
    doc.rect(0, 0, pageWidth, 40, 'F');
    
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(24);
    doc.setFont('helvetica', 'bold');
    doc.text('CONFIT Analytics Report', margin, 25);
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    const days = periodToDays(period);
    const dateRange = `${days}-day period ending ${new Date().toLocaleDateString()}`;
    doc.text(dateRange, margin, 33);

    y = 55;

    // ── Executive Summary ─────────────────────────────────────────────
    doc.setTextColor(...BRAND_COLORS.text);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Executive Summary', margin, y);
    y += 10;

    if (kpis) {
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      
      const summaryData = [
        ['Delivery Rate', `${(kpis.overall_delivery_rate * 100).toFixed(1)}%`],
        ['Average Open Rate', `${(kpis.avg_open_rate * 100).toFixed(1)}%`],
        ['Average Click Rate', `${(kpis.avg_click_rate * 100).toFixed(1)}%`],
        ['Most Used Channel', kpis.most_used_channel.replace('_', '-').toUpperCase()],
        ['Top Conversion Channel', kpis.top_conversion_channel.replace('_', '-').toUpperCase()],
        ['Total Events', kpis.total_events.toLocaleString()],
        ['Delivery Rate Trend', kpis.delivery_rate_trend >= 0 ? `+${(kpis.delivery_rate_trend * 100).toFixed(1)}%` : `${(kpis.delivery_rate_trend * 100).toFixed(1)}%`],
        ['Open Rate Trend', kpis.open_rate_trend >= 0 ? `+${(kpis.open_rate_trend * 100).toFixed(1)}%` : `${(kpis.open_rate_trend * 100).toFixed(1)}%`],
      ];

      autoTable(doc, {
        startY: y,
        head: [['Metric', 'Value']],
        body: summaryData,
        theme: 'striped',
        headStyles: { fillColor: BRAND_COLORS.primary },
        margin: { left: margin, right: margin },
        tableWidth: 'auto',
      });

      y = (doc as any).lastAutoTable.finalY + 15;
    }

    // ── Channel Performance ───────────────────────────────────────────
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Channel Performance', margin, y);
    y += 10;

    if (channelMetrics.length > 0) {
      const channelData = channelMetrics.map((m) => [
        m.channel.replace('_', '-').toUpperCase(),
        m.total_sent.toLocaleString(),
        m.total_delivered.toLocaleString(),
        `${(m.delivery_rate * 100).toFixed(1)}%`,
        `${(m.open_rate * 100).toFixed(1)}%`,
        `${(m.click_through_rate * 100).toFixed(1)}%`,
      ]);

      autoTable(doc, {
        startY: y,
        head: [['Channel', 'Sent', 'Delivered', 'Delivery %', 'Open %', 'Click %']],
        body: channelData,
        theme: 'striped',
        headStyles: { fillColor: BRAND_COLORS.secondary },
        margin: { left: margin, right: margin },
        tableWidth: 'auto',
      });

      y = (doc as any).lastAutoTable.finalY + 15;
    }

    // ── Conversion Impact ──────────────────────────────────────────────
    if (conversions && conversions.length > 0) {
      // Check if we need a new page
      if (y > 220) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Conversion Impact', margin, y);
      y += 10;

      const conversionData = conversions.map((c) => [
        c.channel.replace('_', '-').toUpperCase(),
        `${c.period_days}d`,
        c.notification_count.toLocaleString(),
        c.repeat_purchases.toLocaleString(),
        `${(c.conversion_rate * 100).toFixed(1)}%`,
      ]);

      autoTable(doc, {
        startY: y,
        head: [['Channel', 'Period', 'Notifications', 'Conversions', 'Rate']],
        body: conversionData,
        theme: 'striped',
        headStyles: { fillColor: BRAND_COLORS.primary },
        margin: { left: margin, right: margin },
        tableWidth: 'auto',
      });

      y = (doc as any).lastAutoTable.finalY + 15;
    }

    // ── Owner Response Times ───────────────────────────────────────────
    if (ownerResponseTimes && ownerResponseTimes.length > 0) {
      // Check if we need a new page
      if (y > 220) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Owner Response Times', margin, y);
      y += 10;

      const responseData = ownerResponseTimes.slice(0, 10).map((o) => [
        o.store_name,
        o.notification_count.toLocaleString(),
        `${o.avg_response_time_min.toFixed(1)} min`,
        `${o.median_response_time_min.toFixed(1)} min`,
      ]);

      autoTable(doc, {
        startY: y,
        head: [['Store', 'Notifications', 'Avg Response', 'Median Response']],
        body: responseData,
        theme: 'striped',
        headStyles: { fillColor: BRAND_COLORS.secondary },
        margin: { left: margin, right: margin },
        tableWidth: 'auto',
      });

      y = (doc as any).lastAutoTable.finalY + 15;
    }

    // ── Engagement Heatmap Summary ─────────────────────────────────────
    if (heatmap && heatmap.length > 0) {
      // Check if we need a new page
      if (y > 200) {
        doc.addPage();
        y = 20;
      }

      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text('Peak Engagement Times', margin, y);
      y += 10;

      // Find top 5 engagement times
      const topTimes = [...heatmap]
        .filter((c) => c.event_count > 0)
        .sort((a, b) => b.open_rate - a.open_rate)
        .slice(0, 5);

      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      
      const heatmapData = topTimes.map((c) => [
        `${dayNames[c.day]} ${c.hour}:00`,
        `${(c.open_rate * 100).toFixed(1)}%`,
        `${(c.click_rate * 100).toFixed(1)}%`,
        c.event_count.toLocaleString(),
      ]);

      autoTable(doc, {
        startY: y,
        head: [['Time Slot', 'Open Rate', 'Click Rate', 'Events']],
        body: heatmapData,
        theme: 'striped',
        headStyles: { fillColor: BRAND_COLORS.primary },
        margin: { left: margin, right: margin },
        tableWidth: 'auto',
      });
    }

    // ── Footer ─────────────────────────────────────────────────────────
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(128, 128, 128);
      doc.text(
        `Generated on ${new Date().toLocaleString()} | Timezone: ${timezone} | Page ${i} of ${pageCount}`,
        margin,
        doc.internal.pageSize.getHeight() - 10
      );
    }

    return doc;
  }, [kpis, channelMetrics, heatmap, conversions, ownerResponseTimes, period, timezone]);

  const handleExport = useCallback(async (format: ExportFormat) => {
    setState({ isExporting: true, success: false, error: null });

    try {
      if (format === 'csv') {
        await notificationAnalyticsApi.downloadCSV({ period: periodToDays(period) });
      } else {
        const doc = await generatePDF();
        doc.save(`confit-analytics-${period}-${new Date().toISOString().split('T')[0]}.pdf`);
      }

      setState({ isExporting: false, success: true, error: null });
      setTimeout(() => {
        setState((s) => ({ ...s, success: false }));
        setShowMenu(false);
      }, 2000);
    } catch (err) {
      setState({
        isExporting: false,
        success: false,
        error: err instanceof Error ? err.message : 'Export failed',
      });
    }
  }, [generatePDF, period]);

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        disabled={state.isExporting}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm font-medium text-foreground hover:bg-white/[0.08] transition-colors disabled:opacity-50"
      >
        {state.isExporting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : state.success ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        ) : state.error ? (
          <XCircle className="h-4 w-4 text-red-400" />
        ) : (
          <FileDown className="h-4 w-4" />
        )}
        Export
      </button>

      <AnimatePresence>
        {showMenu && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-white/[0.08] bg-[hsl(220,22%,12%)] shadow-xl z-50 overflow-hidden"
          >
            <div className="p-1">
              <button
                onClick={() => handleExport('pdf')}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-foreground hover:bg-white/[0.06] transition-colors"
              >
                <FileText className="h-4 w-4 text-amber-400" />
                <div className="text-left">
                  <div className="font-medium">PDF Report</div>
                  <div className="text-xs text-muted-foreground">Full analytics report</div>
                </div>
              </button>

              <button
                onClick={() => handleExport('csv')}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-foreground hover:bg-white/[0.06] transition-colors"
              >
                <Table className="h-4 w-4 text-purple-400" />
                <div className="text-left">
                  <div className="font-medium">CSV Export</div>
                  <div className="text-xs text-muted-foreground">Raw event data</div>
                </div>
              </button>
            </div>

            {state.error && (
              <div className="px-3 py-2 border-t border-white/[0.06] text-xs text-red-400">
                {state.error}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default AnalyticsExport;
