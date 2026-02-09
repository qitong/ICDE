import { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { useApp } from '../../contexts/AppContext';
import { Loader2 } from 'lucide-react';

export function MessageList() {
  const { state } = useApp();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.isProcessing]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="py-2">
        {state.messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Typing indicator */}
        {state.isProcessing && (
          <div className="flex gap-3 px-4 py-3 animate-fade-in">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <Loader2 size={18} className="text-primary animate-spin" strokeWidth={1.5} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-foreground">ICDE Assistant</span>
              </div>
              <div className="bg-surface text-muted text-sm px-4 py-2.5 rounded-2xl rounded-tl-md max-w-[85%] border border-border">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-muted rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-muted rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-muted rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
