import React, { useEffect, useRef } from 'react';
import { Database, FileText, Code, Folder, X } from 'lucide-react';
import type { MentionableItem, MentionRef } from '../../types';

interface MentionDropdownProps {
  isOpen: boolean;
  query: string;
  items: MentionableItem[];
  loading: boolean;
  position: { top: number; left: number };
  selectedIndex: number;
  onSelect: (item: MentionableItem) => void;
  onClose: () => void;
}

export function MentionDropdown({
  isOpen,
  query,
  items,
  loading,
  position,
  selectedIndex,
  onSelect,
  onClose,
}: MentionDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getIcon = (type: string) => {
    switch (type) {
      case 'dataset':
        return <Database size={14} className="text-primary" />;
      case 'file':
        return <FileText size={14} className="text-success" />;
      case 'script':
        return <Code size={14} className="text-warning" />;
      default:
        return <Folder size={14} className="text-muted" />;
    }
  };

  const groupedItems = {
    datasets: items.filter((i) => i.type === 'dataset'),
    files: items.filter((i) => i.type === 'file'),
    scripts: items.filter((i) => i.type === 'script'),
  };

  const hasResults = items.length > 0;

  return (
    <div
      ref={dropdownRef}
      className="absolute z-50 bg-background border border-border rounded-lg shadow-lg max-h-[280px] overflow-y-auto min-w-[280px] max-w-[360px]"
      style={{
        bottom: position.top,
        left: position.left,
      }}
    >
      {/* Header */}
      <div className="sticky top-0 bg-background border-b border-border px-3 py-2 flex items-center justify-between">
        <span className="text-xs font-medium text-muted">
          {query ? `Searching "${query}"` : 'Reference files with @'}
        </span>
        <button
          onClick={onClose}
          className="p-1 hover:bg-surface rounded text-muted hover:text-foreground"
        >
          <X size={12} />
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="px-3 py-4 text-center text-sm text-muted">
          <div className="animate-pulse">Loading...</div>
        </div>
      )}

      {/* No results */}
      {!loading && !hasResults && (
        <div className="px-3 py-4 text-center text-sm text-muted">
          No files found
        </div>
      )}

      {/* Results */}
      {!loading && hasResults && (
        <div className="py-1">
          {/* Datasets */}
          {groupedItems.datasets.length > 0 && (
            <div>
              <div className="px-3 py-1 text-xs font-medium text-muted uppercase tracking-wider flex items-center gap-1.5">
                <Database size={12} />
                Datasets
              </div>
              {groupedItems.datasets.map((item, index) => (
                <MentionItem
                  key={item.id}
                  item={item}
                  icon={getIcon(item.type)}
                  isSelected={selectedIndex === index}
                  onSelect={onSelect}
                />
              ))}
            </div>
          )}

          {/* Files */}
          {groupedItems.files.length > 0 && (
            <div>
              <div className="px-3 py-1 text-xs font-medium text-muted uppercase tracking-wider flex items-center gap-1.5 mt-1">
                <FileText size={12} />
                Files
              </div>
              {groupedItems.files.map((item, index) => (
                <MentionItem
                  key={item.id}
                  item={item}
                  icon={getIcon(item.type)}
                  isSelected={selectedIndex === groupedItems.datasets.length + index}
                  onSelect={onSelect}
                />
              ))}
            </div>
          )}

          {/* Scripts */}
          {groupedItems.scripts.length > 0 && (
            <div>
              <div className="px-3 py-1 text-xs font-medium text-muted uppercase tracking-wider flex items-center gap-1.5 mt-1">
                <Code size={12} />
                Scripts
              </div>
              {groupedItems.scripts.map((item, index) => (
                <MentionItem
                  key={item.id}
                  item={item}
                  icon={getIcon(item.type)}
                  isSelected={
                    selectedIndex ===
                    groupedItems.datasets.length + groupedItems.files.length + index
                  }
                  onSelect={onSelect}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface MentionItemProps {
  item: MentionableItem;
  icon: React.ReactNode;
  isSelected: boolean;
  onSelect: (item: MentionableItem) => void;
}

function MentionItem({ item, icon, isSelected, onSelect }: MentionItemProps) {
  return (
    <button
      onClick={() => onSelect(item)}
      className={`
        w-full px-3 py-2 flex items-start gap-2 text-left
        hover:bg-surface transition-colors
        ${isSelected ? 'bg-primary/10' : ''}
      `}
    >
      <span className="mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-foreground truncate">{item.name}</div>
        <div className="text-xs text-muted truncate">{item.path}</div>
        {item.metadata && (
          <div className="text-xs text-muted mt-0.5">
            {item.metadata.row_count && `${item.metadata.row_count} rows`}
            {item.metadata.row_count && item.metadata.column_count && ' · '}
            {item.metadata.column_count && `${item.metadata.column_count} cols`}
            {item.metadata.description && (
              <span className="ml-2">{item.metadata.description.slice(0, 40)}...</span>
            )}
          </div>
        )}
      </div>
    </button>
  );
}

// Mention tag component for displaying selected mentions
interface MentionTagProps {
  mention: MentionRef;
  onRemove: () => void;
}

export function MentionTag({ mention, onRemove }: MentionTagProps) {
  const getIcon = () => {
    switch (mention.type) {
      case 'dataset':
        return <Database size={12} />;
      case 'file':
        return <FileText size={12} />;
      case 'script':
        return <Code size={12} />;
      default:
        return <Folder size={12} />;
    }
  };

  const getColor = () => {
    switch (mention.type) {
      case 'dataset':
        return 'bg-primary/10 text-primary border-primary/20';
      case 'file':
        return 'bg-success/10 text-success border-success/20';
      case 'script':
        return 'bg-warning/10 text-warning border-warning/20';
      default:
        return 'bg-surface text-foreground border-border';
    }
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2 py-0.5 rounded-full
        text-xs font-medium border ${getColor()}
      `}
    >
      {getIcon()}
      <span className="max-w-[100px] truncate">{mention.name || mention.path}</span>
      <button
        onClick={onRemove}
        className="ml-0.5 hover:opacity-70"
        title="Remove reference"
      >
        <X size={10} />
      </button>
    </span>
  );
}
