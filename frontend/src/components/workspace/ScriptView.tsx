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
} from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';

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
