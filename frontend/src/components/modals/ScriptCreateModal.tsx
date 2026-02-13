import { useState, useCallback, useRef, useEffect } from 'react';
import { X, FileCode, Upload, Wand2, AlertCircle, FolderPlus, ChevronDown } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import type { ScriptCreate } from '../../types';

interface ScriptCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialFolder?: string;
}

type CreateMode = 'new' | 'upload' | 'paste';

// Default Python template
const DEFAULT_PYTHON_TEMPLATE = `"""
Script description here.
"""
import pandas as pd


def main(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main function description.

    Args:
        df: Input DataFrame

    Returns:
        Processed DataFrame
    """
    # Your code here
    result = df.copy()

    return result


if __name__ == "__main__":
    # Example usage
    pass
`;

export function ScriptCreateModal({ isOpen, onClose, initialFolder = '' }: ScriptCreateModalProps) {
  const { createScript, viewScript, state } = useApp();

  const [mode, setMode] = useState<CreateMode>('new');
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [code, setCode] = useState(DEFAULT_PYTHON_TEMPLATE);
  const [language, setLanguage] = useState<'python' | 'r' | 'sas'>('python');
  const [folder, setFolder] = useState(initialFolder);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [showFolderDropdown, setShowFolderDropdown] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropzoneRef = useRef<HTMLDivElement>(null);

  // Get unique folders from existing scripts
  const existingFolders = Array.from(
    new Set(
      state.scripts
        .map((s) => {
          const parts = s.name.split('/');
          return parts.length > 1 ? parts.slice(0, -1).join('/') : '';
        })
        .filter(Boolean)
    )
  );

  // Reset form when modal closes/opens
  useEffect(() => {
    if (isOpen) {
      setName('');
      setDisplayName('');
      setDescription('');
      setCode(DEFAULT_PYTHON_TEMPLATE);
      setLanguage('python');
      setFolder(initialFolder);
      setError(null);
      setMode('new');
    }
  }, [isOpen, initialFolder]);

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];
    const fileName = file.name;
    const ext = fileName.split('.').pop()?.toLowerCase();

    // Determine language from extension
    if (ext === 'py') setLanguage('python');
    else if (ext === 'r') setLanguage('r');
    else if (ext === 'sas') setLanguage('sas');

    // Extract name without extension
    const baseName = fileName.replace(/\.[^/.]+$/, '');
    setName(baseName.toLowerCase().replace(/[^a-z0-9_]/g, '_'));
    setDisplayName(baseName);

    // Read file content
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setCode(content);

      // Try to extract description from docstring
      const docstringMatch = content.match(/^[\s\S]*?['"]{3}([\s\S]*?)['"]{3}/);
      if (docstringMatch) {
        const desc = docstringMatch[1].trim().split('\n')[0];
        setDescription(desc);
      }
    };
    reader.readAsText(file);

    setMode('upload');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const pastedText = e.clipboardData.getData('text');
    if (pastedText && pastedText.includes('\n')) {
      // Looks like code, switch to paste mode
      setCode(pastedText);
      setMode('paste');
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!name.trim()) {
      setError('Script name is required');
      return;
    }
    if (!displayName.trim()) {
      setError('Display name is required');
      return;
    }
    if (!description.trim()) {
      setError('Description is required');
      return;
    }
    if (!code.trim()) {
      setError('Script code is required');
      return;
    }

    // Construct full name with folder
    const fullName = folder ? `${folder}/${name}` : name;

    setIsCreating(true);

    try {
      const scriptData: ScriptCreate = {
        name: fullName,
        display_name: displayName,
        description,
        code,
        language,
        created_by: 'user',
      };

      const newScript = await createScript(scriptData);
      viewScript(newScript.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create script');
    } finally {
      setIsCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-100 flex items-center justify-center">
              <FileCode className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">New Script</h2>
              <p className="text-sm text-gray-500">Create a new data transformation script</p>
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
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Mode tabs / Drop zone */}
            <div
              ref={dropzoneRef}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
                isDragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-center gap-4 mb-3">
                <button
                  type="button"
                  onClick={() => setMode('new')}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                    mode === 'new'
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  New Script
                </button>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors flex items-center gap-1.5 ${
                    mode === 'upload'
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <Upload size={14} />
                  Upload
                </button>
              </div>
              <p className="text-xs text-gray-500">
                Drop .py, .R, or .sas files here, or click Upload
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".py,.r,.R,.sas"
                className="hidden"
                onChange={(e) => handleFileSelect(e.target.files)}
              />
            </div>

            {/* Folder selection */}
            <div className="relative">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Folder (optional)
              </label>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowFolderDropdown(!showFolderDropdown)}
                  className="w-full flex items-center justify-between px-3 py-2 text-left border border-gray-300 rounded-lg hover:border-gray-400 transition-colors"
                >
                  <span className={folder ? 'text-gray-900' : 'text-gray-400'}>
                    {folder || 'Root (no folder)'}
                  </span>
                  <ChevronDown size={16} className="text-gray-400" />
                </button>

                {showFolderDropdown && (
                  <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg">
                    <button
                      type="button"
                      onClick={() => {
                        setFolder('');
                        setShowFolderDropdown(false);
                      }}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50"
                    >
                      Root (no folder)
                    </button>
                    {existingFolders.map((f) => (
                      <button
                        key={f}
                        type="button"
                        onClick={() => {
                          setFolder(f);
                          setShowFolderDropdown(false);
                        }}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50"
                      >
                        {f}
                      </button>
                    ))}
                    <div className="border-t border-gray-100">
                      <div className="flex items-center gap-2 p-2">
                        <FolderPlus size={14} className="text-gray-400" />
                        <input
                          type="text"
                          placeholder="New folder name..."
                          className="flex-1 text-sm outline-none"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault();
                              const value = (e.target as HTMLInputElement).value.trim();
                              if (value) {
                                setFolder(value);
                                setShowFolderDropdown(false);
                              }
                            }
                          }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Name fields */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Script Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                  placeholder="my_script"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm font-mono"
                />
                <p className="mt-1 text-xs text-gray-500">Lowercase, underscores only</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="My Script"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm"
                />
              </div>
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <div className="flex gap-2">
                {(['python', 'r', 'sas'] as const).map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => setLanguage(lang)}
                    className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                      language === lang
                        ? 'border-primary bg-primary/5 text-primary'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'
                    }`}
                  >
                    {lang === 'python' ? 'Python' : lang === 'r' ? 'R' : 'SAS'}
                  </button>
                ))}
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description <span className="text-red-500">*</span>
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this script does..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm resize-none"
              />
            </div>

            {/* Code preview */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Code <span className="text-red-500">*</span>
                </label>
                <span className="text-xs text-gray-500">
                  {code.split('\n').length} lines
                </span>
              </div>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                onPaste={handlePaste}
                placeholder="Paste or write your code here..."
                rows={8}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none text-sm font-mono resize-none bg-gray-50"
              />
            </div>

            {/* Metadata generation hint */}
            <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg">
              <Wand2 size={16} className="text-blue-500 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-blue-700">
                <p className="font-medium">AI Metadata Generation</p>
                <p className="text-blue-600">
                  After creating the script, you can generate parameter schemas and use cases
                  using the metadata editor in the script view.
                </p>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg">
                <AlertCircle size={16} />
                <span className="text-sm">{error}</span>
              </div>
            )}
          </form>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isCreating}
            className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isCreating ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              'Create Script'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
