import { createContext, useContext, useReducer, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { AppState, AppAction, FileNode, Message, TabType } from '../types';
import { api } from '../services/api';

// Constants
const STORAGE_KEYS = {
  CURRENT_PROJECT_ID: 'icde_current_project_id',
  SIDEBAR_WIDTH: 'icde_sidebar_width',
};

const DEFAULT_SIDEBAR_WIDTH = 256;
const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 600;

// Helper to get persisted values
function getPersistedProjectId(): string | null {
  return localStorage.getItem(STORAGE_KEYS.CURRENT_PROJECT_ID);
}

function getPersistedSidebarWidth(): number {
  const saved = localStorage.getItem(STORAGE_KEYS.SIDEBAR_WIDTH);
  if (saved) {
    const width = parseInt(saved, 10);
    if (!isNaN(width) && width >= MIN_SIDEBAR_WIDTH && width <= MAX_SIDEBAR_WIDTH) {
      return width;
    }
  }
  return DEFAULT_SIDEBAR_WIDTH;
}

// Mock data for demonstration
const mockFiles: FileNode[] = [
  {
    id: 'datasets',
    name: 'Datasets',
    type: 'folder',
    children: [
      { id: 'ds-1', name: 'ADSL.sas7bdat', type: 'file', fileType: 'dataset' },
      { id: 'ds-2', name: 'ADAE.sas7bdat', type: 'file', fileType: 'dataset' },
      { id: 'ds-3', name: 'ADTTE.sas7bdat', type: 'file', fileType: 'dataset' },
      { id: 'ds-4', name: 'ADVS.sas7bdat', type: 'file', fileType: 'dataset' },
    ],
  },
  {
    id: 'analysis',
    name: 'Analysis Sets',
    type: 'folder',
    children: [
      { id: 'an-1', name: 'Safety Population', type: 'file', fileType: 'analysis' },
      { id: 'an-2', name: 'ITT Population', type: 'file', fileType: 'analysis' },
    ],
  },
  {
    id: 'scripts',
    name: 'Scripts',
    type: 'folder',
    children: [
      { id: 'sc-1', name: 'demographics.R', type: 'file', fileType: 'script' },
      { id: 'sc-2', name: 'efficacy_analysis.py', type: 'file', fileType: 'script' },
    ],
  },
  {
    id: 'outputs',
    name: 'Outputs',
    type: 'folder',
    children: [
      { id: 'out-1', name: 'Table 14.1.1', type: 'file', fileType: 'output' },
      { id: 'out-2', name: 'Figure 14.2.1', type: 'file', fileType: 'output' },
      { id: 'out-3', name: 'Listing 16.1.1', type: 'file', fileType: 'output' },
    ],
  },
];

const initialMessages: Message[] = [
  {
    id: '1',
    role: 'system',
    content: 'Welcome to ICDE. I can help you analyze clinical trial data, generate TLFs (Tables, Listings, Figures), and answer questions about your datasets. How can I assist you today?',
    timestamp: new Date(),
    status: 'complete',
  },
];

const initialState: AppState = {
  selectedFileId: null,
  expandedFolders: new Set(['datasets', 'outputs', 'scripts']),
  files: mockFiles,
  sidebarCollapsed: false,
  sidebarWidth: getPersistedSidebarWidth(),
  activeTab: 'chart',
  canvasContent: null,
  messages: initialMessages,
  isProcessing: false,
  analysisStatus: 'idle',
  currentDataSource: 'Study ABC-123',
  uploadModalOpen: false,
  datasets: [],
  currentProjectId: getPersistedProjectId(),
  projects: [],
  projectTree: null,
  selectedDatasetId: null,
  metadataData: null,
  metadataLoading: false,
  scripts: [],
  selectedScriptId: null,
  selectedFilePreview: null,
  filePreviewData: null,
  filePreviewLoading: false,
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SELECT_FILE':
      return { ...state, selectedFileId: action.payload };
    case 'TOGGLE_FOLDER': {
      const newExpanded = new Set(state.expandedFolders);
      if (newExpanded.has(action.payload)) {
        newExpanded.delete(action.payload);
      } else {
        newExpanded.add(action.payload);
      }
      return { ...state, expandedFolders: newExpanded };
    }
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed };
    case 'SET_SIDEBAR_WIDTH':
      return { ...state, sidebarWidth: action.payload };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'SET_CANVAS_CONTENT':
      return { ...state, canvasContent: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_PROCESSING':
      return { ...state, isProcessing: action.payload };
    case 'SET_ANALYSIS_STATUS':
      return { ...state, analysisStatus: action.payload };
    case 'SET_DATA_SOURCE':
      return { ...state, currentDataSource: action.payload };
    case 'SET_UPLOAD_MODAL_OPEN':
      return { ...state, uploadModalOpen: action.payload };
    case 'SET_DATASETS':
      return { ...state, datasets: action.payload };
    case 'ADD_DATASET':
      return { ...state, datasets: [action.payload, ...state.datasets] };
    case 'SET_CURRENT_PROJECT':
      return { ...state, currentProjectId: action.payload };
    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };
    case 'SET_PROJECT_TREE':
      return { ...state, projectTree: action.payload };
    case 'SET_SELECTED_DATASET':
      return { ...state, selectedDatasetId: action.payload };
    case 'SET_METADATA_DATA':
      return { ...state, metadataData: action.payload };
    case 'SET_METADATA_LOADING':
      return { ...state, metadataLoading: action.payload };
    case 'SET_SCRIPTS':
      return { ...state, scripts: action.payload };
    case 'SET_SELECTED_SCRIPT':
      return { ...state, selectedScriptId: action.payload };
    case 'SET_SELECTED_FILE_PREVIEW':
      return { ...state, selectedFilePreview: action.payload };
    case 'SET_FILE_PREVIEW_DATA':
      return { ...state, filePreviewData: action.payload };
    case 'SET_FILE_PREVIEW_LOADING':
      return { ...state, filePreviewLoading: action.payload };
    default:
      return state;
  }
}

interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  // Convenience functions
  selectFile: (id: string) => void;
  toggleFolder: (id: string) => void;
  toggleSidebar: () => void;
  setSidebarWidth: (width: number) => void;
  setActiveTab: (tab: TabType) => void;
  sendMessage: (content: string) => void;
  openUploadModal: () => void;
  closeUploadModal: () => void;
  loadDatasets: () => Promise<void>;
  loadProjects: () => Promise<void>;
  switchProject: (projectId: string | null) => Promise<void>;
  loadProjectTree: () => Promise<void>;
  viewDatasetMetadata: (datasetId: string) => Promise<void>;
  loadScripts: () => Promise<void>;
  viewScript: (scriptId: string) => void;
  updateScript: (scriptId: string, data: Partial<import('../types').ScriptCreate>) => Promise<void>;
  createScript: (data: import('../types').ScriptCreate) => Promise<import('../types').Script>;
  deleteScript: (scriptId: string) => Promise<void>;
  viewFile: (datasetId: string, fileId: string, fileName: string, fileType: string) => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const selectFile = (id: string) => {
    dispatch({ type: 'SELECT_FILE', payload: id });
  };

  const toggleFolder = (id: string) => {
    dispatch({ type: 'TOGGLE_FOLDER', payload: id });
  };

  const toggleSidebar = () => {
    dispatch({ type: 'TOGGLE_SIDEBAR' });
  };

  const setSidebarWidth = (width: number) => {
    const clampedWidth = Math.min(Math.max(width, MIN_SIDEBAR_WIDTH), MAX_SIDEBAR_WIDTH);
    dispatch({ type: 'SET_SIDEBAR_WIDTH', payload: clampedWidth });
    localStorage.setItem(STORAGE_KEYS.SIDEBAR_WIDTH, clampedWidth.toString());
  };

  const setActiveTab = (tab: TabType) => {
    dispatch({ type: 'SET_ACTIVE_TAB', payload: tab });
  };

  const sendMessage = (content: string) => {
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'complete',
    };
    dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
    dispatch({ type: 'SET_PROCESSING', payload: true });

    // Simulate AI response after delay
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateMockResponse(content),
        timestamp: new Date(),
        status: 'complete',
      };
      dispatch({ type: 'ADD_MESSAGE', payload: aiMessage });
      dispatch({ type: 'SET_PROCESSING', payload: false });
    }, 1500);
  };

  const openUploadModal = () => {
    dispatch({ type: 'SET_UPLOAD_MODAL_OPEN', payload: true });
  };

  const closeUploadModal = () => {
    dispatch({ type: 'SET_UPLOAD_MODAL_OPEN', payload: false });
  };

  const loadDatasets = async () => {
    try {
      const datasets = await api.listDatasets();
      dispatch({ type: 'SET_DATASETS', payload: datasets });
    } catch (error) {
      console.error('Failed to load datasets:', error);
    }
  };

  const loadProjects = async () => {
    try {
      const projects = await api.listProjects();
      dispatch({ type: 'SET_PROJECTS', payload: projects });

      // Auto-select first project if none selected
      if (!state.currentProjectId && projects.length > 0) {
        await switchProject(projects[0].id);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const switchProject = async (projectId: string | null) => {
    dispatch({ type: 'SET_CURRENT_PROJECT', payload: projectId });
    dispatch({ type: 'SET_PROJECT_TREE', payload: null });

    if (projectId) {
      localStorage.setItem(STORAGE_KEYS.CURRENT_PROJECT_ID, projectId);
      // Load project tree
      try {
        const tree = await api.getProjectTree(projectId);
        dispatch({ type: 'SET_PROJECT_TREE', payload: tree });
      } catch (error) {
        console.error('Failed to load project tree:', error);
      }
    } else {
      localStorage.removeItem(STORAGE_KEYS.CURRENT_PROJECT_ID);
    }
  };

  const loadProjectTree = async () => {
    if (!state.currentProjectId) return;

    try {
      const tree = await api.getProjectTree(state.currentProjectId);
      dispatch({ type: 'SET_PROJECT_TREE', payload: tree });
    } catch (error) {
      console.error('Failed to load project tree:', error);
    }
  };

  const viewDatasetMetadata = async (datasetId: string) => {
    dispatch({ type: 'SET_SELECTED_DATASET', payload: datasetId });
    dispatch({ type: 'SET_METADATA_LOADING', payload: true });
    dispatch({ type: 'SET_ACTIVE_TAB', payload: 'metadata' });

    try {
      const metadataData = await api.getDatasetLineage(datasetId);
      dispatch({ type: 'SET_METADATA_DATA', payload: metadataData });
    } catch (error) {
      console.error('Failed to load metadata:', error);
      dispatch({ type: 'SET_METADATA_DATA', payload: null });
    } finally {
      dispatch({ type: 'SET_METADATA_LOADING', payload: false });
    }
  };

  const loadScripts = async () => {
    try {
      const scripts = await api.listScripts();
      dispatch({ type: 'SET_SCRIPTS', payload: scripts });
    } catch (error) {
      console.error('Failed to load scripts:', error);
    }
  };

  const viewScript = (scriptId: string) => {
    dispatch({ type: 'SET_SELECTED_SCRIPT', payload: scriptId });
    dispatch({ type: 'SET_ACTIVE_TAB', payload: 'script' });
  };

  const updateScript = async (scriptId: string, data: Partial<import('../types').ScriptCreate>) => {
    try {
      const updatedScript = await api.updateScript(scriptId, data);
      // Update the script in the local state
      const updatedScripts = state.scripts.map((s) =>
        s.id === scriptId ? updatedScript : s
      );
      dispatch({ type: 'SET_SCRIPTS', payload: updatedScripts });
    } catch (error) {
      console.error('Failed to update script:', error);
      throw error;
    }
  };

  const createScript = async (data: import('../types').ScriptCreate) => {
    try {
      const newScript = await api.createScript(data);
      dispatch({ type: 'SET_SCRIPTS', payload: [newScript, ...state.scripts] });
      return newScript;
    } catch (error) {
      console.error('Failed to create script:', error);
      throw error;
    }
  };

  const deleteScript = async (scriptId: string) => {
    try {
      await api.deleteScript(scriptId);
      const updatedScripts = state.scripts.filter((s) => s.id !== scriptId);
      dispatch({ type: 'SET_SCRIPTS', payload: updatedScripts });
      // Clear selection if deleted script was selected
      if (state.selectedScriptId === scriptId) {
        dispatch({ type: 'SET_SELECTED_SCRIPT', payload: null });
      }
    } catch (error) {
      console.error('Failed to delete script:', error);
      throw error;
    }
  };

  const viewFile = async (datasetId: string, fileId: string, fileName: string, fileType: string) => {
    dispatch({ type: 'SET_SELECTED_FILE_PREVIEW', payload: { datasetId, fileId, fileName, fileType } });
    dispatch({ type: 'SET_FILE_PREVIEW_LOADING', payload: true });
    dispatch({ type: 'SET_ACTIVE_TAB', payload: 'file' });

    try {
      // Only fetch preview for tabular file types
      const tabularTypes = ['xlsx', 'xls', 'csv'];
      if (tabularTypes.includes(fileType.toLowerCase())) {
        const previewData = await api.getFilePreview(datasetId, fileId);
        dispatch({ type: 'SET_FILE_PREVIEW_DATA', payload: previewData });
      } else {
        dispatch({ type: 'SET_FILE_PREVIEW_DATA', payload: null });
      }
    } catch (error) {
      console.error('Failed to load file preview:', error);
      dispatch({ type: 'SET_FILE_PREVIEW_DATA', payload: null });
    } finally {
      dispatch({ type: 'SET_FILE_PREVIEW_LOADING', payload: false });
    }
  };

  // Load datasets, projects, and scripts on mount
  useEffect(() => {
    loadDatasets();
    loadProjects();
    loadScripts();
  }, []);

  // Load project tree when current project changes
  useEffect(() => {
    if (state.currentProjectId) {
      loadProjectTree();
    }
  }, [state.currentProjectId]);

  return (
    <AppContext.Provider
      value={{
        state,
        dispatch,
        selectFile,
        toggleFolder,
        toggleSidebar,
        setSidebarWidth,
        setActiveTab,
        sendMessage,
        openUploadModal,
        closeUploadModal,
        loadDatasets,
        loadProjects,
        switchProject,
        loadProjectTree,
        viewDatasetMetadata,
        loadScripts,
        viewScript,
        updateScript,
        createScript,
        deleteScript,
        viewFile,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}

// Helper function to generate mock responses
function generateMockResponse(userMessage: string): string {
  const lowerMessage = userMessage.toLowerCase();

  if (lowerMessage.includes('demographic') || lowerMessage.includes('baseline')) {
    return 'I\'ve analyzed the demographic data from ADSL. The study includes 450 subjects with a mean age of 58.3 years (SD: 12.1). The gender distribution is 52% male and 48% female. Would you like me to generate a detailed demographics table (Table 14.1.1)?';
  }

  if (lowerMessage.includes('adverse') || lowerMessage.includes('safety')) {
    return 'Based on ADAE, there were 1,234 adverse events reported across 312 subjects (69.3%). The most common AEs were headache (15.2%), nausea (12.8%), and fatigue (11.4%). Shall I create a summary of adverse events by system organ class?';
  }

  if (lowerMessage.includes('efficacy') || lowerMessage.includes('endpoint')) {
    return 'The primary efficacy analysis shows a statistically significant difference between treatment groups (p < 0.001). The treatment effect estimate is -2.45 (95% CI: -3.12, -1.78). Would you like me to generate the efficacy figures?';
  }

  if (lowerMessage.includes('table') || lowerMessage.includes('generate')) {
    return 'I can generate that table for you. Based on the SAP specifications, I\'ll use the ITT population and apply the standard formatting. The table will be ready in the Outputs folder once generated. Should I proceed?';
  }

  return 'I understand your request. Let me analyze the relevant datasets and prepare the output. Is there a specific format or population you\'d like me to focus on?';
}
