// File Tree Types
export interface FileNode {
  id: string;
  name: string;
  type: 'folder' | 'file';
  icon?: string;
  children?: FileNode[];
  fileType?: 'dataset' | 'analysis' | 'script' | 'output';
}

// Message Types
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'pending' | 'complete' | 'error';
}

// Tab Types
export type TabType = 'chart' | 'table' | 'text' | 'code';

export interface Tab {
  id: string;
  type: TabType;
  label: string;
  isActive: boolean;
}

// Canvas Content Types
export interface CanvasContent {
  type: TabType;
  data: unknown;
}

// Analysis Status
export type AnalysisStatus = 'idle' | 'running' | 'complete' | 'error';

// App State
export interface AppState {
  // File navigation
  selectedFileId: string | null;
  expandedFolders: Set<string>;
  files: FileNode[];
  sidebarCollapsed: boolean;

  // Workspace
  activeTab: TabType;
  canvasContent: CanvasContent | null;

  // Chat
  messages: Message[];
  isProcessing: boolean;

  // Analysis
  analysisStatus: AnalysisStatus;
  currentDataSource: string;

  // Upload
  uploadModalOpen: boolean;
  datasets: Dataset[];
}

// Action Types
export type AppAction =
  | { type: 'SELECT_FILE'; payload: string }
  | { type: 'TOGGLE_FOLDER'; payload: string }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_ACTIVE_TAB'; payload: TabType }
  | { type: 'SET_CANVAS_CONTENT'; payload: CanvasContent }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'SET_PROCESSING'; payload: boolean }
  | { type: 'SET_ANALYSIS_STATUS'; payload: AnalysisStatus }
  | { type: 'SET_DATA_SOURCE'; payload: string }
  | { type: 'SET_UPLOAD_MODAL_OPEN'; payload: boolean }
  | { type: 'SET_DATASETS'; payload: Dataset[] }
  | { type: 'ADD_DATASET'; payload: Dataset };

// Export Types
export type ExportFormat = 'word' | 'pdf';

// Dataset Types
export type DatasetType = 'RAW' | 'DERIVED';

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  type: DatasetType;
  file_count: number;
  total_size: number;
  row_count: number | null;
  column_count: number | null;
  files?: DatasetFile[];
  // Version lineage (time dimension)
  parent_dataset_id: string | null;
  crf_version: string | null;
  // Derivation lineage (logic dimension)
  source_dataset_id: string | null;
  script_id: string | null;
  // Patient identifier
  patient_id_column: string | null;
  // Stale state
  is_stale: boolean;
  stale_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetFile {
  id: string;
  file_name: string;
  original_name: string;
  file_type: string;
  file_size: number;
  row_count: number | null;
  column_count: number | null;
  parse_status: 'pending' | 'parsed' | 'error';
  parse_error: string | null;
  created_at: string;
}

export interface ColumnInfo {
  name: string;
  data_type: 'numeric' | 'categorical' | 'date' | 'text';
  non_null_count: number;
  unique_count: number;
  sample_values: string[];
}

export interface FilePreview {
  file_id: string;
  file_name: string;
  row_count: number;
  column_count: number;
  columns: ColumnInfo[];
  sample_rows: Record<string, unknown>[];
}

// Script Types
export interface Script {
  id: string;
  name: string;
  display_name: string;
  description: string;
  code: string;
  keywords: string[] | null;
  language: string;
  input_requirements: string | null;
  output_description: string | null;
  created_by: 'user' | 'llm';
  created_from_prompt: string | null;
  usage_count: number;
  last_used_at: string | null;
  version: number;
  parent_script_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScriptCreate {
  name: string;
  display_name: string;
  description: string;
  code: string;
  keywords?: string[];
  language?: string;
  input_requirements?: string;
  output_description?: string;
  created_by?: 'user' | 'llm';
  created_from_prompt?: string;
}

export interface DeriveDatasetRequest {
  script_id: string;
  output_name: string;
}

// Lineage Types
export interface LineageNode {
  id: string;
  name: string;
  type: DatasetType;
  relationship: 'version_parent' | 'version_child' | 'derivation_source' | 'derived';
}

export interface DatasetLineage {
  dataset: {
    id: string;
    name: string;
    type: DatasetType;
  };
  ancestors: LineageNode[];
  descendants: LineageNode[];
}
