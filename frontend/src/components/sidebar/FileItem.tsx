
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  Database,
  FileSpreadsheet,
  FileCode,
  FileOutput,
} from 'lucide-react';
import type { FileNode } from '../../types';
import { useApp } from '../../contexts/AppContext';

interface FileItemProps {
  node: FileNode;
  level?: number;
}

export function FileItem({ node, level = 0 }: FileItemProps) {
  const { state, selectFile, toggleFolder } = useApp();
  const isExpanded = state.expandedFolders.has(node.id);
  const isSelected = state.selectedFileId === node.id;

  const getFileIcon = () => {
    if (node.type === 'folder') {
      return isExpanded ? FolderOpen : Folder;
    }

    switch (node.fileType) {
      case 'dataset':
        return Database;
      case 'analysis':
        return FileSpreadsheet;
      case 'script':
        return FileCode;
      case 'output':
        return FileOutput;
      default:
        return FileOutput;
    }
  };

  const FileIcon = getFileIcon();

  const handleClick = () => {
    if (node.type === 'folder') {
      toggleFolder(node.id);
    } else {
      selectFile(node.id);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={`
          w-full flex items-center gap-2 px-2 py-1.5 text-left text-sm
          transition-colors duration-100 rounded-md
          ${isSelected
            ? 'bg-primary/10 text-primary'
            : 'text-foreground hover:bg-surface'
          }
        `}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
      >
        {node.type === 'folder' ? (
          <span className="w-4 h-4 flex items-center justify-center text-muted">
            {isExpanded ? (
              <ChevronDown size={14} strokeWidth={2} />
            ) : (
              <ChevronRight size={14} strokeWidth={2} />
            )}
          </span>
        ) : (
          <span className="w-4" />
        )}
        <FileIcon
          size={16}
          strokeWidth={1.5}
          className={isSelected ? 'text-primary' : 'text-muted'}
        />
        <span className="truncate flex-1">{node.name}</span>
      </button>

      {node.type === 'folder' && isExpanded && node.children && (
        <div className="animate-fade-in">
          {node.children.map((child) => (
            <FileItem key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
