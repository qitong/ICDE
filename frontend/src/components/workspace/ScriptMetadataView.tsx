import { useApp } from '../../contexts/AppContext';
import {
  FileCode,
  Braces,
  ArrowRightLeft,
  Lightbulb,
  Code2,
  BookOpen,
  Wand2,
  Pencil,
  X,
  Tag,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import type { Script, ScriptCreate } from '../../types';

interface ScriptMetadataViewProps {
  script?: Script;
}

export function ScriptMetadataView({ script: propScript }: ScriptMetadataViewProps) {
  const { state, updateScript } = useApp();
  const { scripts, selectedScriptId } = state;

  // Use prop script if provided, otherwise get from state
  const selectedScript = propScript || scripts.find((s) => s.id === selectedScriptId);

  const [activeTab, setActiveTab] = useState<'params' | 'returns' | 'examples' | 'usecases'>('params');
  const [isEditing, setIsEditing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [editedUseCases, setEditedUseCases] = useState<string[]>(selectedScript?.use_cases || []);
  const [newUseCase, setNewUseCase] = useState('');

  // Update local state when script changes
  useEffect(() => {
    if (selectedScript) {
      setEditedUseCases(selectedScript.use_cases || []);
    }
  }, [selectedScript?.id, selectedScript?.use_cases]);

  const handleUpdate = async (data: Partial<ScriptCreate>) => {
    if (!selectedScript) return;
    await updateScript(selectedScript.id, data);
  };

  const handleGenerateMetadata = async () => {
    if (!selectedScript) return;
    setIsGenerating(true);
    // Simulate AI generation - in production this would call an API
    setTimeout(async () => {
      const generatedUseCases = [
        `Process and transform data using ${selectedScript.display_name}`,
        `Apply ${selectedScript.name} function to clinical datasets`,
        `Generate summary statistics from input DataFrame`,
      ];

      try {
        await handleUpdate({
          use_cases: generatedUseCases,
        });
        setEditedUseCases(generatedUseCases);
      } catch (error) {
        console.error('Failed to update metadata:', error);
      }
      setIsGenerating(false);
    }, 1500);
  };

  const handleAddUseCase = async () => {
    if (!newUseCase.trim()) return;
    const updated = [...editedUseCases, newUseCase.trim()];
    setEditedUseCases(updated);
    setNewUseCase('');
    try {
      await handleUpdate({ use_cases: updated });
    } catch (error) {
      console.error('Failed to add use case:', error);
    }
  };

  const handleRemoveUseCase = async (index: number) => {
    const updated = editedUseCases.filter((_, i) => i !== index);
    setEditedUseCases(updated);
    try {
      await handleUpdate({ use_cases: updated });
    } catch (error) {
      console.error('Failed to remove use case:', error);
    }
  };

  // Empty state when no script is selected
  if (!selectedScriptId || !selectedScript) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-surface text-center p-8">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <FileCode className="w-8 h-8 text-muted" />
        </div>
        <h3 className="text-lg font-semibold text-primary mb-2">No Script Selected</h3>
        <p className="text-muted text-sm max-w-md">
          Select a script from the sidebar to view its metadata and API documentation.
        </p>
      </div>
    );
  }

  // Get keywords array
  const keywords = selectedScript.keywords ?? [];

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">
      {/* Script header */}
      <div className="flex-shrink-0 bg-surface border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <FileCode size={20} className="text-green-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                {selectedScript.display_name}
              </h2>
              <span className="text-sm text-muted">{selectedScript.name}.py</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerateMetadata}
              disabled={isGenerating}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Wand2 size={14} />
                  Generate with AI
                </>
              )}
            </button>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                isEditing
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Pencil size={14} />
              {isEditing ? 'Done' : 'Edit'}
            </button>
          </div>
        </div>

        {/* Script description */}
        <p className="mt-3 text-sm text-muted">{selectedScript.description}</p>

        {/* Keywords */}
        {keywords.length > 0 && (
          <div className="mt-3 flex items-center gap-2">
            <Tag size={14} className="text-muted" />
            <div className="flex flex-wrap gap-1.5">
              {keywords.map((kw, i) => (
                <span key={i} className="px-2 py-0.5 text-xs bg-primary/10 text-primary rounded-full">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Script stats */}
        <div className="mt-3 flex items-center gap-4 text-xs text-muted">
          <span>Version {selectedScript.version}</span>
          <span>Used {selectedScript.usage_count} times</span>
          <span>Language: {selectedScript.language || 'Python'}</span>
        </div>
      </div>

      {/* API Documentation Header */}
      <div className="flex-shrink-0 bg-white border-b border-border px-6 py-3">
        <div className="flex items-center gap-2">
          <BookOpen size={16} className="text-blue-500" />
          <span className="font-medium text-foreground">API Documentation</span>
          <span className="text-xs text-muted">(Tool Metadata for LLM)</span>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex-shrink-0 flex border-b border-gray-100 px-6 bg-white">
        <button
          onClick={() => setActiveTab('params')}
          className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'params'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-muted hover:text-foreground'
          }`}
        >
          <Braces size={14} />
          Parameters
        </button>
        <button
          onClick={() => setActiveTab('returns')}
          className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'returns'
              ? 'border-green-500 text-green-600'
              : 'border-transparent text-muted hover:text-foreground'
          }`}
        >
          <ArrowRightLeft size={14} />
          Returns
        </button>
        <button
          onClick={() => setActiveTab('examples')}
          className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'examples'
              ? 'border-purple-500 text-purple-600'
              : 'border-transparent text-muted hover:text-foreground'
          }`}
        >
          <Code2 size={14} />
          Examples
        </button>
        <button
          onClick={() => setActiveTab('usecases')}
          className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'usecases'
              ? 'border-amber-500 text-amber-600'
              : 'border-transparent text-muted hover:text-foreground'
          }`}
        >
          <Lightbulb size={14} />
          Use Cases
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto p-6 bg-surface">
        {/* Parameters Tab */}
        {activeTab === 'params' && (
          <div className="max-w-3xl">
            {selectedScript.parameters_schema ? (
              <div className="space-y-4">
                {Object.entries(selectedScript.parameters_schema.properties).map(([name, prop]) => {
                  const isRequired = selectedScript.parameters_schema?.required?.includes(name);
                  return (
                    <div key={name} className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                      <div className="flex items-center gap-2 mb-2">
                        <code className="text-base font-semibold text-blue-600">{name}</code>
                        <span className="px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600 font-mono">
                          {prop.type}
                        </span>
                        {isRequired ? (
                          <span className="px-2 py-0.5 text-xs rounded bg-red-100 text-red-600 font-medium">
                            required
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 text-xs rounded bg-gray-50 text-gray-500">
                            optional
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{prop.description}</p>
                      {prop.enum && (
                        <div className="mt-2 flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-gray-500">Options:</span>
                          {prop.enum.map((val) => (
                            <code key={val} className="px-2 py-0.5 text-xs bg-gray-50 border rounded">
                              {val}
                            </code>
                          ))}
                        </div>
                      )}
                      {prop.default !== undefined && (
                        <div className="mt-2 text-xs text-gray-500">
                          Default: <code className="bg-gray-50 px-1.5 py-0.5 rounded">{JSON.stringify(prop.default)}</code>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-12 bg-white rounded-lg border border-dashed border-gray-300">
                <Braces size={32} className="mx-auto text-gray-300 mb-3" />
                <p className="text-muted mb-2">No parameters schema defined</p>
                <p className="text-xs text-gray-400">
                  Click "Generate with AI" to automatically extract parameters from your code
                </p>
              </div>
            )}
          </div>
        )}

        {/* Returns Tab */}
        {activeTab === 'returns' && (
          <div className="max-w-3xl">
            {selectedScript.returns_schema ? (
              <div className="bg-white rounded-lg p-5 border border-green-200 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-3 py-1 text-sm rounded bg-green-100 text-green-700 font-mono">
                    {selectedScript.returns_schema.type}
                  </span>
                </div>
                <p className="text-gray-700">{selectedScript.returns_schema.description}</p>
                {selectedScript.returns_schema.properties && (
                  <div className="mt-4 space-y-2">
                    <span className="text-sm font-medium text-gray-500">Properties:</span>
                    <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                      {Object.entries(selectedScript.returns_schema.properties).map(([key, val]) => (
                        <div key={key} className="flex items-start gap-2 text-sm">
                          <code className="text-green-600 font-medium">{key}</code>
                          <span className="text-gray-400">:</span>
                          <span className="text-gray-600">{(val as { description?: string }).description || JSON.stringify(val)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 bg-white rounded-lg border border-dashed border-gray-300">
                <ArrowRightLeft size={32} className="mx-auto text-gray-300 mb-3" />
                <p className="text-muted mb-2">No returns schema defined</p>
                <p className="text-xs text-gray-400">
                  Click "Generate with AI" to automatically detect return types
                </p>
              </div>
            )}
          </div>
        )}

        {/* Examples Tab */}
        {activeTab === 'examples' && (
          <div className="max-w-3xl">
            {selectedScript.example_calls && selectedScript.example_calls.length > 0 ? (
              <div className="space-y-4">
                {selectedScript.example_calls.map((example, i) => (
                  <div key={i} className="bg-gray-900 rounded-lg p-4 text-sm font-mono shadow-sm">
                    {example.description && (
                      <p className="text-gray-400 mb-3 font-sans text-sm"># {example.description}</p>
                    )}
                    <div className="text-green-400 mb-2">
                      <span className="text-gray-500">&gt;&gt;&gt; </span>
                      {example.input}
                    </div>
                    <div className="text-amber-300 pl-6 whitespace-pre-wrap break-all">
                      {example.output}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 bg-white rounded-lg border border-dashed border-gray-300">
                <Code2 size={32} className="mx-auto text-gray-300 mb-3" />
                <p className="text-muted mb-2">No examples defined</p>
                <p className="text-xs text-gray-400">
                  Click "Generate with AI" to create example function calls
                </p>
              </div>
            )}
          </div>
        )}

        {/* Use Cases Tab */}
        {activeTab === 'usecases' && (
          <div className="max-w-3xl">
            {editedUseCases.length > 0 ? (
              <ul className="space-y-3">
                {editedUseCases.map((useCase, i) => (
                  <li key={i} className="flex items-start gap-3 bg-white rounded-lg p-4 border border-gray-200 shadow-sm group">
                    <Lightbulb size={18} className="text-amber-500 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-700 flex-1">{useCase}</span>
                    {isEditing && (
                      <button
                        onClick={() => handleRemoveUseCase(i)}
                        className="p-1.5 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all rounded hover:bg-red-50"
                      >
                        <X size={16} />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-center py-12 bg-white rounded-lg border border-dashed border-gray-300">
                <Lightbulb size={32} className="mx-auto text-gray-300 mb-3" />
                <p className="text-muted mb-2">No use cases defined</p>
                <p className="text-xs text-gray-400">
                  Click "Generate with AI" or "Edit" to add use cases
                </p>
              </div>
            )}

            {isEditing && (
              <div className="flex items-center gap-2 mt-4">
                <input
                  type="text"
                  value={newUseCase}
                  onChange={(e) => setNewUseCase(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddUseCase()}
                  placeholder="Add a new use case..."
                  className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                <button
                  onClick={handleAddUseCase}
                  disabled={!newUseCase.trim()}
                  className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
