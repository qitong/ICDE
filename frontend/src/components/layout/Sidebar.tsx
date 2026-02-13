import { useRef, useEffect, useCallback } from 'react';
import { FileTree } from '../sidebar/FileTree';
import { Search, Upload, PanelLeftClose, PanelLeft } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';

const MIN_WIDTH = 200;
const MAX_WIDTH = 600;

export function Sidebar() {
  const { state, toggleSidebar, setSidebarWidth, openUploadModal } = useApp();
  const isCollapsed = state.sidebarCollapsed;
  const sidebarRef = useRef<HTMLElement>(null);
  const isResizingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    startXRef.current = e.clientX;
    startWidthRef.current = state.sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [state.sidebarWidth]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return;

      const delta = e.clientX - startXRef.current;
      const newWidth = Math.min(Math.max(startWidthRef.current + delta, MIN_WIDTH), MAX_WIDTH);
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      if (isResizingRef.current) {
        isResizingRef.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [setSidebarWidth]);

  // Collapsed state - just show toggle button
  if (isCollapsed) {
    return (
      <aside className="w-12 h-full bg-background border-r border-border flex flex-col items-center py-3 transition-all duration-200">
        <button
          onClick={toggleSidebar}
          className="p-2 text-muted hover:text-foreground hover:bg-surface rounded-lg transition-colors"
          title="Expand sidebar"
        >
          <PanelLeft size={18} />
        </button>
      </aside>
    );
  }

  // Expanded state
  return (
    <aside
      ref={sidebarRef}
      style={{ width: state.sidebarWidth }}
      className="relative h-full bg-background border-r border-border flex flex-col"
    >
      {/* Header with collapse button */}
      <div className="h-10 px-2 flex items-center justify-between border-b border-border">
        <span className="text-xs font-medium text-muted uppercase tracking-wider pl-1">
          Explorer
        </span>
        <button
          onClick={toggleSidebar}
          className="p-1.5 text-muted hover:text-foreground hover:bg-surface rounded-md transition-colors"
          title="Collapse sidebar"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* Search bar */}
      <div className="p-3 border-b border-border">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            type="text"
            placeholder="Search files..."
            className="
              w-full h-8 pl-8 pr-3 text-sm
              bg-surface border border-border rounded-md
              placeholder:text-muted
              focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20
              transition-all duration-150
            "
          />
        </div>
      </div>

      {/* File tree */}
      <div className="flex-1 overflow-y-auto">
        <FileTree />
      </div>

      {/* Upload dataset button */}
      <div className="p-3 border-t border-border">
        <button
          onClick={openUploadModal}
          className="
            w-full h-9 flex items-center justify-center gap-2
            text-sm font-medium text-primary
            bg-primary/10 border border-primary/20 rounded-md
            hover:bg-primary/20 hover:border-primary/30
            transition-colors duration-150
          "
        >
          <Upload size={16} />
          <span>Upload Dataset</span>
        </button>
      </div>

      {/* Resize handle */}
      <div
        onMouseDown={handleMouseDown}
        className="
          absolute top-0 right-0 w-1 h-full cursor-col-resize
          hover:bg-primary/50 active:bg-primary/70
          transition-colors duration-150
        "
      />
    </aside>
  );
}
