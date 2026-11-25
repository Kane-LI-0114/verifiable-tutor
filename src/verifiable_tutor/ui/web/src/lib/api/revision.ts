import { apiFetch } from "./client";

export type RevisionCategory =
  | "assignment"
  | "lecture"
  | "tutorial"
  | "other";

export interface RevisionDocument {
  doc_id: string;
  title: string | null;
  filename: string | null;
  category: RevisionCategory;
}

export interface RevisionTheme {
  id: string;
  title: string;
  summary: string;
  position: number;
  documents: RevisionDocument[];
}

export interface RevisionTreeResponse {
  themes: RevisionTheme[];
}

export function getRevisionTree(
  signal?: AbortSignal,
): Promise<RevisionTreeResponse> {
  return apiFetch<RevisionTreeResponse>("/api/revision", { signal });
}
