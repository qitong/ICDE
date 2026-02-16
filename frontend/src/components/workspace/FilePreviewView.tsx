import { useApp } from '../../contexts/AppContext';
import {
  FileSpreadsheet,
  FileText,
  File,
  Download,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { useState } from 'react';
import { api } from '../../services/api';

export function FilePreviewView() {
  const { state, viewFile } = useApp();
  const { selectedFilePreview, filePreviewData, filePreviewLoading } = state;

  const [currentPage, setCurrentPage] = useState(0);
  const [isReparsing, setIsReparsing] = useState(false);
  const rowsPerPage = 50;

  const handleReparse = async () => {
    if (!selectedFilePreview) return;

    setIsReparsing(true);
    try {
      // Re-parse the file on the backend
      await api.reparseFile(selectedFilePreview.datasetId, selectedFilePreview.fileId);
      // Reload the file preview
      await viewFile(
        selectedFilePreview.datasetId,
        selectedFilePreview.fileId,
        selectedFilePreview.fileName,
        selectedFilePreview.fileType
      );
    } catch (error) {
      console.error('Failed to reparse file:', error);
    } finally {
      setIsReparsing(false);
    }
  };

  // Empty state when no file is selected
  if (!selectedFilePreview) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-surface text-center p-8">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <File className="w-8 h-8 text-muted" />
        </div>
        <h3 className="text-lg font-semibold text-primary mb-2">No File Selected</h3>
        <p className="text-muted text-sm max-w-md">
          Select a file from the sidebar to view its contents.
        </p>
      </div>
    );
  }

  const { fileName, fileType } = selectedFilePreview;
  const isTabular = ['xlsx', 'xls', 'csv'].includes(fileType.toLowerCase());

  // Get file icon based on type
  const getFileIcon = () => {
    const type = fileType.toLowerCase();
    if (['xlsx', 'xls', 'csv'].includes(type)) {
      return <FileSpreadsheet size={18} className="text-green-600" />;
    }
    if (['md', 'txt'].includes(type)) {
      return <FileText size={18} className="text-blue-500" />;
    }
    if (type === 'pdf') {
      return <File size={18} className="text-red-500" />;
    }
    return <File size={18} className="text-gray-500" />;
  };

  // Loading state
  if (filePreviewLoading) {
    return (
      <div className="h-full flex flex-col bg-background">
        {/* File header */}
        <div className="flex-shrink-0 bg-surface border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            {getFileIcon()}
            <span className="text-sm font-medium text-foreground">{fileName}</span>
            <span className="text-xs text-muted px-2 py-0.5 bg-gray-100 rounded uppercase">
              {fileType}
            </span>
          </div>
        </div>

        {/* Loading spinner */}
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
            <span className="text-sm text-muted">Loading file preview...</span>
          </div>
        </div>
      </div>
    );
  }

  // Non-tabular file types
  if (!isTabular) {
    return (
      <div className="h-full flex flex-col bg-background">
        {/* File header */}
        <div className="flex-shrink-0 bg-surface border-b border-border px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getFileIcon()}
              <span className="text-sm font-medium text-foreground">{fileName}</span>
              <span className="text-xs text-muted px-2 py-0.5 bg-gray-100 rounded uppercase">
                {fileType}
              </span>
            </div>
            <button
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted hover:text-foreground hover:bg-gray-100 rounded transition-colors"
              title="Download file"
            >
              <Download size={14} />
              Download
            </button>
          </div>
        </div>

        {/* Non-tabular content message */}
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
          <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center mb-4">
            {fileType.toLowerCase() === 'pdf' ? (
              <File className="w-10 h-10 text-red-500" />
            ) : fileType.toLowerCase() === 'md' ? (
              <FileText className="w-10 h-10 text-blue-500" />
            ) : (
              <File className="w-10 h-10 text-gray-400" />
            )}
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Preview not available
          </h3>
          <p className="text-muted text-sm max-w-md mb-4">
            {fileType.toLowerCase() === 'pdf'
              ? 'PDF preview is coming soon. You can download the file to view it.'
              : fileType.toLowerCase() === 'md'
              ? 'Markdown preview is coming soon. You can download the file to view it.'
              : `File type "${fileType}" cannot be previewed directly. You can download the file to view it.`}
          </p>
          <button className="flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary/90 transition-colors">
            <Download size={16} />
            Download File
          </button>
        </div>
      </div>
    );
  }

  // No preview data (error case)
  if (!filePreviewData) {
    return (
      <div className="h-full flex flex-col bg-background">
        {/* File header */}
        <div className="flex-shrink-0 bg-surface border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            {getFileIcon()}
            <span className="text-sm font-medium text-foreground">{fileName}</span>
            <span className="text-xs text-muted px-2 py-0.5 bg-gray-100 rounded uppercase">
              {fileType}
            </span>
          </div>
        </div>

        {/* Error state */}
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Failed to Load Preview
          </h3>
          <p className="text-muted text-sm max-w-md mb-4">
            There was an error loading the file preview. The file may need to be re-parsed.
          </p>
          <button
            onClick={handleReparse}
            disabled={isReparsing}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isReparsing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Re-parsing...
              </>
            ) : (
              <>
                <RefreshCw size={16} />
                Retry
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // Tabular data preview
  const { columns, sample_rows, row_count, column_count } = filePreviewData;
  const totalPages = Math.ceil(sample_rows.length / rowsPerPage);
  const startRow = currentPage * rowsPerPage;
  const endRow = Math.min(startRow + rowsPerPage, sample_rows.length);
  const visibleRows = sample_rows.slice(startRow, endRow);

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">
      {/* File header */}
      <div className="flex-shrink-0 bg-surface border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {getFileIcon()}
              <span className="text-sm font-medium text-foreground">{fileName}</span>
            </div>
            <span className="text-xs text-muted px-2 py-0.5 bg-gray-100 rounded uppercase">
              {fileType}
            </span>
            <span className="text-xs text-muted">
              {row_count.toLocaleString()} rows &times; {column_count} columns
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted hover:text-foreground hover:bg-gray-100 rounded transition-colors"
              title="Download file"
            >
              <Download size={14} />
              Download
            </button>
          </div>
        </div>

        {/* Column summary */}
        <div className="mt-2 flex items-center gap-1 flex-wrap">
          {columns.slice(0, 10).map((col, i) => (
            <span
              key={i}
              className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
              title={`${col.name}: ${col.data_type}`}
            >
              {col.name}
            </span>
          ))}
          {columns.length > 10 && (
            <span className="text-xs text-muted">
              +{columns.length - 10} more
            </span>
          )}
        </div>
      </div>

      {/* Table content */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="bg-gray-100">
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 border-b border-r border-gray-200 bg-gray-50 w-12">
                #
              </th>
              {columns.map((col, i) => (
                <th
                  key={i}
                  className="px-3 py-2 text-left text-xs font-medium text-gray-700 border-b border-r border-gray-200 bg-gray-100 whitespace-nowrap"
                  title={`Type: ${col.data_type} | ${col.non_null_count} non-null | ${col.unique_count} unique`}
                >
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold">{col.name}</span>
                    <span className="font-normal text-gray-400 text-[10px]">
                      {col.data_type}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className="hover:bg-blue-50/50 border-b border-gray-100"
              >
                <td className="px-3 py-1.5 text-xs text-gray-400 border-r border-gray-100 bg-gray-50/50 font-mono">
                  {startRow + rowIdx + 1}
                </td>
                {columns.map((col, colIdx) => {
                  const value = row[col.name];
                  const displayValue =
                    value === null || value === undefined
                      ? ''
                      : String(value);

                  return (
                    <td
                      key={colIdx}
                      className="px-3 py-1.5 text-xs text-gray-700 border-r border-gray-100 max-w-xs truncate"
                      title={displayValue}
                    >
                      {displayValue === '' ? (
                        <span className="text-gray-300 italic">null</span>
                      ) : (
                        displayValue
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination bar */}
      <div className="flex-shrink-0 h-8 bg-gray-100 border-t border-border flex items-center justify-between px-4 text-xs text-muted">
        <span>
          Showing rows {startRow + 1} - {endRow} of {sample_rows.length} (preview)
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
            disabled={currentPage === 0}
            className="p-1 hover:bg-gray-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={14} />
          </button>
          <span>
            Page {currentPage + 1} of {totalPages || 1}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={currentPage >= totalPages - 1}
            className="p-1 hover:bg-gray-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
