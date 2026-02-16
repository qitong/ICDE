import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Paperclip, Mic, Settings } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { MentionDropdown, MentionTag } from './MentionDropdown';
import type { MentionableItem, MentionRef } from '../../types';
import { getMentionableItems } from '../../services/api';

interface ChatInputProps {
  onOpenSettings?: () => void;
}

export function ChatInput({ onOpenSettings }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [mentions, setMentions] = useState<MentionRef[]>([]);
  const [mentionQuery, setMentionQuery] = useState('');
  const [showMentionDropdown, setShowMentionDropdown] = useState(false);
  const [mentionableItems, setMentionableItems] = useState<MentionableItem[]>([]);
  const [mentionLoading, setMentionLoading] = useState(false);
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);
  const [mentionStartIndex, setMentionStartIndex] = useState(-1);

  const { sendMessage, state } = useApp();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inputContainerRef = useRef<HTMLDivElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [message]);

  // Fetch mentionable items when query changes
  useEffect(() => {
    if (!showMentionDropdown) return;

    const fetchItems = async () => {
      setMentionLoading(true);
      try {
        const result = await getMentionableItems(
          state.currentProjectId || undefined,
          mentionQuery
        );

        // Flatten results
        const items: MentionableItem[] = [
          ...result.datasets.map((d: any) => ({
            type: 'dataset' as const,
            id: d.id,
            name: d.name,
            path: d.path,
            metadata: {
              row_count: d.row_count,
              column_count: d.column_count,
              study_name: d.study_name,
              version_name: d.version_name,
            },
          })),
          ...result.files.map((f: any) => ({
            type: 'file' as const,
            id: f.id,
            name: f.name,
            path: f.path,
            metadata: {
              row_count: f.row_count,
              column_count: f.column_count,
              file_type: f.file_type,
            },
          })),
          ...result.scripts.map((s: any) => ({
            type: 'script' as const,
            id: s.id,
            name: s.display_name || s.name,
            path: s.path,
            metadata: {
              description: s.description,
              language: s.language,
            },
          })),
        ];

        setMentionableItems(items);
        setSelectedMentionIndex(0);
      } catch (error) {
        console.error('Failed to fetch mentionable items:', error);
        setMentionableItems([]);
      } finally {
        setMentionLoading(false);
      }
    };

    const debounceTimer = setTimeout(fetchItems, 150);
    return () => clearTimeout(debounceTimer);
  }, [mentionQuery, showMentionDropdown, state.currentProjectId]);

  // Handle text input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    const cursorPos = e.target.selectionStart;

    setMessage(value);

    // Check for @ mention trigger
    const textBeforeCursor = value.slice(0, cursorPos);
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex !== -1) {
      const textAfterAt = textBeforeCursor.slice(atIndex + 1);
      // Only show dropdown if @ is at start or after whitespace
      const charBeforeAt = atIndex > 0 ? value[atIndex - 1] : ' ';

      if (/\s/.test(charBeforeAt) || atIndex === 0) {
        // Check if there's no space after the @
        if (!/\s/.test(textAfterAt)) {
          setMentionStartIndex(atIndex);
          setMentionQuery(textAfterAt);
          setShowMentionDropdown(true);
          return;
        }
      }
    }

    setShowMentionDropdown(false);
    setMentionStartIndex(-1);
  };

  // Handle mention selection
  const handleSelectMention = useCallback(
    (item: MentionableItem) => {
      // Create mention reference
      const mentionRef: MentionRef = {
        type: item.type,
        id: item.id,
        path: item.path,
        name: item.name,
      };

      // Check for duplicates
      if (!mentions.some((m) => m.id === mentionRef.id)) {
        setMentions([...mentions, mentionRef]);
      }

      // Replace @ query with the mention path in the message
      if (mentionStartIndex !== -1) {
        const beforeAt = message.slice(0, mentionStartIndex);
        const afterQuery = message.slice(
          mentionStartIndex + 1 + mentionQuery.length
        );
        setMessage(beforeAt + item.path + ' ' + afterQuery);
      }

      setShowMentionDropdown(false);
      setMentionStartIndex(-1);
      setMentionQuery('');

      // Focus back on textarea
      textareaRef.current?.focus();
    },
    [mentions, message, mentionStartIndex, mentionQuery]
  );

  // Handle keyboard navigation in mention dropdown
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showMentionDropdown && mentionableItems.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedMentionIndex((prev) =>
          prev < mentionableItems.length - 1 ? prev + 1 : 0
        );
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedMentionIndex((prev) =>
          prev > 0 ? prev - 1 : mentionableItems.length - 1
        );
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        handleSelectMention(mentionableItems[selectedMentionIndex]);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowMentionDropdown(false);
        return;
      }
    }

    // Normal Enter handling (send message)
    if (e.key === 'Enter' && !e.shiftKey && !showMentionDropdown) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Remove a mention
  const removeMention = (index: number) => {
    const mention = mentions[index];
    setMentions(mentions.filter((_, i) => i !== index));

    // Also remove from message text if present
    const newMessage = message.replace(mention.path, '').replace(/\s+/g, ' ').trim();
    setMessage(newMessage);
  };

  const handleSubmit = (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    if (message.trim() && !state.isProcessing) {
      sendMessage(message.trim(), mentions);
      setMessage('');
      setMentions([]);
    }
  };

  // Calculate dropdown position
  const getDropdownPosition = () => {
    return { top: 8, left: 0 };
  };

  return (
    <div className="border-t border-border bg-background p-4">
      {/* Mention tags */}
      {mentions.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {mentions.map((mention, index) => (
            <MentionTag
              key={mention.id}
              mention={mention}
              onRemove={() => removeMention(index)}
            />
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="relative">
        <div
          ref={inputContainerRef}
          className="flex items-end gap-2 bg-surface border border-border rounded-xl p-2 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20 transition-all duration-150"
        >
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
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your data... (use @ to reference files)"
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

          {/* Settings button */}
          {onOpenSettings && (
            <button
              type="button"
              onClick={onOpenSettings}
              className="p-2 text-muted hover:text-foreground rounded-lg hover:bg-border/50 transition-colors"
              title="LLM Settings"
            >
              <Settings size={18} />
            </button>
          )}

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
              ${
                message.trim() && !state.isProcessing
                  ? 'bg-primary text-white hover:bg-primary-hover'
                  : 'bg-border text-muted cursor-not-allowed'
              }
            `}
            title="Send message"
          >
            <Send size={18} />
          </button>
        </div>

        {/* Mention dropdown */}
        <MentionDropdown
          isOpen={showMentionDropdown}
          query={mentionQuery}
          items={mentionableItems}
          loading={mentionLoading}
          position={getDropdownPosition()}
          selectedIndex={selectedMentionIndex}
          onSelect={handleSelectMention}
          onClose={() => setShowMentionDropdown(false)}
        />
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
