
import { FileText, FileDown, Printer, Share2 } from 'lucide-react';
import { Button } from '../ui';

export function ExportBar() {
  return (
    <div className="h-[60px] border-t border-border bg-background flex items-center justify-between px-4">
      {/* Left side - status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="text-sm text-muted">Ready to export</span>
        </div>
      </div>

      {/* Right side - export buttons */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="text-muted">
          <Share2 size={16} />
          <span>Share</span>
        </Button>
        <Button variant="ghost" size="sm" className="text-muted">
          <Printer size={16} />
          <span>Print</span>
        </Button>
        <Button variant="secondary" size="sm">
          <FileText size={16} />
          <span>Export Word</span>
        </Button>
        <Button variant="primary" size="sm">
          <FileDown size={16} />
          <span>Export PDF</span>
        </Button>
      </div>
    </div>
  );
}
