
import { BarChart3, Table2, FileText, Code } from 'lucide-react';
import type { TabType } from '../../types';
import { useApp } from '../../contexts/AppContext';

const tabs: { type: TabType; label: string; icon: typeof BarChart3 }[] = [
  { type: 'chart', label: 'Chart', icon: BarChart3 },
  { type: 'table', label: 'Table', icon: Table2 },
  { type: 'text', label: 'Text', icon: FileText },
  { type: 'code', label: 'Code', icon: Code },
];

export function TabBar() {
  const { state, setActiveTab } = useApp();

  return (
    <div className="h-[44px] border-b border-border bg-background flex items-center px-2 gap-1">
      {tabs.map((tab) => {
        const isActive = state.activeTab === tab.type;
        const TabIcon = tab.icon;

        return (
          <button
            key={tab.type}
            onClick={() => setActiveTab(tab.type)}
            className={`
              h-8 px-3 flex items-center gap-2 rounded-md text-sm font-medium
              transition-all duration-150
              ${isActive
                ? 'bg-primary text-white'
                : 'text-muted hover:text-foreground hover:bg-surface'
              }
            `}
          >
            <TabIcon size={16} strokeWidth={1.5} />
            <span>{tab.label}</span>
          </button>
        );
      })}

      {/* Spacer */}
      <div className="flex-1" />

      {/* View controls placeholder */}
      <div className="flex items-center gap-2 text-xs text-muted">
        <span>Zoom: 100%</span>
      </div>
    </div>
  );
}
