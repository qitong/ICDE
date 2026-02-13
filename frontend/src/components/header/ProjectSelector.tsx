import { useState, useRef, useEffect } from 'react';
import { FolderOpen, ChevronDown, Plus, Check } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { api } from '../../services/api';

export function ProjectSelector() {
  const { state, switchProject, loadProjects } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Find current project name
  const currentProject = state.projects.find((p) => p.id === state.currentProjectId);
  const currentProjectName = currentProject?.name || 'Select Project';

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setIsCreating(false);
        setNewProjectName('');
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus input when creating
  useEffect(() => {
    if (isCreating && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isCreating]);

  const handleSelectProject = async (projectId: string) => {
    await switchProject(projectId);
    setIsOpen(false);
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim() || isLoading) return;

    setIsLoading(true);
    try {
      const newProject = await api.createProject({ name: newProjectName.trim() });
      await loadProjects();
      await switchProject(newProject.id);
      setNewProjectName('');
      setIsCreating(false);
      setIsOpen(false);
    } catch (error) {
      console.error('Failed to create project:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleCreateProject();
    } else if (e.key === 'Escape') {
      setIsCreating(false);
      setNewProjectName('');
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-surface transition-colors"
      >
        <FolderOpen size={16} className="text-primary" />
        <span className="text-sm font-medium text-foreground max-w-[200px] truncate">
          {currentProjectName}
        </span>
        <ChevronDown
          size={14}
          className={`text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-background border border-border rounded-lg shadow-lg z-50 py-1">
          {/* New project button/input */}
          {isCreating ? (
            <div className="px-2 py-1.5">
              <div className="flex items-center gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Project name..."
                  className="
                    flex-1 h-8 px-2 text-sm
                    bg-surface border border-border rounded-md
                    placeholder:text-muted
                    focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20
                  "
                  disabled={isLoading}
                />
                <button
                  onClick={handleCreateProject}
                  disabled={!newProjectName.trim() || isLoading}
                  className="
                    p-1.5 rounded-md
                    text-primary hover:bg-primary/10
                    disabled:opacity-50 disabled:cursor-not-allowed
                    transition-colors
                  "
                >
                  <Check size={16} />
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setIsCreating(true)}
              className="
                w-full flex items-center gap-2 px-3 py-2
                text-sm text-primary
                hover:bg-surface transition-colors
              "
            >
              <Plus size={16} />
              <span>New Project</span>
            </button>
          )}

          {/* Divider */}
          {state.projects.length > 0 && (
            <div className="h-px bg-border my-1" />
          )}

          {/* Project list */}
          <div className="max-h-64 overflow-y-auto">
            {state.projects.map((project) => (
              <button
                key={project.id}
                onClick={() => handleSelectProject(project.id)}
                className="
                  w-full flex items-center gap-2 px-3 py-2
                  text-sm text-foreground
                  hover:bg-surface transition-colors
                "
              >
                {project.id === state.currentProjectId ? (
                  <Check size={14} className="text-primary" />
                ) : (
                  <span className="w-[14px]" />
                )}
                <span className="truncate">{project.name}</span>
              </button>
            ))}

            {state.projects.length === 0 && !isCreating && (
              <div className="px-3 py-4 text-center text-sm text-muted">
                No projects yet
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
