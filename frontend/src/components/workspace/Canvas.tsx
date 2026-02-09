
import { BarChart3, Table2, FileText, Code, MousePointer } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';

export function Canvas() {
  const { state } = useApp();

  const getPlaceholderContent = () => {
    switch (state.activeTab) {
      case 'chart':
        return {
          icon: BarChart3,
          title: 'Chart View',
          description: 'Your generated charts and figures will appear here',
        };
      case 'table':
        return {
          icon: Table2,
          title: 'Table View',
          description: 'Your generated tables and listings will appear here',
        };
      case 'text':
        return {
          icon: FileText,
          title: 'Text View',
          description: 'Your generated text outputs will appear here',
        };
      case 'code':
        return {
          icon: Code,
          title: 'Code View',
          description: 'Your generated code and scripts will appear here',
        };
    }
  };

  const placeholder = getPlaceholderContent();
  const PlaceholderIcon = placeholder.icon;

  // Mock chart display for demonstration
  if (state.activeTab === 'chart') {
    return (
      <div className="flex-1 bg-surface overflow-auto p-6">
        <div className="bg-background border border-border rounded-lg p-6 shadow-sm max-w-4xl mx-auto">
          {/* Mock chart header */}
          <div className="mb-6">
            <h3 className="font-display font-semibold text-lg text-foreground">
              Figure 14.2.1: Kaplan-Meier Plot of Time to First Event
            </h3>
            <p className="text-sm text-muted mt-1">
              ITT Population - Study ABC-123
            </p>
          </div>

          {/* Mock chart area */}
          <div className="h-80 bg-surface border border-border rounded-lg flex items-center justify-center relative overflow-hidden">
            {/* Grid lines */}
            <div className="absolute inset-0 opacity-30">
              {[...Array(5)].map((_, i) => (
                <div
                  key={`h-${i}`}
                  className="absolute left-0 right-0 border-t border-border"
                  style={{ top: `${(i + 1) * 20}%` }}
                />
              ))}
              {[...Array(5)].map((_, i) => (
                <div
                  key={`v-${i}`}
                  className="absolute top-0 bottom-0 border-l border-border"
                  style={{ left: `${(i + 1) * 20}%` }}
                />
              ))}
            </div>

            {/* Mock KM curves */}
            <svg viewBox="0 0 400 200" className="w-full h-full p-8">
              {/* Treatment group - red */}
              <path
                d="M 40 40 L 80 40 L 80 55 L 120 55 L 120 75 L 160 75 L 160 95 L 200 95 L 200 110 L 240 110 L 240 125 L 280 125 L 280 140 L 320 140 L 320 155 L 360 155"
                fill="none"
                stroke="#E42313"
                strokeWidth="2"
              />
              {/* Placebo group - gray */}
              <path
                d="M 40 40 L 70 40 L 70 60 L 100 60 L 100 90 L 130 90 L 130 120 L 160 120 L 160 145 L 190 145 L 190 160 L 220 160 L 220 170 L 250 170"
                fill="none"
                stroke="#7A7A7A"
                strokeWidth="2"
              />
            </svg>

            {/* Y-axis label */}
            <div
              className="absolute left-2 top-1/2 -translate-y-1/2 -rotate-90 text-xs text-muted whitespace-nowrap"
            >
              Probability of Event-Free
            </div>

            {/* X-axis label */}
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-xs text-muted">
              Time (months)
            </div>
          </div>

          {/* Legend */}
          <div className="mt-4 flex items-center justify-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-primary" />
              <span className="text-sm text-foreground">Treatment (n=225)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-muted" />
              <span className="text-sm text-foreground">Placebo (n=225)</span>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-4 border-t border-border text-xs text-muted">
            <p>Source: ADTTE dataset</p>
            <p>Log-rank p-value: 0.0023</p>
          </div>
        </div>
      </div>
    );
  }

  // Mock table display
  if (state.activeTab === 'table') {
    return (
      <div className="flex-1 bg-surface overflow-auto p-6">
        <div className="bg-background border border-border rounded-lg shadow-sm max-w-5xl mx-auto overflow-hidden">
          {/* Table header */}
          <div className="p-4 border-b border-border">
            <h3 className="font-display font-semibold text-lg text-foreground">
              Table 14.1.1: Summary of Demographic and Baseline Characteristics
            </h3>
            <p className="text-sm text-muted mt-1">
              Safety Population - Study ABC-123
            </p>
          </div>

          {/* Table content */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface">
                  <th className="px-4 py-3 text-left font-medium text-foreground border-b border-border">
                    Characteristic
                  </th>
                  <th className="px-4 py-3 text-center font-medium text-foreground border-b border-border">
                    Treatment<br />(N=225)
                  </th>
                  <th className="px-4 py-3 text-center font-medium text-foreground border-b border-border">
                    Placebo<br />(N=225)
                  </th>
                  <th className="px-4 py-3 text-center font-medium text-foreground border-b border-border">
                    Total<br />(N=450)
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border">
                  <td className="px-4 py-2 font-medium text-foreground" colSpan={4}>
                    Age (years)
                  </td>
                </tr>
                <tr className="border-b border-border hover:bg-surface/50">
                  <td className="px-4 py-2 pl-8 text-muted">Mean (SD)</td>
                  <td className="px-4 py-2 text-center">58.2 (11.8)</td>
                  <td className="px-4 py-2 text-center">58.4 (12.4)</td>
                  <td className="px-4 py-2 text-center">58.3 (12.1)</td>
                </tr>
                <tr className="border-b border-border hover:bg-surface/50">
                  <td className="px-4 py-2 pl-8 text-muted">Median (Min, Max)</td>
                  <td className="px-4 py-2 text-center">59.0 (28, 82)</td>
                  <td className="px-4 py-2 text-center">60.0 (25, 85)</td>
                  <td className="px-4 py-2 text-center">59.5 (25, 85)</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2 font-medium text-foreground" colSpan={4}>
                    Sex, n (%)
                  </td>
                </tr>
                <tr className="border-b border-border hover:bg-surface/50">
                  <td className="px-4 py-2 pl-8 text-muted">Male</td>
                  <td className="px-4 py-2 text-center">118 (52.4%)</td>
                  <td className="px-4 py-2 text-center">116 (51.6%)</td>
                  <td className="px-4 py-2 text-center">234 (52.0%)</td>
                </tr>
                <tr className="border-b border-border hover:bg-surface/50">
                  <td className="px-4 py-2 pl-8 text-muted">Female</td>
                  <td className="px-4 py-2 text-center">107 (47.6%)</td>
                  <td className="px-4 py-2 text-center">109 (48.4%)</td>
                  <td className="px-4 py-2 text-center">216 (48.0%)</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2 font-medium text-foreground" colSpan={4}>
                    Race, n (%)
                  </td>
                </tr>
                <tr className="border-b border-border hover:bg-surface/50">
                  <td className="px-4 py-2 pl-8 text-muted">White</td>
                  <td className="px-4 py-2 text-center">180 (80.0%)</td>
                  <td className="px-4 py-2 text-center">178 (79.1%)</td>
                  <td className="px-4 py-2 text-center">358 (79.6%)</td>
                </tr>
                <tr className="border-b border-border hover:bg-surface/50">
                  <td className="px-4 py-2 pl-8 text-muted">Black or African American</td>
                  <td className="px-4 py-2 text-center">28 (12.4%)</td>
                  <td className="px-4 py-2 text-center">32 (14.2%)</td>
                  <td className="px-4 py-2 text-center">60 (13.3%)</td>
                </tr>
                <tr className="hover:bg-surface/50">
                  <td className="px-4 py-2 pl-8 text-muted">Asian</td>
                  <td className="px-4 py-2 text-center">17 (7.6%)</td>
                  <td className="px-4 py-2 text-center">15 (6.7%)</td>
                  <td className="px-4 py-2 text-center">32 (7.1%)</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Table footer */}
          <div className="p-4 border-t border-border text-xs text-muted">
            <p>Source: ADSL dataset</p>
            <p>SD = Standard Deviation</p>
          </div>
        </div>
      </div>
    );
  }

  // Empty state for other tabs
  return (
    <div className="flex-1 bg-surface flex items-center justify-center">
      <div className="text-center animate-fade-in">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-border/50 flex items-center justify-center">
          <PlaceholderIcon size={32} className="text-muted" strokeWidth={1} />
        </div>
        <h3 className="font-display font-semibold text-lg text-foreground mb-2">
          {placeholder.title}
        </h3>
        <p className="text-sm text-muted max-w-xs mx-auto">
          {placeholder.description}
        </p>
        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-muted">
          <MousePointer size={14} />
          <span>Ask AI to generate content</span>
        </div>
      </div>
    </div>
  );
}
