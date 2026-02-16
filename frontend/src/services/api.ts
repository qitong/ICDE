import type {
  Dataset,
  DatasetFile,
  FilePreview,
  Script,
  ScriptCreate,
  DeriveDatasetRequest,
  DatasetLineage,
  Project,
  ProjectCreate,
  ProjectTree,
  SetRelationshipRequest,
  ChatRequest,
  ChatResponse,
  StreamChunk,
  Conversation,
  ConversationWithMessages,
  LLMSettings,
  LLMSettingsUpdate,
  ApiKeyValidation,
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || `HTTP error ${response.status}`
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

interface CreateDatasetOptions {
  name: string;
  description?: string;
  parent_dataset_id?: string;
  crf_version?: string;
  patient_id_column?: string;
  project_id?: string;
  study_name?: string;
  version_name?: string;
}

export const api = {
  // Projects
  async createProject(project: ProjectCreate): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/api/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(project),
    });
    return handleResponse<Project>(response);
  },

  async listProjects(): Promise<Project[]> {
    const response = await fetch(`${API_BASE_URL}/api/projects`);
    return handleResponse<Project[]>(response);
  },

  async getProject(id: string): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/api/projects/${id}`);
    return handleResponse<Project>(response);
  },

  async updateProject(id: string, data: Partial<ProjectCreate>): Promise<Project> {
    const response = await fetch(`${API_BASE_URL}/api/projects/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return handleResponse<Project>(response);
  },

  async deleteProject(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/projects/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(response);
  },

  async getProjectTree(projectId: string): Promise<ProjectTree> {
    const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/tree`);
    return handleResponse<ProjectTree>(response);
  },

  // Datasets
  async createDataset(options: CreateDatasetOptions): Promise<Dataset> {
    const response = await fetch(`${API_BASE_URL}/api/datasets`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(options),
    });
    return handleResponse<Dataset>(response);
  },

  async listDatasets(): Promise<Dataset[]> {
    const response = await fetch(`${API_BASE_URL}/api/datasets`);
    return handleResponse<Dataset[]>(response);
  },

  async getDataset(id: string): Promise<Dataset> {
    const response = await fetch(`${API_BASE_URL}/api/datasets/${id}`);
    return handleResponse<Dataset>(response);
  },

  async deleteDataset(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/datasets/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(response);
  },

  async setDatasetRelationship(
    datasetId: string,
    request: SetRelationshipRequest
  ): Promise<Dataset> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/relationship`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );
    return handleResponse<Dataset>(response);
  },

  // Files
  async uploadFiles(datasetId: string, files: File[]): Promise<DatasetFile[]> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/files`,
      {
        method: 'POST',
        body: formData,
      }
    );
    return handleResponse<DatasetFile[]>(response);
  },

  async getFilePreview(datasetId: string, fileId: string): Promise<FilePreview> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/files/${fileId}/preview`
    );
    return handleResponse<FilePreview>(response);
  },

  async reparseFile(datasetId: string, fileId: string): Promise<DatasetFile> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/files/${fileId}/reparse`,
      { method: 'POST' }
    );
    return handleResponse<DatasetFile>(response);
  },

  async reparseAllFiles(datasetId: string): Promise<DatasetFile[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/reparse-all`,
      { method: 'POST' }
    );
    return handleResponse<DatasetFile[]>(response);
  },

  // Dataset Versioning
  async getDatasetVersions(datasetId: string): Promise<Dataset[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/versions`
    );
    return handleResponse<Dataset[]>(response);
  },

  // Dataset Derivation
  async deriveDataset(
    sourceDatasetId: string,
    request: DeriveDatasetRequest
  ): Promise<Dataset> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${sourceDatasetId}/derive`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }
    );
    return handleResponse<Dataset>(response);
  },

  async getDerivedDatasets(datasetId: string): Promise<Dataset[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/derived`
    );
    return handleResponse<Dataset[]>(response);
  },

  // Dataset Lineage
  async getDatasetLineage(datasetId: string): Promise<DatasetLineage> {
    const response = await fetch(
      `${API_BASE_URL}/api/datasets/${datasetId}/lineage`
    );
    return handleResponse<DatasetLineage>(response);
  },

  // Scripts
  async createScript(script: ScriptCreate): Promise<Script> {
    const response = await fetch(`${API_BASE_URL}/api/scripts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(script),
    });
    return handleResponse<Script>(response);
  },

  async listScripts(): Promise<Script[]> {
    const response = await fetch(`${API_BASE_URL}/api/scripts`);
    return handleResponse<Script[]>(response);
  },

  async getScript(id: string): Promise<Script> {
    const response = await fetch(`${API_BASE_URL}/api/scripts/${id}`);
    return handleResponse<Script>(response);
  },

  async searchScripts(query: string): Promise<Script[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/scripts/search?q=${encodeURIComponent(query)}`
    );
    return handleResponse<Script[]>(response);
  },

  async updateScript(id: string, data: Partial<ScriptCreate>): Promise<Script> {
    const response = await fetch(`${API_BASE_URL}/api/scripts/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return handleResponse<Script>(response);
  },

  async deleteScript(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/scripts/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(response);
  },

  // ============== Chat ==============

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    return handleResponse<ChatResponse>(response);
  },

  async listConversations(projectId?: string, limit = 50): Promise<Conversation[]> {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    params.append('limit', String(limit));

    const response = await fetch(
      `${API_BASE_URL}/api/chat/conversations?${params}`
    );
    return handleResponse<Conversation[]>(response);
  },

  async getConversation(conversationId: string): Promise<ConversationWithMessages> {
    const response = await fetch(
      `${API_BASE_URL}/api/chat/conversations/${conversationId}`
    );
    return handleResponse<ConversationWithMessages>(response);
  },

  async deleteConversation(conversationId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/api/chat/conversations/${conversationId}`,
      { method: 'DELETE' }
    );
    return handleResponse<void>(response);
  },

  // ============== LLM Settings ==============

  async getLLMSettings(): Promise<LLMSettings> {
    const response = await fetch(`${API_BASE_URL}/api/settings/llm`);
    return handleResponse<LLMSettings>(response);
  },

  async updateLLMSettings(settings: LLMSettingsUpdate): Promise<LLMSettings> {
    const response = await fetch(`${API_BASE_URL}/api/settings/llm`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(settings),
    });
    return handleResponse<LLMSettings>(response);
  },

  async validateLLMApiKey(provider: string): Promise<ApiKeyValidation> {
    const response = await fetch(
      `${API_BASE_URL}/api/settings/llm/${provider}/validate`,
      { method: 'POST' }
    );
    return handleResponse<ApiKeyValidation>(response);
  },
};

// ============== Streaming Chat ==============

export async function* streamChatMessage(
  request: ChatRequest
): AsyncGenerator<StreamChunk, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || `HTTP error ${response.status}`
    );
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data) {
            try {
              const chunk = JSON.parse(data) as StreamChunk;
              yield chunk;
            } catch (e) {
              console.error('Failed to parse SSE data:', data, e);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ============== Mentionable Items ==============

export async function getMentionableItems(
  projectId?: string,
  query?: string
): Promise<{
  datasets: any[];
  files: any[];
  scripts: any[];
}> {
  const params = new URLSearchParams();
  if (projectId) params.append('project_id', projectId);
  if (query) params.append('query', query);

  const response = await fetch(
    `${API_BASE_URL}/api/chat/mentionables?${params}`
  );
  return handleResponse<{
    datasets: any[];
    files: any[];
    scripts: any[];
  }>(response);
}

export { ApiError };
