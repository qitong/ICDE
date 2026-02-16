import { useState } from 'react';
import { MessageList } from '../chat/MessageList';
import { ChatInput } from '../chat/ChatInput';
import { LLMSettingsModal } from '../modals/LLMSettingsModal';
import { Bot, Sparkles, Settings, RefreshCw } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';

export function ChatPanel() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { clearChat, state } = useApp();

  return (
    <aside className="w-[360px] h-full bg-background border-l border-border flex flex-col">
      {/* Panel header */}
      <div className="h-[52px] px-4 flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <Bot size={16} className="text-primary" />
          </div>
          <div>
            <h2 className="text-sm font-display font-semibold text-foreground">
              AI Assistant
            </h2>
            <p className="text-xs text-muted capitalize">{state.currentProvider}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearChat}
            className="p-2 text-muted hover:text-foreground hover:bg-surface rounded-lg transition-colors"
            title="New conversation"
          >
            <RefreshCw size={16} />
          </button>
          <button
            className="p-2 text-muted hover:text-foreground hover:bg-surface rounded-lg transition-colors"
            title="Capabilities"
          >
            <Sparkles size={16} />
          </button>
          <button
            onClick={() => setSettingsOpen(true)}
            className="p-2 text-muted hover:text-foreground hover:bg-surface rounded-lg transition-colors"
            title="LLM Settings"
          >
            <Settings size={16} />
          </button>
        </div>
      </div>

      {/* Messages area */}
      <MessageList />

      {/* Input area */}
      <ChatInput onOpenSettings={() => setSettingsOpen(true)} />

      {/* Settings modal */}
      <LLMSettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </aside>
  );
}
