import { useState, useEffect } from 'react';
import { MessageList } from '../chat/MessageList';
import { ChatInput } from '../chat/ChatInput';
import { LLMSettingsModal } from '../modals/LLMSettingsModal';
import { Bot, Sparkles, Settings, RefreshCw, ShieldCheck } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { api } from '../../services/api';
import type { HarnessStatus } from '../../types';

export function ChatPanel() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [harnessStatus, setHarnessStatus] = useState<HarnessStatus | null>(null);
  const { clearChat, state } = useApp();

  useEffect(() => {
    let mounted = true;
    api
      .getHarnessStatus()
      .then((status) => {
        if (mounted) setHarnessStatus(status);
      })
      .catch(() => {
        // Ignore status fetch failure when backend is offline
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <aside className="w-[360px] h-full bg-background border-l border-border flex flex-col">
      {/* Panel header */}
      <div className="h-[52px] px-4 flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Bot size={16} className="text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-display font-semibold text-foreground truncate">
              AI Assistant
            </h2>
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <span className="capitalize">{state.currentProvider}</span>
              {harnessStatus?.raw_guard_enabled && (
                <span
                  className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.2 rounded bg-surface border border-border text-muted"
                  title={
                    harnessStatus.available
                      ? `OpenCode Harness active (${harnessStatus.mcp_tools.length} MCP tools) · RAW datasets read-only`
                      : harnessStatus.diagnostic || 'RAW dataset guard active'
                  }
                >
                  <ShieldCheck size={10} className="text-success" />
                  <span>{harnessStatus.available ? 'OpenCode' : 'RAW Guard'}</span>
                </span>
              )}
            </div>
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
