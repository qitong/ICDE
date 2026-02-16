import { MousePointer, FileText, GitBranch } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { MetadataView } from '../lineage';
import { ScriptView } from './ScriptView';
import { ScriptMetadataView } from './ScriptMetadataView';
import { FilePreviewView } from './FilePreviewView';

export function Canvas() {
  const { state } = useApp();
  const { activeTab, selectedScriptId, selectedFilePreview, selectedDatasetId } = state;

  // Content tab: render based on what's selected
  if (activeTab === 'content') {
    // Script selected → show code editor
    if (selectedScriptId) {
      return <ScriptView />;
    }

    // File selected → show file preview
    if (selectedFilePreview) {
      return <FilePreviewView />;
    }

    // Nothing selected → show welcome state
    return (
      <div className="flex-1 bg-surface flex items-center justify-center">
        <div className="text-center animate-fade-in">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-border/50 flex items-center justify-center">
            <FileText size={32} className="text-muted" strokeWidth={1} />
          </div>
          <h3 className="font-display font-semibold text-lg text-foreground mb-2">
            Content View
          </h3>
          <p className="text-sm text-muted max-w-xs mx-auto">
            Select a file or script from the sidebar to view its contents
          </p>
          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-muted">
            <MousePointer size={14} />
            <span>Click on an item in the sidebar</span>
          </div>
        </div>
      </div>
    );
  }

  // Metadata tab: render based on what's selected
  if (activeTab === 'metadata') {
    // Script selected → show script metadata
    if (selectedScriptId) {
      return <ScriptMetadataView />;
    }

    // Dataset or file selected → show dataset metadata (lineage)
    if (selectedDatasetId || selectedFilePreview) {
      return <MetadataView />;
    }

    // Nothing selected → show empty state
    return (
      <div className="flex-1 bg-surface flex items-center justify-center">
        <div className="text-center animate-fade-in">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-border/50 flex items-center justify-center">
            <GitBranch size={32} className="text-muted" strokeWidth={1} />
          </div>
          <h3 className="font-display font-semibold text-lg text-foreground mb-2">
            Metadata View
          </h3>
          <p className="text-sm text-muted max-w-xs mx-auto">
            Select a dataset or script to view its metadata and relationships
          </p>
          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-muted">
            <MousePointer size={14} />
            <span>Click on an item in the sidebar</span>
          </div>
        </div>
      </div>
    );
  }

  // Fallback (should not happen with current TabType)
  return (
    <div className="flex-1 bg-surface flex items-center justify-center">
      <div className="text-center">
        <p className="text-muted">Unknown tab type</p>
      </div>
    </div>
  );
}
