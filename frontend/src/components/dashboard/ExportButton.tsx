/**
 * CONFIT — Export Button
 * =======================
 * Dropdown button for CSV and PDF export of filtered sales data.
 * Gold accent styling consistent with CONFIT design language.
 */

import { useState } from 'react';
import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { exportCSV, exportPDF } from '@/utils/dashboardExport';
import type { SaleRecord, KPIData } from '@/types/dashboard';

interface ExportButtonProps {
  data: SaleRecord[];
  kpis: KPIData;
  storeName?: string;
  /** Labels of currently active filters — included in PDF export */
  activeFilterLabels?: string[];
}

export function ExportButton({ data, kpis, storeName = 'CONFIT Store', activeFilterLabels = [] }: ExportButtonProps) {
  const [isPDFLoading, setIsPDFLoading] = useState(false);

  const handleCSV = () => {
    exportCSV(data);
  };

  const handlePDF = async () => {
    setIsPDFLoading(true);
    try {
      await exportPDF(data, kpis, storeName, activeFilterLabels);
    } catch (err) {
      console.error('PDF export failed:', err);
    } finally {
      setIsPDFLoading(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 border-accent/30 text-accent hover:bg-accent/10 hover:text-accent"
        >
          {isPDFLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuItem onClick={handleCSV} className="gap-2 cursor-pointer">
          <FileSpreadsheet className="h-4 w-4 text-green-400" />
          Export as CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handlePDF} disabled={isPDFLoading} className="gap-2 cursor-pointer">
          <FileText className="h-4 w-4 text-red-400" />
          Export as PDF
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default ExportButton;
