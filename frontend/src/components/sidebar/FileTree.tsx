import React from 'react';
import { FileItem } from './FileItem';
import { useApp } from '../../contexts/AppContext';
import { ChevronRight, ChevronDown, Database, FileSpreadsheet, Trash2 } from 'lucide-react';
import { api } from '../../services/api';
import type { Dataset } from '../../types';

function DatasetItem({ dataset, onDelete }: { dataset: Dataset; onDelete: () => void }) {
  const { state, toggleFolder } = useApp();
  const isExpanded = state.expandedFolders.has(`dataset-${dataset.id}`);

  const handleToggle = () => {
    toggleFolder(`dataset-${dataset.id}`);
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`Delete dataset "${dataset.name}"?`)) {
      try {
        await api.deleteDataset(dataset.id);
        onDelete();
      } catch (error) {
        console.error('Failed to delete dataset:', error);
      }
    }
  };

  return (
    <div>
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-2 px-2 py-1.5 text-left text-sm
          transition-colors duration-100 rounded-md text-foreground hover:bg-surface group"
        style={{ paddingLeft: '8px' }}
      >
        <span className="w-4 h-4 flex items-center justify-center text-muted">
          {isExpanded ? (
            <ChevronDown size={14} strokeWidth={2} />
          ) : (
            <ChevronRight size={14} strokeWidth={2} />
          )}
        </span>
        <Database size={16} strokeWidth={1.5} className="text-primary" />
        <span className="truncate flex-1">{dataset.name}</span>
        <span className="text-xs text-muted">{dataset.file_count}</span>
        <button
          onClick={handleDelete}
          className="p-1 opacity-0 group-hover:opacity-100 text-muted hover:text-error transition-all"
          title="Delete dataset"
        >
          <Trash2 size={14} />
        </button>
      </button>

      {isExpanded && dataset.files && dataset.files.length > 0 && (
        <div className="animate-fade-in">
          {dataset.files.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-2 px-2 py-1.5 text-sm text-foreground hover:bg-surface rounded-md"
              style={{ paddingLeft: '32px' }}
            >
              <span className="w-4" />
              <FileSpreadsheet size={16} strokeWidth={1.5} className="text-muted" />
              <span className="truncate flex-1">{file.original_name}</span>
              <span className="text-xs text-muted">
                {file.row_count ? `${file.row_count} rows` : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      {isExpanded && (!dataset.files || dataset.files.length === 0) && (
        <div className="px-2 py-1.5 text-sm text-muted" style={{ paddingLeft: '44px' }}>
          No files
        </div>
      )}
    </div>
  );
}

export function FileTree() {
  const { state, loadDatasets } = useApp();

  return (
    <div className="py-2">
      {/* Uploaded Datasets */}
      {state.datasets.length > 0 && (
        <div className="mb-2">
          <div className="px-3 py-1.5 text-xs font-medium text-muted uppercase tracking-wider">
            Uploaded Datasets
          </div>
          {state.datasets.map((dataset) => (
            <DatasetItem key={dataset.id} dataset={dataset} onDelete={loadDatasets} />
          ))}
        </div>
      )}

      {/* Original mock files */}
      {state.files.map((node) => (
        <FileItem key={node.id} node={node} />
      ))}
    </div>
  );
}
