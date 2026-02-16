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
export type TabType = 'content' | 'metadata';

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
  sidebarWidth: number;

  // Workspace
  activeTab: TabType;
  canvasContent: CanvasContent | null;

  // Chat
  messages: Message[];
  isProcessing: boolean;
  currentConversationId: string | null;
  currentProvider: string;

  // Analysis
  analysisStatus: AnalysisStatus;
  currentDataSource: string;

  // Upload
  uploadModalOpen: boolean;
  datasets: Dataset[];

  // Projects
  currentProjectId: string | null;
  projects: Project[];
  projectTree: ProjectTree | null;

  // Lineage
  selectedDatasetId: string | null;
  metadataData: DatasetMetadata | null;
  metadataLoading: boolean;

  // Scripts
  scripts: Script[];
  selectedScriptId: string | null;

  // File Preview
  selectedFilePreview: {
    datasetId: string;
    fileId: string;
    fileName: string;
    fileType: string;
  } | null;
  filePreviewData: FilePreview | null;
  filePreviewLoading: boolean;
}

// Action Types
export type AppAction =
  | { type: 'SELECT_FILE'; payload: string }
  | { type: 'TOGGLE_FOLDER'; payload: string }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_SIDEBAR_WIDTH'; payload: number }
  | { type: 'SET_ACTIVE_TAB'; payload: TabType }
  | { type: 'SET_CANVAS_CONTENT'; payload: CanvasContent }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_LAST_MESSAGE'; payload: { content: string } }
  | { type: 'SET_PROCESSING'; payload: boolean }
  | { type: 'SET_CONVERSATION_ID'; payload: string | null }
  | { type: 'SET_PROVIDER'; payload: string }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'SET_ANALYSIS_STATUS'; payload: AnalysisStatus }
  | { type: 'SET_DATA_SOURCE'; payload: string }
  | { type: 'SET_UPLOAD_MODAL_OPEN'; payload: boolean }
  | { type: 'SET_DATASETS'; payload: Dataset[] }
  | { type: 'ADD_DATASET'; payload: Dataset }
  | { type: 'SET_CURRENT_PROJECT'; payload: string | null }
  | { type: 'SET_PROJECTS'; payload: Project[] }
  | { type: 'SET_PROJECT_TREE'; payload: ProjectTree | null }
  | { type: 'SET_SELECTED_DATASET'; payload: string | null }
  | { type: 'SET_METADATA_DATA'; payload: DatasetMetadata | null }
  | { type: 'SET_METADATA_LOADING'; payload: boolean }
  | { type: 'SET_SCRIPTS'; payload: Script[] }
  | { type: 'SET_SELECTED_SCRIPT'; payload: string | null }
  | { type: 'SET_SELECTED_FILE_PREVIEW'; payload: { datasetId: string; fileId: string; fileName: string; fileType: string } | null }
  | { type: 'SET_FILE_PREVIEW_DATA'; payload: FilePreview | null }
  | { type: 'SET_FILE_PREVIEW_LOADING'; payload: boolean };

// Export Types
export type ExportFormat = 'word' | 'pdf';

// Project Types
export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface DatasetSummary {
  id: string;
  name: string;
  type: string;
  file_count: number;
  created_at: string;
}

export interface StudyVersion {
  name: string;
  datasets: DatasetSummary[];
}

export interface Study {
  name: string;
  versions: StudyVersion[];
}

export interface ProjectTree {
  project_id: string;
  project_name: string;
  studies: Study[];
}

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
  // Manual upload flag (自建)
  is_manual: boolean;
  // Project and hierarchy
  project_id: string | null;
  study_name: string | null;
  version_name: string | null;
  created_at: string;
  updated_at: string;
}

// Relationship types for dataset upload
export type RelationshipType = 'none' | 'version' | 'derived';

export interface SetRelationshipRequest {
  relationship_type: RelationshipType;
  parent_dataset_id?: string;
  source_dataset_id?: string;
  version_name?: string;
  is_manual?: boolean;
  description?: string;
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

// Parameter property for function parameters
export interface ParameterProperty {
  type: string;  // DataFrame, string, int, float, list, dict, etc.
  description: string;
  enum?: string[];  // For categorical parameters
  default?: unknown;
  items?: Record<string, unknown>;  // For array types
}

// JSON Schema format for function parameters (OpenAI-compatible)
export interface ParametersSchema {
  type: string;  // "object"
  properties: Record<string, ParameterProperty>;
  required: string[];
}

// Schema for function return value
export interface ReturnsSchema {
  type: string;  // DataFrame, dict, list, int, etc.
  description: string;
  properties?: Record<string, unknown>;
}

// Function definition within a script
export interface FunctionDefinition {
  name: string;
  description: string;
  is_main: boolean;
}

// Example of how to call the script
export interface ExampleCall {
  input: string;
  output: string;
  description?: string;
}

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
  // Structured metadata for LLM tool calling
  parameters_schema: ParametersSchema | null;
  returns_schema: ReturnsSchema | null;
  functions: FunctionDefinition[] | null;
  use_cases: string[] | null;
  example_calls: ExampleCall[] | null;
  // Origin and stats
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
  // Structured metadata for LLM tool calling
  parameters_schema?: ParametersSchema;
  returns_schema?: ReturnsSchema;
  functions?: FunctionDefinition[];
  use_cases?: string[];
  example_calls?: ExampleCall[];
}

export interface DeriveDatasetRequest {
  script_id: string;
  output_name: string;
}

// Metadata Types (Dataset relationships)
export interface RelatedDataset {
  id: string;
  name: string;
  type: DatasetType;
  relationship: 'version_parent' | 'version_child' | 'derivation_source' | 'derived';
}

export interface DatasetMetadata {
  dataset: {
    id: string;
    name: string;
    type: DatasetType;
  };
  ancestors: RelatedDataset[];
  descendants: RelatedDataset[];
}

// Legacy alias for backward compatibility
export type DatasetLineage = DatasetMetadata;
export type LineageNode = RelatedDataset;

// ============== Chat Types ==============

// Mention reference for @ mentions in chat
export interface MentionRef {
  type: 'dataset' | 'file' | 'script';
  id: string;
  path: string;
  name?: string;
  metadata?: Record<string, unknown>;
}

// Mentionable item returned from API
export interface MentionableItem {
  type: 'dataset' | 'file' | 'script';
  id: string;
  name: string;
  path: string;
  metadata?: {
    row_count?: number;
    column_count?: number;
    study_name?: string;
    version_name?: string;
    file_type?: string;
    description?: string;
    language?: string;
  };
}

// Chat request sent to API
export interface ChatRequest {
  message: string;
  mentions?: MentionRef[];
  conversation_id?: string;
  provider?: string;
  project_id?: string;
  stream?: boolean;
}

// Chat response from API (non-streaming)
export interface ChatResponse {
  message: string;
  conversation_id: string;
  message_id: string;
  provider: string;
  model?: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

// Stream chunk from SSE
export interface StreamChunk {
  type: 'content' | 'done' | 'error';
  content?: string;
  conversation_id?: string;
  message_id?: string;
  error?: string;
}

// Conversation summary
export interface Conversation {
  id: string;
  title?: string;
  project_id?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

// Conversation with messages
export interface ConversationWithMessages extends Conversation {
  messages: ChatMessage[];
}

// Individual chat message from API
export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  mentions?: MentionRef[];
  provider?: string;
  model?: string;
  tokens_used?: number;
  status: string;
  error_message?: string;
  created_at: string;
}

// ============== LLM Settings Types ==============

// Provider configuration
export interface ProviderConfig {
  provider: string;
  display_name: string;
  api_key?: string;
  api_key_set: boolean;
  api_base_url?: string;
  model: string;
  enabled: boolean;
  is_default: boolean;
  available_models: string[];
}

// LLM settings response
export interface LLMSettings {
  default_provider?: string;
  providers: ProviderConfig[];
}

// Update for a single provider
export interface LLMSettingUpdate {
  api_key?: string;
  api_base_url?: string;
  model?: string;
  enabled?: boolean;
  is_default?: boolean;
}

// Update for all LLM settings
export interface LLMSettingsUpdate {
  default_provider?: string;
  providers: Record<string, LLMSettingUpdate>;
}

// API key validation result
export interface ApiKeyValidation {
  provider: string;
  valid: boolean;
  message: string;
}
