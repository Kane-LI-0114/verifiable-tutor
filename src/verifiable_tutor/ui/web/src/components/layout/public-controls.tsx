import { LanguageToggle } from "@/components/layout/language-toggle";
import { PreviewControls } from "@/components/layout/preview-controls";

/**
 * Keeps the language switch and the preview controls reachable on pages that
 * render without the application shell, so a reviewer is never stranded
 * without a way back into the app.
 */
export function PublicControls() {
  return (
    <div className="fixed right-0 top-0 z-20 flex items-center gap-1 p-3">
      <PreviewControls />
      <LanguageToggle />
    </div>
  );
}
