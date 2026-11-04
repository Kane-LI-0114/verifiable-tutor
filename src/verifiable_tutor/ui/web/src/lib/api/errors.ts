import type { Messages } from "@/lib/i18n/en";

import { ApiError, NETWORK_ERROR_STATUS } from "./client";

/** Keys of `auth` copy whose value is a plain string. */
type AuthCopyKey = {
  [K in keyof Messages["auth"]]: Messages["auth"][K] extends string ? K : never;
}[keyof Messages["auth"]];

/**
 * Stable backend `detail` strings mapped to their localized copy.
 *
 * The backend keeps these English strings (see `tests/api`); unknown details
 * and server failures fall back to the generic copy rather than surfacing a
 * raw English sentence inside a translated page.
 */
const DETAIL_COPY: Record<string, AuthCopyKey> = {
  "incorrect email or password": "invalidCredentials",
  "account is not verified": "accountNotVerified",
  "account is disabled": "accountDisabled",
  "an account with this email already exists": "emailInUse",
  "invalid or expired verification code": "invalidCode",
  "invalid or expired reset token": "invalidResetToken",
  "email domain is not allowed": "invalidEmail",
  "email address is not valid": "invalidEmail",
};

/** The backend appends the concrete minimum length to this prefix. */
const SHORT_PASSWORD_PREFIX = "password must be at least";

/** Map a backend `detail` string to the localized copy the reader should see. */
export function apiErrorMessage(error: unknown, t: Messages): string {
  if (!(error instanceof ApiError)) {
    return t.common.networkError;
  }
  if (error.status === NETWORK_ERROR_STATUS) {
    return t.common.networkError;
  }

  const detail = error.detail;
  const copyKey = DETAIL_COPY[detail];
  if (copyKey !== undefined) {
    return t.auth[copyKey];
  }
  if (detail.startsWith(SHORT_PASSWORD_PREFIX)) {
    return t.auth.shortPassword;
  }
  return t.common.serverError;
}
