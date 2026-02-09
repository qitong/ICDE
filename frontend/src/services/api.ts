import type {
  Dataset,
  DatasetFile,
  FilePreview,
  Script,
  ScriptCreate,
  DeriveDatasetRequest,
  DatasetLineage,
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
}

export const api = {
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

  async deleteScript(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/scripts/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(response);
  },
};

export { ApiError };
