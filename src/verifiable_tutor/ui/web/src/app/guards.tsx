import { Navigate, Outlet, useLocation } from "react-router";

import { PublicControls } from "@/components/layout/public-controls";
import { PageError, PageLoading } from "@/components/layout/page-states";
import { safeNextPath } from "@/lib/auth/redirect";
import { useSession } from "@/lib/auth/session";
import { useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";
import { ForbiddenPage } from "@/routes/forbidden-page";

function UnavailablePage() {
  const t = useT();
  const { refresh } = useSession();

  return (
    <div className="relative flex min-h-svh items-center justify-center p-6">
      <PublicControls />
      <div className="w-full max-w-md">
        <PageError
          title={t.common.unavailableTitle}
          description={t.common.unavailableBody}
          onRetry={() => {
            void refresh();
          }}
        />
      </div>
    </div>
  );
}

export function RequireAuth() {
  const { status, user } = useSession();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="p-6">
        <PageLoading />
      </div>
    );
  }

  if (status === "unavailable") {
    return <UnavailablePage />;
  }

  if (user === null) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }

  return <Outlet />;
}

export function RequireInstructor() {
  const { user } = useSession();

  if (user?.role !== "instructor") {
    return <ForbiddenPage />;
  }

  return <Outlet />;
}

/**
 * Authentication pages are for signed-out visitors in live mode.
 *
 * In the preview demo the forms stay reachable so a reviewer can inspect them
 * from any role, which is the documented demo behavior.
 */
export function PublicOnly() {
  const { isPreview } = usePreview();
  const { status, user } = useSession();
  const location = useLocation();

  if (isPreview) {
    return <Outlet />;
  }
  if (status === "loading") {
    return (
      <div className="p-6">
        <PageLoading />
      </div>
    );
  }
  if (status === "unavailable") {
    return <UnavailablePage />;
  }
  if (user !== null) {
    const requested = new URLSearchParams(location.search).get("next");
    return <Navigate to={safeNextPath(requested)} replace />;
  }
  return <Outlet />;
}
