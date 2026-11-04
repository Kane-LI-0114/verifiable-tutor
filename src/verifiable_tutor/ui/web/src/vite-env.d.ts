/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" builds the offline preview demo instead of the live app. */
  readonly VITE_PREVIEW?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
