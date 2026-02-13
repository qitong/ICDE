import { useApp } from '../../contexts/AppContext';
import { LineageGraph } from './LineageGraph';
import { DatasetMetaPanel } from './DatasetMetaPanel';
import { GitBranch } from 'lucide-react';

export function MetadataView() {
  const { state, viewDatasetMetadata } = useApp();
  const { metadataData, metadataLoading, selectedDatasetId, datasets } = state;

  // Find the selected dataset for the meta panel
  const selectedDataset = datasets.find(d => d.id === selectedDatasetId) ?? null;

  // Handle node click in the graph - navigate to that dataset's metadata
  const handleNodeClick = (datasetId: string) => {
    if (datasetId !== selectedDatasetId) {
      viewDatasetMetadata(datasetId);
    }
  };

  // Empty state when no dataset is selected
  if (!selectedDatasetId && !metadataLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-surface text-center p-8">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <GitBranch className="w-8 h-8 text-muted" />
        </div>
        <h3 className="text-lg font-semibold text-primary mb-2">No Dataset Selected</h3>
        <p className="text-muted text-sm max-w-md">
          Select a dataset from the sidebar to view its metadata and explore relationships
          between datasets.
        </p>
      </div>
    );
  }

  // Loading state
  if (metadataLoading) {
    return (
      <div className="h-full flex">
        {/* Graph loading skeleton */}
        <div className="flex-1 bg-surface flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-muted text-sm">Loading metadata...</p>
          </div>
        </div>
        {/* Meta panel loading skeleton */}
        <div className="w-80">
          <DatasetMetaPanel dataset={null} loading={true} />
        </div>
      </div>
    );
  }

  // Error state when metadata failed to load
  if (!metadataData) {
    return (
      <div className="h-full flex">
        <div className="flex-1 bg-surface flex items-center justify-center">
          <div className="text-center p-8">
            <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
              <GitBranch className="w-8 h-8 text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-primary mb-2">Failed to Load Metadata</h3>
            <p className="text-muted text-sm max-w-md">
              Unable to retrieve metadata for this dataset. Please try again.
            </p>
          </div>
        </div>
        <div className="w-80">
          <DatasetMetaPanel dataset={selectedDataset} />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Relationship Graph - takes remaining space */}
      <div className="flex-1 bg-surface overflow-hidden">
        <LineageGraph
          lineageData={metadataData}
          datasets={datasets}
          onNodeClick={handleNodeClick}
        />
      </div>

      {/* Meta Panel - fixed width sidebar */}
      <div className="w-80 flex-shrink-0">
        <DatasetMetaPanel dataset={selectedDataset} />
      </div>
    </div>
  );
}

// Export with legacy name for backward compatibility
export const LineageView = MetadataView;
