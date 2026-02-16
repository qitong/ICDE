import { useState, useEffect } from 'react';
import { X, Database, GitFork, History, Link2Off, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import type { Dataset, RelationshipType, SetRelationshipRequest } from '../../types';

interface DatasetRelationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
  dataset: Dataset | null;
  allDatasets: Dataset[];
}

export function DatasetRelationModal({
  isOpen,
  onClose,
  onComplete,
  dataset,
  allDatasets,
}: DatasetRelationModalProps) {
  const [relationshipType, setRelationshipType] = useState<RelationshipType>('none');
  const [parentDatasetId, setParentDatasetId] = useState<string>('');
  const [sourceDatasetId, setSourceDatasetId] = useState<string>('');
  const [versionName, setVersionName] = useState<string>('');
  const [_derivedName, _setDerivedName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get available datasets for selection (exclude current dataset)
  const availableDatasets = allDatasets.filter(d =>
    d.id !== dataset?.id && d.type === 'RAW'
  );

  // Reset form when modal opens with new dataset
  useEffect(() => {
    if (isOpen && dataset) {
      setRelationshipType('none');
      setParentDatasetId('');
      setSourceDatasetId('');
      setVersionName('');
      _setDerivedName(dataset.name);
      setDescription(dataset.description || '');
      setError(null);
    }
  }, [isOpen, dataset]);

  const handleSubmit = async () => {
    if (!dataset) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const request: SetRelationshipRequest = {
        relationship_type: relationshipType,
      };

      if (relationshipType === 'version') {
        if (!parentDatasetId) {
          setError('Please select a parent dataset');
          setIsSubmitting(false);
          return;
        }
        request.parent_dataset_id = parentDatasetId;
        request.version_name = versionName || undefined;
      } else if (relationshipType === 'derived') {
        if (!sourceDatasetId) {
          setError('Please select a source dataset');
          setIsSubmitting(false);
          return;
        }
        request.source_dataset_id = sourceDatasetId;
        request.is_manual = true; // Manual upload
      }

      if (description) {
        request.description = description;
      }

      await api.setDatasetRelationship(dataset.id, request);
      onComplete();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set relationship');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen || !dataset) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Database className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Set Dataset Relationship</h2>
              <p className="text-sm text-gray-500">{dataset.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="space-y-5">
            {/* Relationship Type Selection */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                This dataset is:
              </label>

              {/* Option: None */}
              <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input
                  type="radio"
                  name="relationshipType"
                  value="none"
                  checked={relationshipType === 'none'}
                  onChange={() => setRelationshipType('none')}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Link2Off size={16} className="text-gray-500" />
                    <span className="font-medium text-gray-900">New dataset (no relationship)</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    This is a standalone dataset with no connection to existing data
                  </p>
                </div>
              </label>

              {/* Option: Version */}
              <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input
                  type="radio"
                  name="relationshipType"
                  value="version"
                  checked={relationshipType === 'version'}
                  onChange={() => setRelationshipType('version')}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <History size={16} className="text-blue-500" />
                    <span className="font-medium text-gray-900">New version of existing dataset</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    This is an updated version (e.g., ADSL v2.0 to v2.1)
                  </p>
                </div>
              </label>

              {/* Version Options */}
              {relationshipType === 'version' && (
                <div className="ml-7 pl-4 border-l-2 border-blue-200 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Parent Dataset <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={parentDatasetId}
                      onChange={(e) => setParentDatasetId(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm"
                    >
                      <option value="">Select parent dataset...</option>
                      {availableDatasets.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} {d.version_name ? `(${d.version_name})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Version Name
                    </label>
                    <input
                      type="text"
                      value={versionName}
                      onChange={(e) => setVersionName(e.target.value)}
                      placeholder="e.g., v2.1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm"
                    />
                  </div>
                </div>
              )}

              {/* Option: Derived */}
              <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                <input
                  type="radio"
                  name="relationshipType"
                  value="derived"
                  checked={relationshipType === 'derived'}
                  onChange={() => setRelationshipType('derived')}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <GitFork size={16} className="text-purple-500" />
                    <span className="font-medium text-gray-900">Derived dataset (manual upload)</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Analysis subset derived from a source (e.g., FAS, PPS, SAS)
                  </p>
                </div>
              </label>

              {/* Derived Options */}
              {relationshipType === 'derived' && (
                <div className="ml-7 pl-4 border-l-2 border-purple-200 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Source Dataset <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={sourceDatasetId}
                      onChange={(e) => setSourceDatasetId(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm"
                    >
                      <option value="">Select source dataset...</option>
                      {availableDatasets.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} {d.version_name ? `(${d.version_name})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Description
                    </label>
                    <input
                      type="text"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="e.g., Full Analysis Set"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm"
                    />
                  </div>
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <p className="text-sm text-purple-700">
                      This dataset will be marked as <strong>"Manual Upload"</strong> since it was uploaded directly rather than generated by a script.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg">
                <AlertCircle size={16} />
                <span className="text-sm">{error}</span>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Skip
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving...
              </>
            ) : (
              'Confirm'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
