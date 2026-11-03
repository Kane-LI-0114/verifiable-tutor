const DEFAULT_APP_PATH = "/chat";

const AUTH_PATHS = new Set([
  "/login",
  "/register",
  "/verify",
  "/reset",
  "/reset/confirm",
]);

const INSTRUCTOR_PATHS = new Set([
  "/instructor/builds",
  "/instructor/deadlines",
]);

function withoutTrailingSlash(pathname: string): string {
  return pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
}

function pathnameOf(destination: string): string {
  const [pathname = ""] = destination.split(/[?#]/);
  return withoutTrailingSlash(pathname);
}

export function isAuthPath(pathname: string): boolean {
  return AUTH_PATHS.has(withoutTrailingSlash(pathname));
}

function isInstructorPath(pathname: string): boolean {
  return INSTRUCTOR_PATHS.has(withoutTrailingSlash(pathname));
}

export function safeNextPath(
  raw: string | null | undefined,
  fallback = DEFAULT_APP_PATH,
): string {
  if (typeof raw !== "string") {
    return fallback;
  }

  const value = raw.trim();
  if (
    value === "" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    /[\u0000-\u001f\u007f]/.test(value)
  ) {
    return fallback;
  }

  return value;
}

export function destinationAfterRoleSwitch(
  raw: string | null | undefined,
  role: "student" | "instructor",
): string {
  const destination = safeNextPath(raw);
  const pathname = pathnameOf(destination);

  if (isAuthPath(pathname)) {
    return DEFAULT_APP_PATH;
  }
  if (role === "student" && isInstructorPath(pathname)) {
    return DEFAULT_APP_PATH;
  }

  return destination;
}
