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
  generated: boolean;
  total: number;
  mastered: number;
}

export interface RevisionTheme {
  id: string;
  title: string;
  summary: string;
  position: number;
  total: number;
  mastered: number;
  documents: RevisionDocument[];
}

export interface RevisionTreeResponse {
  total: number;
  mastered: number;
  themes: RevisionTheme[];
}

export interface RevisionPoint {
  id: string;
  title: string;
  body_markdown: string;
  position: number;
  page_no: number | null;
  mastered: boolean;
}

export interface RevisionDocumentDetail {
  doc_id: string;
  title: string | null;
  filename: string | null;
  category: RevisionCategory;
  theme_id: string;
  theme_title: string | null;
  intro_markdown: string;
  model: string | null;
  generated_at: string | null;
  total: number;
  mastered: number;
  points: RevisionPoint[];
}

export function getRevisionTree(
  signal?: AbortSignal,
): Promise<RevisionTreeResponse> {
  return apiFetch<RevisionTreeResponse>("/api/revision", { signal });
}

export function getRevisionDocument(
  docId: string,
): Promise<RevisionDocumentDetail> {
  return apiFetch<RevisionDocumentDetail>(
    `/api/revision/docs/${encodeURIComponent(docId)}`,
  );
}

export function setRevisionPoint(
  pointId: string,
  mastered: boolean,
): Promise<{ doc_id: string; total: number; mastered: number }> {
  return apiFetch<{ doc_id: string; total: number; mastered: number }>(
    `/api/revision/points/${encodeURIComponent(pointId)}`,
    { method: "PATCH", body: { mastered } },
  );
}

export function revisionMarkdownUrl(docId: string): string {
  return `/api/revision/docs/${encodeURIComponent(docId)}/markdown`;
}
