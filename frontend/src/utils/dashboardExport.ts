/**
 * CONFIT — Dashboard Export Utilities
 * =====================================
 * CSV and PDF export functions for the Store Owner Dashboard.
 * Exports respect active filters — only filtered+sorted data is exported.
 * Filenames include timestamp: CONFIT_SalesReport_YYYY-MM-DD_HH-MM
 */

import type { SaleRecord, KPIData } from '@/types/dashboard';

// ─── Timestamp Filename Helper ──────────────────────────────────

function brandedFilename(ext: string): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  const ts = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
  return `CONFIT_SalesReport_${ts}.${ext}`;
}

// ─── CSV Export ─────────────────────────────────────────────────

export function exportCSV(data: SaleRecord[], filename?: string) {
  const finalFilename = filename || brandedFilename('csv');
  const headers = [
    'Product Name', 'Category', 'Type', 'SKU', 'Price', 'Quantity', 'Currency',
    'Customer Name', 'Customer Email', 'Customer Segment', 'Sale Date',
    'Profit Margin %', 'Return Status', 'Brand', 'Payment Method', 'Order ID',
  ];

  const rows = data.map(r => [
    r.productName,
    r.category,
    r.productType,
    r.sku,
    r.price.toString(),
    r.quantity.toString(),
    r.currency,
    r.customerName,
    r.customerEmail || '',
    r.customerSegment,
    new Date(r.saleDate).toLocaleString(),
    r.profitMargin.toString(),
    r.returnStatus,
    r.brand,
    r.paymentMethod,
    r.orderId,
  ]);

  const csv = [headers, ...rows]
    .map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
    .join('\n');

  downloadBlob(csv, finalFilename, 'text/csv;charset=utf-8;');
}

// ─── PDF Export ─────────────────────────────────────────────────

export async function exportPDF(
  data: SaleRecord[],
  kpis: KPIData,
  storeName = 'CONFIT Store',
  appliedFilters: string[] = []
) {
  // Dynamic import to avoid bundling jspdf if not used
  const [{ default: jsPDF }, { default: autoTable }] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ]);

  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const now = new Date().toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });

  // ─── Header ───────────────────────────────────────────────────
  doc.setFillColor(20, 24, 38); // CONFIT dark bg
  doc.rect(0, 0, pageWidth, 28, 'F');

  doc.setTextColor(212, 175, 55); // Gold
  doc.setFontSize(20);
  doc.setFont('helvetica', 'bold');
  doc.text('CONFIT', 14, 14);

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text(`Sales Report — ${storeName}`, 14, 22);

  doc.setFontSize(9);
  doc.text(`Generated: ${now}`, pageWidth - 14, 22, { align: 'right' });

  // ─── KPI Strip ────────────────────────────────────────────────
  const kpiY = 34;
  const kpiEntries = [
    { label: 'Total Sales', value: kpis.totalSales.formatted, delta: kpis.totalSales.delta },
    { label: 'Conversion Rate', value: kpis.conversionRate.formatted, delta: kpis.conversionRate.delta },
    { label: 'Return Rate', value: kpis.returnRate.formatted, delta: kpis.returnRate.delta },
    { label: 'Avg Order Value', value: kpis.avgOrderValue.formatted, delta: kpis.avgOrderValue.delta },
  ];

  const kpiWidth = (pageWidth - 28 - 18) / 4;
  kpiEntries.forEach((kpi, i) => {
    const x = 14 + i * (kpiWidth + 6);
    doc.setFillColor(30, 35, 50);
    doc.roundedRect(x, kpiY, kpiWidth, 18, 2, 2, 'F');

    doc.setTextColor(160, 160, 170);
    doc.setFontSize(8);
    doc.text(kpi.label, x + 4, kpiY + 6);

    doc.setTextColor(255, 255, 255);
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(kpi.value, x + 4, kpiY + 13);

    const deltaColor = kpi.label === 'Return Rate'
      ? (kpi.delta <= 0 ? [76, 175, 80] : [244, 67, 54])
      : (kpi.delta >= 0 ? [76, 175, 80] : [244, 67, 54]);
    doc.setTextColor(deltaColor[0], deltaColor[1], deltaColor[2]);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.text(`${kpi.delta >= 0 ? '↑' : '↓'} ${Math.abs(kpi.delta)}%`, x + kpiWidth - 4, kpiY + 13, { align: 'right' });
  });

  // ─── Applied Filters Summary ──────────────────────────────────
  let filterEndY = kpiY + 24;
  if (appliedFilters.length > 0) {
    const filterY = kpiY + 24;
    doc.setFontSize(8);
    doc.setTextColor(160, 160, 170);
    doc.text('Active Filters:', 14, filterY);
    doc.setTextColor(212, 175, 55);
    doc.text(appliedFilters.join('  •  '), 46, filterY);
    filterEndY = filterY + 6;
  }

  // ─── Data Table ────────────────────────────────────────────────
  const tableHeaders = [
    'Product', 'Category', 'Price', 'Qty', 'Customer', 'Date', 'Margin', 'Status',
  ];

  const tableBody = data.map(r => [
    r.productName,
    r.category,
    `${r.currency} ${r.price.toLocaleString()}`,
    r.quantity.toString(),
    r.customerName,
    new Date(r.saleDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    `${r.profitMargin}%`,
    r.returnStatus,
  ]);

  autoTable(doc, {
    head: [tableHeaders],
    body: tableBody,
    startY: filterEndY,
    theme: 'grid',
    styles: {
      fontSize: 7,
      cellPadding: 2,
      textColor: [230, 230, 230],
      fillColor: [25, 30, 45],
      lineColor: [50, 55, 70],
      lineWidth: 0.2,
    },
    headStyles: {
      fillColor: [40, 45, 60],
      textColor: [212, 175, 55],
      fontStyle: 'bold',
      fontSize: 8,
    },
    alternateRowStyles: {
      fillColor: [30, 35, 50],
    },
    margin: { left: 14, right: 14 },
  });

  // ─── Footer ───────────────────────────────────────────────────
  const pageCount = doc.getNumberOfPages();
  for (let p = 1; p <= pageCount; p++) {
    doc.setPage(p);
    doc.setFontSize(7);
    doc.setTextColor(120, 120, 130);
    doc.text(
      `CONFIT Sales Report • Page ${p} of ${pageCount}`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 6,
      { align: 'center' }
    );
  }

  doc.save(brandedFilename('pdf'));
}

// ─── Utility ────────────────────────────────────────────────────

function downloadBlob(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
