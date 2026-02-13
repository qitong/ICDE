import { useApp } from '../../contexts/AppContext';
import {
  FileCode,
  Play,
  Save,
  RotateCcw,
  Tag,
  Terminal,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  Braces,
  ArrowRightLeft,
  Lightbulb,
  Code2,
  BookOpen,
  Wand2,
  Pencil,
  X,
} from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import type { Script, ScriptCreate } from '../../types';

// Token types for syntax highlighting
type TokenType = 'keyword' | 'builtin' | 'string' | 'comment' | 'number' | 'function' | 'decorator' | 'self' | 'default';

interface Token {
  type: TokenType;
  value: string;
}

// Tokenize Python code for syntax highlighting
function tokenizePython(code: string): Token[][] {
  const keywords = new Set([
    'def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except',
    'finally', 'with', 'as', 'import', 'from', 'return', 'yield', 'raise',
    'pass', 'break', 'continue', 'and', 'or', 'not', 'in', 'is', 'lambda',
    'None', 'True', 'False', 'async', 'await', 'global', 'nonlocal',
  ]);

  const builtins = new Set([
    'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set',
    'tuple', 'bool', 'type', 'isinstance', 'sum', 'min', 'max', 'abs',
    'round', 'sorted', 'enumerate', 'zip', 'map', 'filter', 'open',
  ]);

  const lines = code.split('\n');
  const tokenizedLines: Token[][] = [];

  for (const line of lines) {
    const tokens: Token[] = [];
    let i = 0;

    while (i < line.length) {
      // Comments
      if (line[i] === '#') {
        tokens.push({ type: 'comment', value: line.slice(i) });
        break;
      }

      // Decorator
      if (line[i] === '@' && (i === 0 || /\s/.test(line[i - 1]))) {
        let end = i + 1;
        while (end < line.length && /\w/.test(line[end])) end++;
        tokens.push({ type: 'decorator', value: line.slice(i, end) });
        i = end;
        continue;
      }

      // Strings (triple-quoted)
      if (line.slice(i, i + 3) === '"""' || line.slice(i, i + 3) === "'''") {
        const quote = line.slice(i, i + 3);
        let end = i + 3;
        while (end < line.length && line.slice(end, end + 3) !== quote) end++;
        end = Math.min(end + 3, line.length);
        tokens.push({ type: 'string', value: line.slice(i, end) });
        i = end;
        continue;
      }

      // Strings (single/double quoted)
      if (line[i] === '"' || line[i] === "'") {
        const quote = line[i];
        let end = i + 1;
        while (end < line.length && line[end] !== quote) {
          if (line[end] === '\\') end++;
          end++;
        }
        end = Math.min(end + 1, line.length);
        tokens.push({ type: 'string', value: line.slice(i, end) });
        i = end;
        continue;
      }

      // Numbers
      if (/\d/.test(line[i])) {
        let end = i;
        while (end < line.length && /[\d.]/.test(line[end])) end++;
        tokens.push({ type: 'number', value: line.slice(i, end) });
        i = end;
        continue;
      }

      // Words (identifiers, keywords, builtins)
      if (/[a-zA-Z_]/.test(line[i])) {
        let end = i;
        while (end < line.length && /\w/.test(line[end])) end++;
        const word = line.slice(i, end);

        if (keywords.has(word)) {
          tokens.push({ type: 'keyword', value: word });
        } else if (builtins.has(word) && line[end] === '(') {
          tokens.push({ type: 'builtin', value: word });
        } else if (word === 'self') {
          tokens.push({ type: 'self', value: word });
        } else if (tokens.length > 0 && tokens[tokens.length - 1].value === 'def') {
          tokens.push({ type: 'function', value: word });
        } else {
          tokens.push({ type: 'default', value: word });
        }
        i = end;
        continue;
      }

      // Default: single character
      tokens.push({ type: 'default', value: line[i] });
      i++;
    }

    tokenizedLines.push(tokens);
  }

  return tokenizedLines;
}

// Get CSS class for token type
function getTokenClass(type: TokenType): string {
  switch (type) {
    case 'keyword': return 'text-purple-600 font-semibold';
    case 'builtin': return 'text-blue-600';
    case 'string': return 'text-green-600';
    case 'comment': return 'text-gray-400 italic';
    case 'number': return 'text-orange-500';
    case 'function': return 'text-amber-600 font-medium';
    case 'decorator': return 'text-yellow-600';
    case 'self': return 'text-red-500';
    default: return 'text-gray-800';
  }
}

// ============ Metadata Panel Component ============

interface MetadataPanelProps {
  script: Script;
  isExpanded: boolean;
  onToggle: () => void;
  onUpdate: (data: Partial<ScriptCreate>) => Promise<void>;
}

function MetadataPanel({ script, isExpanded, onToggle, onUpdate }: MetadataPanelProps) {
  const [activeTab, setActiveTab] = useState<'params' | 'returns' | 'examples' | 'usecases'>('params');
  const [isEditing, setIsEditing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [editedUseCases, setEditedUseCases] = useState<string[]>(script.use_cases || []);
  const [newUseCase, setNewUseCase] = useState('');

  // Update local state when script changes
  useEffect(() => {
    setEditedUseCases(script.use_cases || []);
  }, [script.id, script.use_cases]);

  const handleGenerateMetadata = async () => {
    setIsGenerating(true);
    // Simulate AI generation - in production this would call an API
    setTimeout(async () => {
      const generatedUseCases = [
        `Process and transform data using ${script.display_name}`,
        `Apply ${script.name} function to clinical datasets`,
        `Generate summary statistics from input DataFrame`,
      ];

      try {
        await onUpdate({
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
      await onUpdate({ use_cases: updated });
    } catch (error) {
      console.error('Failed to add use case:', error);
    }
  };

  const handleRemoveUseCase = async (index: number) => {
    const updated = editedUseCases.filter((_, i) => i !== index);
    setEditedUseCases(updated);
    try {
      await onUpdate({ use_cases: updated });
    } catch (error) {
      console.error('Failed to remove use case:', error);
    }
  };

  // Show panel even without metadata (user can add via AI generation)
  return (
    <div className="flex-shrink-0 border-b border-border bg-white">
      {/* Toggle Header */}
      <div className="flex items-center justify-between px-4 py-2 hover:bg-gray-50 transition-colors">
        <button
          onClick={onToggle}
          className="flex items-center gap-2 text-sm text-foreground flex-1"
        >
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <BookOpen size={14} className="text-blue-500" />
          <span className="font-medium">API Documentation</span>
          <span className="text-xs text-muted">(Tool Metadata for LLM)</span>
        </button>
        {isExpanded && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerateMetadata}
              disabled={isGenerating}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <div className="w-3 h-3 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Wand2 size={12} />
                  Generate with AI
                </>
              )}
            </button>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded transition-colors ${
                isEditing
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Pencil size={12} />
              {isEditing ? 'Done' : 'Edit'}
            </button>
          </div>
        )}
      </div>

      {isExpanded && (
        <div className="border-t border-gray-100">
          {/* Tab Bar */}
          <div className="flex border-b border-gray-100 px-4">
            <button
              onClick={() => setActiveTab('params')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'params'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-muted hover:text-foreground'
              }`}
            >
              <Braces size={12} />
              Parameters
            </button>
            <button
              onClick={() => setActiveTab('returns')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'returns'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-muted hover:text-foreground'
              }`}
            >
              <ArrowRightLeft size={12} />
              Returns
            </button>
            <button
              onClick={() => setActiveTab('examples')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'examples'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-muted hover:text-foreground'
              }`}
            >
              <Code2 size={12} />
              Examples
            </button>
            <button
              onClick={() => setActiveTab('usecases')}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'usecases'
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-muted hover:text-foreground'
              }`}
            >
              <Lightbulb size={12} />
              Use Cases
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-4 max-h-64 overflow-auto">
            {/* Parameters Tab */}
            {activeTab === 'params' && script.parameters_schema && (
              <div className="space-y-3">
                {Object.entries(script.parameters_schema.properties).map(([name, prop]) => {
                  const isRequired = script.parameters_schema?.required?.includes(name);
                  return (
                    <div key={name} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <code className="text-sm font-semibold text-blue-600">{name}</code>
                        <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-200 text-gray-600 font-mono">
                          {prop.type}
                        </span>
                        {isRequired ? (
                          <span className="px-1.5 py-0.5 text-[10px] rounded bg-red-100 text-red-600 font-medium">
                            required
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-500">
                            optional
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-600">{prop.description}</p>
                      {prop.enum && (
                        <div className="mt-1.5 flex items-center gap-1 flex-wrap">
                          <span className="text-[10px] text-gray-500">options:</span>
                          {prop.enum.map((val) => (
                            <code key={val} className="px-1.5 py-0.5 text-[10px] bg-white border rounded">
                              {val}
                            </code>
                          ))}
                        </div>
                      )}
                      {prop.default !== undefined && (
                        <div className="mt-1 text-[10px] text-gray-500">
                          default: <code className="bg-white px-1 rounded">{JSON.stringify(prop.default)}</code>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Returns Tab */}
            {activeTab === 'returns' && script.returns_schema && (
              <div className="bg-green-50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2 py-0.5 text-xs rounded bg-green-200 text-green-700 font-mono">
                    {script.returns_schema.type}
                  </span>
                </div>
                <p className="text-sm text-gray-700">{script.returns_schema.description}</p>
                {script.returns_schema.properties && (
                  <div className="mt-3 space-y-2">
                    <span className="text-xs font-medium text-gray-500">Properties:</span>
                    {Object.entries(script.returns_schema.properties).map(([key, val]) => (
                      <div key={key} className="flex items-start gap-2 text-xs pl-2">
                        <code className="text-green-600 font-medium">{key}</code>
                        <span className="text-gray-400">:</span>
                        <span className="text-gray-600">{(val as { description?: string }).description || JSON.stringify(val)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Examples Tab */}
            {activeTab === 'examples' && script.example_calls && (
              <div className="space-y-3">
                {script.example_calls.map((example, i) => (
                  <div key={i} className="bg-gray-900 rounded-lg p-3 text-xs font-mono">
                    {example.description && (
                      <p className="text-gray-400 mb-2 font-sans"># {example.description}</p>
                    )}
                    <div className="text-green-400 mb-1">
                      <span className="text-gray-500">&gt;&gt;&gt; </span>
                      {example.input}
                    </div>
                    <div className="text-amber-300 pl-4 whitespace-pre-wrap break-all">
                      {example.output}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Use Cases Tab */}
            {activeTab === 'usecases' && (
              <div className="space-y-3">
                {editedUseCases.length > 0 ? (
                  <ul className="space-y-2">
                    {editedUseCases.map((useCase, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm group">
                        <Lightbulb size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-700 flex-1">{useCase}</span>
                        {isEditing && (
                          <button
                            onClick={() => handleRemoveUseCase(i)}
                            className="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                          >
                            <X size={14} />
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted italic">No use cases defined</p>
                )}

                {isEditing && (
                  <div className="flex items-center gap-2 mt-3">
                    <input
                      type="text"
                      value={newUseCase}
                      onChange={(e) => setNewUseCase(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddUseCase()}
                      placeholder="Add a new use case..."
                      className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary/20"
                    />
                    <button
                      onClick={handleAddUseCase}
                      disabled={!newUseCase.trim()}
                      className="px-3 py-1.5 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Add
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Empty states with generate hint */}
            {activeTab === 'params' && !script.parameters_schema && (
              <div className="text-center py-4">
                <p className="text-sm text-muted italic mb-2">No parameters schema defined</p>
                <p className="text-xs text-gray-400">
                  Click "Generate with AI" to automatically extract parameters from your code
                </p>
              </div>
            )}
            {activeTab === 'returns' && !script.returns_schema && (
              <div className="text-center py-4">
                <p className="text-sm text-muted italic mb-2">No returns schema defined</p>
                <p className="text-xs text-gray-400">
                  Click "Generate with AI" to automatically detect return types
                </p>
              </div>
            )}
            {activeTab === 'examples' && !script.example_calls && (
              <div className="text-center py-4">
                <p className="text-sm text-muted italic mb-2">No examples defined</p>
                <p className="text-xs text-gray-400">
                  Click "Generate with AI" to create example function calls
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function ScriptView() {
  const { state, updateScript } = useApp();
  const { scripts, selectedScriptId } = state;

  const selectedScript = scripts.find((s) => s.id === selectedScriptId);

  const [code, setCode] = useState(selectedScript?.code || '');
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showOutput, setShowOutput] = useState(false);
  const [output, setOutput] = useState<string | null>(null);
  const [showMetadata, setShowMetadata] = useState(true);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const codeDisplayRef = useRef<HTMLDivElement>(null);

  // Update code when selected script changes
  useEffect(() => {
    if (selectedScript) {
      setCode(selectedScript.code);
      setHasChanges(false);
    }
  }, [selectedScript?.id]);

  // Sync scroll between textarea and code display
  const handleScroll = useCallback(() => {
    if (textareaRef.current && codeDisplayRef.current) {
      codeDisplayRef.current.scrollTop = textareaRef.current.scrollTop;
      codeDisplayRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  const handleCodeChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newCode = e.target.value;
    setCode(newCode);
    setHasChanges(newCode !== selectedScript?.code);
  };

  const handleSave = async () => {
    if (!selectedScript || !hasChanges) return;

    setIsSaving(true);
    try {
      await updateScript(selectedScript.id, { code });
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save script:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (selectedScript) {
      setCode(selectedScript.code);
      setHasChanges(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRun = () => {
    setShowOutput(true);
    setOutput('Running script...\n\n# Script execution is not implemented yet.\n# In production, this would execute the script and show results.');
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Cmd/Ctrl + S to save
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }

    // Handle Tab for indentation
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const newCode = code.substring(0, start) + '    ' + code.substring(end);
        setCode(newCode);
        setHasChanges(newCode !== selectedScript?.code);

        // Move cursor after the inserted spaces
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 4;
        }, 0);
      }
    }
  };

  // Get keywords array
  const keywords = selectedScript?.keywords ?? [];

  // Empty state when no script is selected
  if (!selectedScriptId || !selectedScript) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-surface text-center p-8">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <FileCode className="w-8 h-8 text-muted" />
        </div>
        <h3 className="text-lg font-semibold text-primary mb-2">No Script Selected</h3>
        <p className="text-muted text-sm max-w-md">
          Select a script from the sidebar to view and edit its code.
        </p>
      </div>
    );
  }

  const tokenizedLines = tokenizePython(code);

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">
      {/* Script header */}
      <div className="flex-shrink-0 bg-surface border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <FileCode size={18} className="text-green-500" />
              <span className="text-sm font-medium text-foreground">
                {selectedScript.name}.py
              </span>
              {hasChanges && (
                <span className="w-2 h-2 rounded-full bg-orange-500" title="Unsaved changes" />
              )}
            </div>
            <span className="text-xs text-muted px-2 py-0.5 bg-gray-100 rounded">
              {selectedScript.language || 'Python'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted hover:text-foreground hover:bg-gray-100 rounded transition-colors"
              title="Copy code"
            >
              {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              onClick={handleReset}
              disabled={!hasChanges}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted hover:text-foreground hover:bg-gray-100 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Reset changes"
            >
              <RotateCcw size={14} />
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-primary text-white rounded hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Save (Cmd+S)"
            >
              <Save size={14} />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={handleRun}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
              title="Run script"
            >
              <Play size={14} />
              Run
            </button>
          </div>
        </div>

        {/* Script description */}
        <p className="mt-2 text-xs text-muted">{selectedScript.description}</p>

        {/* Keywords */}
        {keywords.length > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <Tag size={12} className="text-muted" />
            <div className="flex flex-wrap gap-1">
              {keywords.map((kw, i) => (
                <span key={i} className="px-1.5 py-0.5 text-xs bg-primary/10 text-primary rounded">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Structured Metadata Panel */}
      <MetadataPanel
        script={selectedScript}
        isExpanded={showMetadata}
        onToggle={() => setShowMetadata(!showMetadata)}
        onUpdate={async (data) => {
          await updateScript(selectedScript.id, data);
        }}
      />

      {/* Code editor area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 relative overflow-auto bg-gray-50">
          {/* Line numbers */}
          <div className="absolute left-0 top-0 bottom-0 w-12 bg-gray-100 border-r border-gray-200 select-none z-10 overflow-hidden">
            <div className="py-4 text-right pr-3">
              {tokenizedLines.map((_, i) => (
                <div
                  key={i}
                  className="text-xs text-gray-400 h-5 leading-5 font-mono"
                >
                  {i + 1}
                </div>
              ))}
            </div>
          </div>

          {/* Code editor container */}
          <div className="ml-12 relative min-h-full">
            {/* Syntax highlighted display layer */}
            <div
              ref={codeDisplayRef}
              className="absolute inset-0 py-4 px-4 font-mono text-sm leading-5 whitespace-pre overflow-hidden pointer-events-none"
              aria-hidden="true"
            >
              {tokenizedLines.map((lineTokens, lineIdx) => (
                <div key={lineIdx} className="h-5">
                  {lineTokens.length === 0 ? (
                    <span>&nbsp;</span>
                  ) : (
                    lineTokens.map((token, tokenIdx) => (
                      <span key={tokenIdx} className={getTokenClass(token.type)}>
                        {token.value}
                      </span>
                    ))
                  )}
                </div>
              ))}
            </div>

            {/* Editable textarea layer */}
            <textarea
              ref={textareaRef}
              value={code}
              onChange={handleCodeChange}
              onScroll={handleScroll}
              onKeyDown={handleKeyDown}
              className="absolute inset-0 w-full h-full py-4 px-4 font-mono text-sm leading-5 bg-transparent text-transparent caret-gray-800 resize-none outline-none"
              spellCheck={false}
              autoCapitalize="off"
              autoComplete="off"
              autoCorrect="off"
              style={{
                minHeight: `${Math.max(tokenizedLines.length * 20 + 32, 300)}px`,
              }}
            />
          </div>
        </div>

        {/* Output panel */}
        {showOutput && (
          <div className="flex-shrink-0 h-48 border-t border-border bg-surface">
            <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b border-border">
              <div className="flex items-center gap-2 text-sm text-foreground">
                <Terminal size={14} />
                Output
              </div>
              <button
                onClick={() => setShowOutput(false)}
                className="text-muted hover:text-foreground text-xs px-2 py-1 hover:bg-gray-200 rounded"
              >
                ✕
              </button>
            </div>
            <pre className="p-4 text-xs font-mono text-muted overflow-auto h-[calc(100%-36px)]">
              {output}
            </pre>
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="flex-shrink-0 h-6 bg-gray-100 border-t border-border flex items-center justify-between px-4 text-xs text-muted">
        <div className="flex items-center gap-4">
          <span>Ln {tokenizedLines.length}, Col 1</span>
          <span>Spaces: 4</span>
          <span>UTF-8</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Python</span>
          <span>v{selectedScript.version}</span>
          <span>Used {selectedScript.usage_count} times</span>
        </div>
      </div>
    </div>
  );
}
