import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Mic } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';

export function ChatInput() {
  const [message, setMessage] = useState('');
  const { sendMessage, state } = useApp();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !state.isProcessing) {
      sendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t border-border bg-background p-4">
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-end gap-2 bg-surface border border-border rounded-xl p-2 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20 transition-all duration-150">
          {/* Attachment button */}
          <button
            type="button"
            className="p-2 text-muted hover:text-foreground rounded-lg hover:bg-border/50 transition-colors"
            title="Attach file"
          >
            <Paperclip size={18} />
          </button>

          {/* Text input */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your data..."
            disabled={state.isProcessing}
            className="
              flex-1 bg-transparent text-sm text-foreground
              placeholder:text-muted resize-none
              focus:outline-none
              min-h-[24px] max-h-[120px]
              py-1.5
              disabled:opacity-50
            "
            rows={1}
          />

          {/* Voice input button */}
          <button
            type="button"
            className="p-2 text-muted hover:text-foreground rounded-lg hover:bg-border/50 transition-colors"
            title="Voice input"
          >
            <Mic size={18} />
          </button>

          {/* Send button */}
          <button
            type="submit"
            disabled={!message.trim() || state.isProcessing}
            className={`
              p-2 rounded-lg transition-all duration-150
              ${message.trim() && !state.isProcessing
                ? 'bg-primary text-white hover:bg-primary-hover'
                : 'bg-border text-muted cursor-not-allowed'
              }
            `}
            title="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </form>

      {/* Quick prompts */}
      <div className="mt-3 flex flex-wrap gap-2">
        {[
          'Generate demographics table',
          'Show adverse events summary',
          'Analyze efficacy endpoints',
        ].map((prompt) => (
          <button
            key={prompt}
            onClick={() => setMessage(prompt)}
            className="
              text-xs px-3 py-1.5 rounded-full
              bg-surface border border-border text-muted
              hover:text-foreground hover:border-muted
              transition-colors duration-150
            "
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
