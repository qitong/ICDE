import { Bot, User, AlertCircle } from 'lucide-react';
import type { Message } from '../../types';
import { ToolCallBadge } from './ToolCallBadge';
import { ApprovalCard } from './ApprovalCard';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  if (isSystem) {
    return (
      <div className="flex gap-3 px-4 py-3 bg-surface/50 border-y border-border animate-fade-in">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <Bot size={18} className="text-primary" strokeWidth={1.5} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-foreground">ICDE Assistant</span>
            <span className="text-xs text-muted">{formatTime(message.timestamp)}</span>
          </div>
          <p className="text-sm text-muted leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex gap-3 px-4 py-3 animate-slide-in">
        <div className="flex-1 min-w-0 flex flex-col items-end">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-muted">{formatTime(message.timestamp)}</span>
            <span className="text-sm font-medium text-foreground">You</span>
          </div>
          <div className="bg-primary text-white text-sm px-4 py-2.5 rounded-2xl rounded-tr-md max-w-[85%]">
            <p className="leading-relaxed">{message.content}</p>
          </div>
        </div>
        <div className="w-8 h-8 rounded-lg bg-border flex items-center justify-center shrink-0">
          <User size={18} className="text-muted" strokeWidth={1.5} />
        </div>
      </div>
    );
  }

  const hasToolCalls = Boolean(message.toolCalls && message.toolCalls.length > 0);
  const hasApprovals = Boolean(message.approvals && message.approvals.length > 0);

  // Assistant message
  return (
    <div className="flex gap-3 px-4 py-3 animate-slide-in">
      <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
        <Bot size={18} className="text-primary" strokeWidth={1.5} />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-foreground">ICDE Assistant</span>
          <span className="text-xs text-muted">{formatTime(message.timestamp)}</span>
          {message.status === 'error' && (
            <AlertCircle size={14} className="text-error" />
          )}
        </div>

        {hasToolCalls && (
          <div className="space-y-1.5 max-w-[92%]">
            {message.toolCalls!.map((tc) => (
              <ToolCallBadge key={tc.call_id} toolCall={tc} />
            ))}
          </div>
        )}

        {hasApprovals && (
          <div className="space-y-2 max-w-[92%]">
            {message.approvals!.map((appr) => (
              <ApprovalCard key={appr.approval_id} approval={appr} />
            ))}
          </div>
        )}

        {(message.content || (!hasToolCalls && !hasApprovals)) && (
          <div className="bg-surface text-foreground text-sm px-4 py-2.5 rounded-2xl rounded-tl-md max-w-[85%] border border-border">
            <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>
        )}
      </div>
    </div>
  );
}
