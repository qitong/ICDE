import { useCallback } from 'react';
import { Sidebar, MainWorkspace, ChatPanel } from './components/layout';
import { UploadModal } from './components/upload';
import { ProjectSelector } from './components/header';
import { Bell, HelpCircle, User } from 'lucide-react';
import { useApp } from './contexts/AppContext';

function Header() {
  const { state } = useApp();

  return (
    <header className="h-[52px] border-b border-border bg-background flex items-center justify-between px-4">
      {/* Left: Logo & branding */}
      <div className="flex items-center gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-white font-display font-bold text-sm">IC</span>
          </div>
          <span className="font-display font-semibold text-foreground text-lg tracking-tight">
            ICDE
          </span>
        </div>

        {/* Divider */}
        <div className="w-px h-6 bg-border" />

        {/* Project selector */}
        <ProjectSelector />
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        {/* Analysis status */}
        <div className="flex items-center gap-2 px-3 py-1.5 mr-2">
          <div className={`w-2 h-2 rounded-full ${
            state.analysisStatus === 'running'
              ? 'bg-warning animate-pulse'
              : state.analysisStatus === 'complete'
              ? 'bg-success'
              : 'bg-border'
          }`} />
          <span className="text-xs text-muted capitalize">
            {state.analysisStatus === 'idle' ? 'Ready' : state.analysisStatus}
          </span>
        </div>

        <button className="p-2 text-muted hover:text-foreground hover:bg-surface rounded-lg transition-colors">
          <HelpCircle size={18} />
        </button>
        <button className="p-2 text-muted hover:text-foreground hover:bg-surface rounded-lg transition-colors relative">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full" />
        </button>
        <div className="w-px h-6 bg-border mx-2" />
        <button className="flex items-center gap-2 p-1.5 hover:bg-surface rounded-lg transition-colors">
          <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center">
            <User size={16} className="text-primary" />
          </div>
        </button>
      </div>
    </header>
  );
}

function App() {
  const { state, closeUploadModal, loadDatasets } = useApp();

  const handleUploadComplete = useCallback(async () => {
    // Refresh datasets list
    await loadDatasets();
  }, [loadDatasets]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      {/* Header */}
      <Header />

      {/* Main content area with three panels */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - File navigation */}
        <Sidebar />

        {/* Middle - Main workspace */}
        <MainWorkspace />

        {/* Right - Chat panel */}
        <ChatPanel />
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={state.uploadModalOpen}
        onClose={closeUploadModal}
        onUploadComplete={handleUploadComplete}
      />
    </div>
  );
}

export default App;
