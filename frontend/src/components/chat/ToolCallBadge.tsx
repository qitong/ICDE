import { useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Wrench,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import type { ToolCallItem } from '../../types';

interface ToolCallBadgeProps {
  toolCall: ToolCallItem;
}

export function ToolCallBadge({ toolCall }: ToolCallBadgeProps) {
  const [expanded, setExpanded] = useState(false);

  const hasDetails =
    Boolean(toolCall.arguments && Object.keys(toolCall.arguments).length > 0) ||
    toolCall.output !== undefined;

  const statusIcon = () => {
    if (toolCall.status === 'started') {
      return <Loader2 size={13} className="text-primary animate-spin shrink-0" />;
    }
    if (toolCall.status === 'error') {
      return <AlertTriangle size={13} className="text-error shrink-0" />;
    }
    return <CheckCircle2 size={13} className="text-success shrink-0" />;
  };

  return (
    <div className="rounded-lg border border-border bg-background/80 text-xs overflow-hidden">
      <button
        type="button"
        onClick={() => hasDetails && setExpanded((prev) => !prev)}
        className={`w-full px-2.5 py-1.5 flex items-center gap-2 text-left ${
          hasDetails ? 'hover:bg-surface cursor-pointer' : 'cursor-default'
        }`}
      >
        {statusIcon()}
        <Wrench size={12} className="text-muted shrink-0" />
        <span className="font-mono font-medium text-foreground truncate">
          {toolCall.tool_name}
        </span>
        <span className="text-muted truncate flex-1">{toolCall.summary}</span>
        {typeof toolCall.duration_ms === 'number' && (
          <span className="text-[10px] text-muted shrink-0">
            {toolCall.duration_ms}ms
          </span>
        )}
        {hasDetails && (
          <span className="text-muted shrink-0">
            {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        )}
      </button>

      {expanded && hasDetails && (
        <div className="px-2.5 py-2 border-t border-border bg-surface/60 space-y-1.5">
          {toolCall.arguments && Object.keys(toolCall.arguments).length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wide text-muted mb-0.5">
                Arguments
              </div>
              <pre className="text-[11px] font-mono text-foreground overflow-x-auto whitespace-pre-wrap break-all bg-background p-1.5 rounded border border-border">
                {JSON.stringify(toolCall.arguments, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.output !== undefined && (
            <div>
              <div className="text-[10px] uppercase tracking-wide text-muted mb-0.5">
                Output
              </div>
              <pre className="text-[11px] font-mono text-foreground overflow-x-auto whitespace-pre-wrap break-all max-h-36 overflow-y-auto bg-background p-1.5 rounded border border-border">
                {typeof toolCall.output === 'string'
                  ? toolCall.output
                  : JSON.stringify(toolCall.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
