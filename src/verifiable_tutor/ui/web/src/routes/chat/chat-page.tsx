import { usePreview } from "@/lib/preview/context";

import { LiveChatPage } from "./live-chat-page";
import { PreviewChatPage } from "./preview-chat-page";

/**
 * The chat route is shared by the live app and the offline preview demo. The
 * two implementations differ in their data source, not in the route or layout.
 */
export function ChatPage() {
  const { isPreview } = usePreview();
  return isPreview ? <PreviewChatPage /> : <LiveChatPage />;
}
