import { Database, FunctionSquare, AlertTriangle, Calendar, Hash, User, FileCode, Clock } from 'lucide-react';
import type { Dataset } from '../../types';

interface DatasetMetaPanelProps {
  dataset: Dataset | null;
  loading?: boolean;
}

export function DatasetMetaPanel({ dataset, loading }: DatasetMetaPanelProps) {
  if (loading) {
    return (
      <div className="h-full bg-white border-l border-border p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-3/4" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          <div className="space-y-3 mt-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="h-full bg-white border-l border-border p-6 flex items-center justify-center">
        <p className="text-muted text-sm">Select a dataset to view details</p>
      </div>
    );
  }

  const isRaw = dataset.type === 'RAW';
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="h-full bg-white border-l border-border overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3 mb-2">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              isRaw ? 'bg-blue-50' : 'bg-orange-50'
            }`}
          >
            {isRaw ? (
              <Database className="w-5 h-5 text-blue-500" />
            ) : (
              <FunctionSquare className="w-5 h-5 text-orange-500" />
            )}
          </div>
          <div>
            <h2 className="font-semibold text-primary text-lg">{dataset.name}</h2>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded ${
                isRaw
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-orange-100 text-orange-700'
              }`}
            >
              {dataset.type}
            </span>
          </div>
        </div>
        {dataset.description && (
          <p className="text-sm text-muted mt-3">{dataset.description}</p>
        )}
      </div>

      {/* Stale Warning */}
      {dataset.is_stale && (
        <div className="mx-6 mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-center gap-2 text-amber-700">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-medium">Dataset is stale</span>
          </div>
          {dataset.stale_reason && (
            <p className="text-xs text-amber-600 mt-1 ml-6">{dataset.stale_reason}</p>
          )}
        </div>
      )}

      {/* Basic Info Section */}
      <div className="p-6 border-b border-border">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-4">
          Basic Information
        </h3>
        <dl className="space-y-3">
          {dataset.crf_version && (
            <div className="flex items-center justify-between">
              <dt className="text-sm text-muted flex items-center gap-2">
                <Hash className="w-4 h-4" />
                CRF Version
              </dt>
              <dd className="text-sm font-medium">{dataset.crf_version}</dd>
            </div>
          )}
          {dataset.patient_id_column && (
            <div className="flex items-center justify-between">
              <dt className="text-sm text-muted flex items-center gap-2">
                <User className="w-4 h-4" />
                Patient ID Column
              </dt>
              <dd className="text-sm font-medium font-mono">{dataset.patient_id_column}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Statistics Section */}
      <div className="p-6 border-b border-border">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-4">
          Statistics
        </h3>
        <dl className="space-y-3">
          <div className="flex items-center justify-between">
            <dt className="text-sm text-muted">Rows</dt>
            <dd className="text-sm font-medium">
              {dataset.row_count?.toLocaleString() ?? 'N/A'}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-sm text-muted">Columns</dt>
            <dd className="text-sm font-medium">
              {dataset.column_count?.toLocaleString() ?? 'N/A'}
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-sm text-muted">Files</dt>
            <dd className="text-sm font-medium">{dataset.file_count}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-sm text-muted">Total Size</dt>
            <dd className="text-sm font-medium">{formatSize(dataset.total_size)}</dd>
          </div>
        </dl>
      </div>

      {/* Lineage Section */}
      <div className="p-6 border-b border-border">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-4">
          Lineage
        </h3>
        <dl className="space-y-3">
          {dataset.parent_dataset_id && (
            <div className="flex items-center justify-between">
              <dt className="text-sm text-muted">Version Parent</dt>
              <dd className="text-sm font-medium font-mono text-xs">
                {dataset.parent_dataset_id.slice(0, 8)}...
              </dd>
            </div>
          )}
          {dataset.source_dataset_id && (
            <div className="flex items-center justify-between">
              <dt className="text-sm text-muted">Source Dataset</dt>
              <dd className="text-sm font-medium font-mono text-xs">
                {dataset.source_dataset_id.slice(0, 8)}...
              </dd>
            </div>
          )}
          {dataset.script_id && (
            <div className="flex items-center justify-between">
              <dt className="text-sm text-muted flex items-center gap-2">
                <FileCode className="w-4 h-4" />
                Script
              </dt>
              <dd className="text-sm font-medium font-mono text-xs">
                {dataset.script_id.slice(0, 8)}...
              </dd>
            </div>
          )}
          {!dataset.parent_dataset_id && !dataset.source_dataset_id && (
            <p className="text-sm text-muted italic">No upstream lineage</p>
          )}
        </dl>
      </div>

      {/* Timestamps Section */}
      <div className="p-6">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-4">
          Timestamps
        </h3>
        <dl className="space-y-3">
          <div className="flex items-center justify-between">
            <dt className="text-sm text-muted flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Created
            </dt>
            <dd className="text-sm">{formatDate(dataset.created_at)}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-sm text-muted flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Updated
            </dt>
            <dd className="text-sm">{formatDate(dataset.updated_at)}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
