import React, { useState } from 'react';
import { useApp } from '../../contexts/AppContext';
import {
  ChevronRight,
  ChevronDown,
  Database,
  FileSpreadsheet,
  Folder,
  FolderOpen,
  FileCode,
  GitFork,
  History,
  Clock,
  Plus,
} from 'lucide-react';
import type { Dataset, Script } from '../../types';
import { ScriptCreateModal } from '../modals';

// Depth constants for indentation
const INDENT_SIZE = 16;

interface TreeItemProps {
  depth: number;
  isExpanded?: boolean;
  isSelected?: boolean;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  onClick?: () => void;
  onToggle?: () => void;
  hasChildren?: boolean;
  className?: string;
}

function TreeItem({
  depth,
  isExpanded,
  isSelected,
  icon,
  label,
  badge,
  onClick,
  onToggle,
  hasChildren = true,
  className = '',
}: TreeItemProps) {
  const paddingLeft = 8 + depth * INDENT_SIZE;

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-2 py-1.5 text-left text-sm
        transition-colors duration-100 rounded-md group
        ${isSelected
          ? 'bg-primary/10 text-primary font-medium'
          : 'text-foreground hover:bg-surface'
        } ${className}`}
      style={{ paddingLeft }}
    >
      {hasChildren ? (
        <span
          className="w-4 h-4 flex items-center justify-center text-muted"
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
        >
          {isExpanded ? (
            <ChevronDown size={14} strokeWidth={2} />
          ) : (
            <ChevronRight size={14} strokeWidth={2} />
          )}
        </span>
      ) : (
        <span className="w-4" />
      )}
      {icon}
      <span className="truncate flex-1">{label}</span>
      {badge && <span className="text-xs text-muted">{badge}</span>}
    </button>
  );
}

// ============ Folder Category Components ============

interface FolderCategoryProps {
  folderId: string;
  label: string;
  icon: React.ReactNode;
  iconOpen: React.ReactNode;
  children: React.ReactNode;
  badge?: string;
  defaultExpanded?: boolean;
  onAdd?: () => void;
}

function FolderCategory({
  folderId,
  label,
  icon,
  iconOpen,
  children,
  badge,
  defaultExpanded = true,
  onAdd,
}: FolderCategoryProps) {
  const { state, toggleFolder } = useApp();

  // Initialize as expanded if not in set
  const isExpanded = state.expandedFolders.has(folderId) ||
    (!state.expandedFolders.has(`${folderId}-collapsed`) && defaultExpanded);

  const handleToggle = () => {
    toggleFolder(folderId);
    if (defaultExpanded && !state.expandedFolders.has(folderId)) {
      toggleFolder(`${folderId}-collapsed`);
    }
  };

  return (
    <div>
      <div className="flex items-center group">
        <div className="flex-1">
          <TreeItem
            depth={0}
            isExpanded={isExpanded}
            icon={isExpanded ? iconOpen : icon}
            label={label}
            badge={badge}
            onClick={handleToggle}
            onToggle={handleToggle}
            hasChildren={true}
          />
        </div>
        {onAdd && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAdd();
            }}
            className="p-1 mr-2 text-muted hover:text-primary hover:bg-primary/10 rounded transition-all"
            title={`Add new ${label.slice(0, -1)}`}
          >
            <Plus size={14} />
          </button>
        )}
      </div>
      {isExpanded && (
        <div className="animate-fade-in">
          {children}
        </div>
      )}
    </div>
  );
}

// ============ Dataset Components ============

interface SourceDatasetItemProps {
  dataset: Dataset;
  derivedDatasets: Dataset[];
  historicalVersions: Dataset[];
  depth: number;
}

function SourceDatasetItem({ dataset, derivedDatasets, historicalVersions, depth }: SourceDatasetItemProps) {
  const { state, toggleFolder, viewDatasetMetadata, viewFile } = useApp();
  const folderId = `source-dataset-${dataset.id}`;
  const isExpanded = state.expandedFolders.has(folderId);
  const isSelected = state.selectedDatasetId === dataset.id;
  const hasChildren = (dataset.files && dataset.files.length > 0) || derivedDatasets.length > 0 || historicalVersions.length > 0;

  const handleToggle = () => {
    toggleFolder(folderId);
  };

  const handleClick = () => {
    viewDatasetMetadata(dataset.id);
  };

  // Format version badge
  const versionBadge = dataset.version_name || 'current';

  return (
    <div>
      <TreeItem
        depth={depth}
        isExpanded={isExpanded}
        isSelected={isSelected}
        icon={
          <Database
            size={16}
            strokeWidth={1.5}
            className={isSelected ? 'text-primary' : 'text-blue-500'}
          />
        }
        label={dataset.name}
        badge={versionBadge}
        onClick={handleClick}
        onToggle={handleToggle}
        hasChildren={hasChildren}
      />

      {isExpanded && (
        <div className="animate-fade-in">
          {/* Dataset files */}
          {dataset.files && dataset.files.map((file) => (
            <button
              key={file.id}
              onClick={() => viewFile(dataset.id, file.id, file.original_name, file.file_type)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-foreground hover:bg-surface rounded-md cursor-pointer text-left"
              style={{ paddingLeft: 8 + (depth + 1) * INDENT_SIZE }}
            >
              <span className="w-4" />
              <FileSpreadsheet size={16} strokeWidth={1.5} className="text-green-600" />
              <span className="truncate flex-1 font-mono text-xs">{file.original_name}</span>
              <span className="text-xs text-muted">
                {file.row_count ? `${file.row_count} rows` : ''}
              </span>
            </button>
          ))}

          {/* Version history folder */}
          {historicalVersions.length > 0 && (
            <VersionHistoryFolder
              datasetId={dataset.id}
              versions={historicalVersions}
              depth={depth + 1}
            />
          )}

          {/* Derived datasets folder */}
          {derivedDatasets.length > 0 && (
            <DerivedDatasetsFolder
              sourceDatasetId={dataset.id}
              derivedDatasets={derivedDatasets}
              depth={depth + 1}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ============ Version History Components ============

interface VersionHistoryFolderProps {
  datasetId: string;
  versions: Dataset[];
  depth: number;
}

function VersionHistoryFolder({ datasetId, versions, depth }: VersionHistoryFolderProps) {
  const { state, toggleFolder } = useApp();
  const folderId = `history-folder-${datasetId}`;
  const isExpanded = state.expandedFolders.has(folderId);

  const handleToggle = () => {
    toggleFolder(folderId);
  };

  // Sort versions by created_at descending (newest first, but these are historical so oldest first)
  const sortedVersions = [...versions].sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div>
      <TreeItem
        depth={depth}
        isExpanded={isExpanded}
        icon={
          isExpanded ? (
            <History size={16} strokeWidth={1.5} className="text-gray-500" />
          ) : (
            <Clock size={16} strokeWidth={1.5} className="text-gray-500" />
          )
        }
        label="history"
        badge={`${versions.length}`}
        onClick={handleToggle}
        onToggle={handleToggle}
        hasChildren={true}
      />

      {isExpanded && (
        <div className="animate-fade-in">
          {sortedVersions.map((version) => (
            <HistoricalVersionItem key={version.id} dataset={version} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface HistoricalVersionItemProps {
  dataset: Dataset;
  depth: number;
}

function HistoricalVersionItem({ dataset, depth }: HistoricalVersionItemProps) {
  const { state, toggleFolder, viewDatasetMetadata, viewFile } = useApp();
  const folderId = `history-version-${dataset.id}`;
  const isExpanded = state.expandedFolders.has(folderId);
  const isSelected = state.selectedDatasetId === dataset.id;

  const handleToggle = () => {
    toggleFolder(folderId);
  };

  const handleClick = () => {
    viewDatasetMetadata(dataset.id);
  };

  // Format date for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const versionLabel = dataset.version_name || formatDate(dataset.created_at);

  return (
    <div>
      <TreeItem
        depth={depth}
        isExpanded={isExpanded}
        isSelected={isSelected}
        icon={
          <Database
            size={16}
            strokeWidth={1.5}
            className={isSelected ? 'text-primary' : 'text-gray-400'}
          />
        }
        label={versionLabel}
        badge={formatDate(dataset.created_at)}
        onClick={handleClick}
        onToggle={handleToggle}
        hasChildren={dataset.files && dataset.files.length > 0}
      />

      {isExpanded && dataset.files && (
        <div className="animate-fade-in">
          {dataset.files.map((file) => (
            <button
              key={file.id}
              onClick={() => viewFile(dataset.id, file.id, file.original_name, file.file_type)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-muted hover:bg-surface rounded-md cursor-pointer text-left"
              style={{ paddingLeft: 8 + (depth + 1) * INDENT_SIZE }}
            >
              <span className="w-4" />
              <FileSpreadsheet size={16} strokeWidth={1.5} className="text-gray-400" />
              <span className="truncate flex-1 font-mono text-xs">{file.original_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface DerivedDatasetsFolderProps {
  sourceDatasetId: string;
  derivedDatasets: Dataset[];
  depth: number;
}

function DerivedDatasetsFolder({ sourceDatasetId, derivedDatasets, depth }: DerivedDatasetsFolderProps) {
  const { state, toggleFolder } = useApp();
  const folderId = `derived-folder-${sourceDatasetId}`;
  const isExpanded = state.expandedFolders.has(folderId);

  const handleToggle = () => {
    toggleFolder(folderId);
  };

  return (
    <div>
      <TreeItem
        depth={depth}
        isExpanded={isExpanded}
        icon={
          isExpanded ? (
            <FolderOpen size={16} strokeWidth={1.5} className="text-purple-500" />
          ) : (
            <Folder size={16} strokeWidth={1.5} className="text-purple-500" />
          )
        }
        label="derived"
        badge={`${derivedDatasets.length}`}
        onClick={handleToggle}
        onToggle={handleToggle}
        hasChildren={true}
      />

      {isExpanded && (
        <div className="animate-fade-in">
          {derivedDatasets.map((derived) => (
            <DerivedDatasetItem key={derived.id} dataset={derived} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface DerivedDatasetItemProps {
  dataset: Dataset;
  depth: number;
}

function DerivedDatasetItem({ dataset, depth }: DerivedDatasetItemProps) {
  const { state, toggleFolder, viewDatasetMetadata, viewFile } = useApp();
  const folderId = `derived-dataset-${dataset.id}`;
  const isExpanded = state.expandedFolders.has(folderId);
  const isSelected = state.selectedDatasetId === dataset.id;

  const handleToggle = () => {
    toggleFolder(folderId);
  };

  const handleClick = () => {
    viewDatasetMetadata(dataset.id);
  };

  // Determine the badge - show "Manual" for manual uploads, otherwise show nothing
  const getBadge = () => {
    if (dataset.is_manual) {
      return 'Manual';
    }
    return undefined;
  };

  return (
    <div>
      <TreeItem
        depth={depth}
        isExpanded={isExpanded}
        isSelected={isSelected}
        icon={
          <GitFork
            size={16}
            strokeWidth={1.5}
            className={isSelected ? 'text-primary' : 'text-purple-500'}
          />
        }
        label={dataset.name}
        badge={getBadge()}
        onClick={handleClick}
        onToggle={handleToggle}
        hasChildren={dataset.files && dataset.files.length > 0}
      />

      {isExpanded && dataset.files && (
        <div className="animate-fade-in">
          {dataset.files.map((file) => (
            <button
              key={file.id}
              onClick={() => viewFile(dataset.id, file.id, file.original_name, file.file_type)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-foreground hover:bg-surface rounded-md cursor-pointer text-left"
              style={{ paddingLeft: 8 + (depth + 1) * INDENT_SIZE }}
            >
              <span className="w-4" />
              <FileSpreadsheet size={16} strokeWidth={1.5} className="text-green-600" />
              <span className="truncate flex-1 font-mono text-xs">{file.original_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ============ Script Components ============

interface ScriptItemProps {
  script: Script;
  depth: number;
}

function ScriptItem({ script, depth }: ScriptItemProps) {
  const { state, viewScript } = useApp();
  const isSelected = state.selectedScriptId === script.id;

  const handleClick = () => {
    viewScript(script.id);
  };

  // Get file extension based on language
  const getExtension = (lang: string) => {
    switch (lang.toLowerCase()) {
      case 'python': return '.py';
      case 'r': return '.R';
      case 'sas': return '.sas';
      case 'sql': return '.sql';
      default: return '.py';
    }
  };

  return (
    <TreeItem
      depth={depth}
      isSelected={isSelected}
      icon={
        <FileCode
          size={16}
          strokeWidth={1.5}
          className={isSelected ? 'text-primary' : 'text-yellow-600'}
        />
      }
      label={`${script.name}${getExtension(script.language)}`}
      onClick={handleClick}
      hasChildren={false}
    />
  );
}

// ============ Main FileTree Component ============

export function FileTree() {
  const { state } = useApp();
  const { datasets, scripts } = state;
  const [showScriptModal, setShowScriptModal] = useState(false);

  // Separate source datasets (RAW without source_dataset_id) from derived
  const allSourceDatasets = datasets.filter(d => d.type === 'RAW' && !d.source_dataset_id);
  const derivedDatasets = datasets.filter(d => d.type === 'DERIVED' || d.source_dataset_id);

  // Find IDs of datasets that are parents of other datasets (historical versions)
  const parentIds = new Set(
    allSourceDatasets
      .filter(d => d.parent_dataset_id)
      .map(d => d.parent_dataset_id as string)
  );

  // Current versions = source datasets that are NOT a parent of any other dataset
  const currentVersions = allSourceDatasets.filter(d => !parentIds.has(d.id));

  // Build version history for each current version by tracing parent_dataset_id chain
  const getVersionHistory = (currentDataset: Dataset): Dataset[] => {
    const history: Dataset[] = [];
    let parentId = currentDataset.parent_dataset_id;

    while (parentId) {
      const parent = allSourceDatasets.find(d => d.id === parentId);
      if (parent) {
        history.push(parent);
        parentId = parent.parent_dataset_id;
      } else {
        break;
      }
    }

    return history;
  };

  // Group derived datasets by their source (including all versions)
  const getDerivedForDataset = (datasetId: string, versionHistory: Dataset[]): Dataset[] => {
    const allVersionIds = [datasetId, ...versionHistory.map(v => v.id)];
    return derivedDatasets.filter(d => d.source_dataset_id && allVersionIds.includes(d.source_dataset_id));
  };

  // Datasets that are derived but their source is not in our list (orphaned)
  const allSourceIds = new Set(allSourceDatasets.map(d => d.id));
  const orphanedDerived = derivedDatasets.filter(d =>
    d.source_dataset_id && !allSourceIds.has(d.source_dataset_id)
  );

  // Count unique dataset names (for badge)
  const uniqueDatasetCount = currentVersions.length + orphanedDerived.length;

  return (
    <div className="py-2">
      {/* datasets/ folder */}
      <FolderCategory
        folderId="folder-datasets"
        label="datasets"
        icon={<Folder size={16} strokeWidth={1.5} className="text-blue-500" />}
        iconOpen={<FolderOpen size={16} strokeWidth={1.5} className="text-blue-500" />}
        badge={`${uniqueDatasetCount}`}
        defaultExpanded={true}
      >
        {currentVersions.length === 0 && orphanedDerived.length === 0 ? (
          <div className="px-3 py-2 text-xs text-muted italic" style={{ paddingLeft: 8 + INDENT_SIZE }}>
            No datasets yet
          </div>
        ) : (
          <>
            {currentVersions.map((dataset) => {
              const versionHistory = getVersionHistory(dataset);
              return (
                <SourceDatasetItem
                  key={dataset.id}
                  dataset={dataset}
                  derivedDatasets={getDerivedForDataset(dataset.id, versionHistory)}
                  historicalVersions={versionHistory}
                  depth={1}
                />
              );
            })}
            {orphanedDerived.map((dataset) => (
              <DerivedDatasetItem
                key={dataset.id}
                dataset={dataset}
                depth={1}
              />
            ))}
          </>
        )}
      </FolderCategory>

      {/* scripts/ folder */}
      <FolderCategory
        folderId="folder-scripts"
        label="scripts"
        icon={<Folder size={16} strokeWidth={1.5} className="text-yellow-600" />}
        iconOpen={<FolderOpen size={16} strokeWidth={1.5} className="text-yellow-600" />}
        badge={`${scripts.length}`}
        defaultExpanded={true}
        onAdd={() => setShowScriptModal(true)}
      >
        {scripts.length === 0 ? (
          <div className="px-3 py-2 text-xs text-muted italic" style={{ paddingLeft: 8 + INDENT_SIZE }}>
            No scripts yet
          </div>
        ) : (
          scripts.map((script) => (
            <ScriptItem key={script.id} script={script} depth={1} />
          ))
        )}
      </FolderCategory>

      {/* references/ folder */}
      <FolderCategory
        folderId="folder-references"
        label="references"
        icon={<Folder size={16} strokeWidth={1.5} className="text-orange-500" />}
        iconOpen={<FolderOpen size={16} strokeWidth={1.5} className="text-orange-500" />}
        defaultExpanded={false}
      >
        <div className="px-3 py-2 text-xs text-muted italic" style={{ paddingLeft: 8 + INDENT_SIZE }}>
          No references yet
        </div>
      </FolderCategory>

      {/* reports/ folder */}
      <FolderCategory
        folderId="folder-reports"
        label="reports"
        icon={<Folder size={16} strokeWidth={1.5} className="text-red-500" />}
        iconOpen={<FolderOpen size={16} strokeWidth={1.5} className="text-red-500" />}
        defaultExpanded={false}
      >
        <div className="px-3 py-2 text-xs text-muted italic" style={{ paddingLeft: 8 + INDENT_SIZE }}>
          No reports yet
        </div>
      </FolderCategory>

      {/* Script Create Modal */}
      <ScriptCreateModal
        isOpen={showScriptModal}
        onClose={() => setShowScriptModal(false)}
      />
    </div>
  );
}
