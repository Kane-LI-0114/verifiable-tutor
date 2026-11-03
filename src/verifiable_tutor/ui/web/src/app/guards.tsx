import { Navigate, Outlet, useLocation } from "react-router";

import { PageLoading } from "@/components/layout/page-states";
import { ForbiddenPage } from "@/routes/forbidden-page";
import { useSession } from "@/lib/auth/session";

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
