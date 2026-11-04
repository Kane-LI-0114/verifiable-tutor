import type { SessionValue } from "@/lib/auth/session";
import { PREVIEW_INSTRUCTOR, PREVIEW_STUDENT } from "@/lib/preview/fixtures";

export type PreviewRole = "student" | "instructor" | "signed-out";

export function previewSession(role: PreviewRole): SessionValue {
  if (role === "signed-out") {
    return {
      status: "anonymous",
      user: null,
      signOut: async () => {},
      refresh: async () => {},
      expire: () => {},
    };
  }

  return {
    status: "authenticated",
    user: role === "instructor" ? PREVIEW_INSTRUCTOR : PREVIEW_STUDENT,
    signOut: async () => {},
    refresh: async () => {},
    expire: () => {},
  };
}
