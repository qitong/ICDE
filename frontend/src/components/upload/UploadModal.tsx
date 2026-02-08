import React, { useState, useRef, useCallback } from 'react';
import { X, Upload, FileSpreadsheet, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { TablePreview } from './TablePreview';
import type { DatasetFile, ColumnInfo } from '../../types';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: () => void;
}

interface FileWithPreview {
  file: File;
  uploaded?: DatasetFile;
  columns?: ColumnInfo[];
}

type UploadStep = 'input' | 'uploading' | 'preview';

export function UploadModal({ isOpen, onClose, onUploadComplete }: UploadModalProps) {
  const [step, setStep] = useState<UploadStep>('input');
  const [datasetName, setDatasetName] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = ['.csv', '.xlsx', '.xls'];

  const handleFileSelect = useCallback((selectedFiles: FileList | null) => {
    if (!selectedFiles) return;

    const validFiles: FileWithPreview[] = [];
    const invalidFiles: string[] = [];

    Array.from(selectedFiles).forEach((file) => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (allowedExtensions.includes(ext)) {
        validFiles.push({ file });
      } else {
        invalidFiles.push(file.name);
      }
    });

    if (invalidFiles.length > 0) {
      setError(`Unsupported files: ${invalidFiles.join(', ')}`);
    } else {
      setError(null);
    }

    setFiles((prev) => [...prev, ...validFiles]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      handleFileSelect(e.dataTransfer.files);
    },
    [handleFileSelect]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleUpload = async () => {
    if (!datasetName.trim() || files.length === 0) return;

    setStep('uploading');
    setError(null);
    setUploadProgress(0);

    try {
      // Create dataset
      const dataset = await api.createDataset(datasetName.trim(), description.trim() || undefined);
      setUploadProgress(20);

      // Upload files
      const uploadedFiles = await api.uploadFiles(
        dataset.id,
        files.map((f) => f.file)
      );
      setUploadProgress(70);

      // Get previews for each file
      const updatedFiles: FileWithPreview[] = [];
      for (let i = 0; i < uploadedFiles.length; i++) {
        const uploadedFile = uploadedFiles[i];
        let columns: ColumnInfo[] = [];

        if (uploadedFile.parse_status === 'parsed') {
          try {
            const preview = await api.getFilePreview(dataset.id, uploadedFile.id);
            columns = preview.columns;
          } catch {
            // Ignore preview errors
          }
        }

        updatedFiles.push({
          file: files[i].file,
          uploaded: uploadedFile,
          columns,
        });

        setUploadProgress(70 + ((i + 1) / uploadedFiles.length) * 30);
      }

      setFiles(updatedFiles);
      setStep('preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setStep('input');
    }
  };

  const handleClose = () => {
    if (step === 'preview') {
      onUploadComplete();
    }
    setStep('input');
    setDatasetName('');
    setDescription('');
    setFiles([]);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">
            {step === 'input' && 'Upload Dataset'}
            {step === 'uploading' && 'Uploading...'}
            {step === 'preview' && 'Upload Complete'}
          </h2>
          <button
            onClick={handleClose}
            className="p-1.5 text-muted hover:text-foreground hover:bg-surface rounded-md transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 'input' && (
            <div className="space-y-6">
              {/* Dataset name */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Dataset Name
                </label>
                <input
                  type="text"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder="e.g., Study ABC-123 Data"
                  className="w-full h-10 px-3 bg-surface border border-border rounded-lg
                    placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Description <span className="text-muted">(optional)</span>
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of this dataset..."
                  rows={2}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg
                    placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 resize-none"
                />
              </div>

              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-border rounded-lg p-8
                  hover:border-primary/50 hover:bg-surface/50 transition-colors cursor-pointer"
              >
                <div className="flex flex-col items-center text-center">
                  <Upload size={32} className="text-muted mb-3" />
                  <p className="text-foreground font-medium">
                    Drop files here or click to browse
                  </p>
                  <p className="text-sm text-muted mt-1">
                    Supports CSV, Excel (.xlsx, .xls)
                  </p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => handleFileSelect(e.target.files)}
                  className="hidden"
                />
              </div>

              {/* Error message */}
              {error && (
                <div className="flex items-center gap-2 px-4 py-3 bg-error/10 text-error rounded-lg">
                  <AlertCircle size={18} />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              {/* File list */}
              {files.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-foreground">
                    Selected Files ({files.length})
                  </h4>
                  <div className="space-y-2">
                    {files.map((f, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between px-3 py-2 bg-surface rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <FileSpreadsheet size={18} className="text-primary" />
                          <div>
                            <p className="text-sm text-foreground">{f.file.name}</p>
                            <p className="text-xs text-muted">{formatFileSize(f.file.size)}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeFile(idx)}
                          className="p-1 text-muted hover:text-error rounded transition-colors"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 'uploading' && (
            <div className="flex flex-col items-center py-12">
              <Loader2 size={48} className="text-primary animate-spin mb-4" />
              <p className="text-foreground font-medium">Processing files...</p>
              <div className="w-64 h-2 bg-surface rounded-full mt-4 overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-sm text-muted mt-2">{Math.round(uploadProgress)}%</p>
            </div>
          )}

          {step === 'preview' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-success mb-6">
                <CheckCircle2 size={20} />
                <span className="font-medium">Dataset uploaded successfully!</span>
              </div>

              {files.map((f, idx) => (
                <div key={idx}>
                  {f.uploaded?.parse_status === 'parsed' && f.columns && f.uploaded.row_count && (
                    <TablePreview
                      fileName={f.file.name}
                      rowCount={f.uploaded.row_count}
                      columnCount={f.uploaded.column_count || 0}
                      columns={f.columns}
                    />
                  )}
                  {f.uploaded?.parse_status === 'error' && (
                    <div className="flex items-center gap-2 px-4 py-3 bg-error/10 text-error rounded-lg">
                      <AlertCircle size={18} />
                      <span className="text-sm">
                        {f.file.name}: {f.uploaded.parse_error}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-border">
          {step === 'input' && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-muted hover:text-foreground
                  hover:bg-surface rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!datasetName.trim() || files.length === 0}
                className="px-4 py-2 text-sm font-medium text-white bg-primary
                  hover:bg-primary/90 rounded-lg transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Upload
              </button>
            </>
          )}
          {step === 'preview' && (
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-white bg-primary
                hover:bg-primary/90 rounded-lg transition-colors"
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
