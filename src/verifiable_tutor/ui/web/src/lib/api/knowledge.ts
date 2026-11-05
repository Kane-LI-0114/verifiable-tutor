import { apiFetch } from "./client";

/** One folder in the knowledge-base tree, with its ancestor path. */
export interface KnowledgeFolder {
  id: string;
  name: string;
  parent_id: string | null;
  position: number;
  created_at: string;
  file_count: number;
  path: { id: string; name: string }[];
}

/** One course document: the file tile and the info pane both render this. */
export interface KnowledgeDocument {
  id: string;
  title: string;
  filename: string;
  folder_id: string | null;
  page_count: number;
  chunk_count: number;
  byte_size: number | null;
  status:
    | "uploading"
    | "uploaded"
    | "upload_failed"
    | "processing"
    | "ready"
    | "failed";
  status_detail: string | null;
  summary: string | null;
  summary_model: string | null;
  created_at: string;
  indexed_at: string | null;
  pdf_url: string;
  thumbnail_url: string;
}

/** Why a document matched a search, and where to mark the hit. */
export interface SearchMatch {
  kind: "filename" | "folder" | "summary" | "content";
  page_no: number | null;
  snippet: string;
  highlights: [number, number][];
}

export interface SearchDocument extends KnowledgeDocument {
  matches: SearchMatch[];
}

export interface FolderTreeResponse {
  folders: KnowledgeFolder[];
  total_files: number;
}

export interface DocumentListResponse {
  documents: KnowledgeDocument[];
  total: number;
}

export interface SearchResponse {
  query: string;
  documents: SearchDocument[];
}

function queryString(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text.length > 0 ? `?${text}` : "";
}

export const knowledgeApi = {
  folders(signal?: AbortSignal): Promise<FolderTreeResponse> {
    return apiFetch<FolderTreeResponse>("/api/knowledge/folders", { signal });
  },

  documents(
    params: { folder_id?: string | null; limit?: number; offset?: number },
    signal?: AbortSignal,
  ): Promise<DocumentListResponse> {
    return apiFetch<DocumentListResponse>(
      `/api/knowledge/documents${queryString({
        folder_id: params.folder_id ?? undefined,
        limit: params.limit,
        offset: params.offset,
      })}`,
      { signal },
    );
  },

  document(docId: string, signal?: AbortSignal): Promise<KnowledgeDocument> {
    return apiFetch<KnowledgeDocument>(`/api/knowledge/documents/${docId}`, {
      signal,
    });
  },

  createFolder(
    body: { name: string; parent_id: string | null },
    signal?: AbortSignal,
  ): Promise<KnowledgeFolder> {
    return apiFetch<KnowledgeFolder>("/api/knowledge/folders", {
      method: "POST",
      body,
      signal,
    });
  },

  updateFolder(
    folderId: string,
    body: { name?: string; parent_id?: string | null },
    signal?: AbortSignal,
  ): Promise<KnowledgeFolder> {
    return apiFetch<KnowledgeFolder>(`/api/knowledge/folders/${folderId}`, {
      method: "PATCH",
      body,
      signal,
    });
  },

  deleteFolder(folderId: string, signal?: AbortSignal): Promise<{ deleted_documents: number }> {
    return apiFetch<{ deleted_documents: number }>(
      `/api/knowledge/folders/${folderId}`,
      { method: "DELETE", signal },
    );
  },

  moveDocument(
    docId: string,
    folderId: string | null,
    signal?: AbortSignal,
  ): Promise<KnowledgeDocument> {
    return apiFetch<KnowledgeDocument>(`/api/knowledge/documents/${docId}`, {
      method: "PATCH",
      body: { folder_id: folderId },
      signal,
    });
  },

  deleteDocument(docId: string, signal?: AbortSignal): Promise<{ id: string; deleted: boolean }> {
    return apiFetch<{ id: string; deleted: boolean }>(
      `/api/knowledge/documents/${docId}`,
      { method: "DELETE", signal },
    );
  },

  search(q: string, signal?: AbortSignal): Promise<SearchResponse> {
    return apiFetch<SearchResponse>(
      `/api/knowledge/search${queryString({ q, limit: 30 })}`,
      { signal },
    );
  },
};
