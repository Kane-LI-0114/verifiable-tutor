import { useEffect } from "react";

/** Keep the browser tab title in step with the page that is rendered. */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title;
  }, [title]);
}
