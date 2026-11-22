import { useSyncExternalStore } from "react";

/**
 * The document page the reader last had open, remembered for this visit only.
 *
 * The knowledge nav points here while the reader is elsewhere, so changing to
 * the conversation view and back returns to the file instead of the grid. The
 * value lives in a module, not in storage: a page reload starts at the grid.
 */
let lastDocumentPath: string | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) {
    listener();
  }
}

export function rememberDocumentPath(path: string): void {
  if (path === lastDocumentPath) {
    return;
  }
  lastDocumentPath = path;
  emit();
}

export function clearDocumentPath(): void {
  if (lastDocumentPath === null) {
    return;
  }
  lastDocumentPath = null;
  emit();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): string | null {
  return lastDocumentPath;
}

function getServerSnapshot(): string | null {
  return null;
}

export function useDocumentReturnPath(): string | null {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
