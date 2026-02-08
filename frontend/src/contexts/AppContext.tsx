import React, { createContext, useContext, useReducer, ReactNode, useEffect } from 'react';
import type { AppState, AppAction, FileNode, Message, TabType, CanvasContent, AnalysisStatus, Dataset } from '../types';
import { api } from '../services/api';

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
  expandedFolders: new Set(['datasets', 'outputs']),
  files: mockFiles,
  sidebarCollapsed: false,
  activeTab: 'chart',
  canvasContent: null,
  messages: initialMessages,
  isProcessing: false,
  analysisStatus: 'idle',
  currentDataSource: 'Study ABC-123',
  uploadModalOpen: false,
  datasets: [],
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
  setActiveTab: (tab: TabType) => void;
  sendMessage: (content: string) => void;
  openUploadModal: () => void;
  closeUploadModal: () => void;
  loadDatasets: () => Promise<void>;
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

  // Load datasets on mount
  useEffect(() => {
    loadDatasets();
  }, []);

  return (
    <AppContext.Provider
      value={{
        state,
        dispatch,
        selectFile,
        toggleFolder,
        toggleSidebar,
        setActiveTab,
        sendMessage,
        openUploadModal,
        closeUploadModal,
        loadDatasets,
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
