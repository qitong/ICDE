import type { Dataset, DatasetFile, FilePreview } from '../types';

const API_BASE_URL = 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
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

export const api = {
  // Datasets
  async createDataset(name: string, description?: string): Promise<Dataset> {
    const response = await fetch(`${API_BASE_URL}/api/datasets`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, description }),
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
};

export { ApiError };
