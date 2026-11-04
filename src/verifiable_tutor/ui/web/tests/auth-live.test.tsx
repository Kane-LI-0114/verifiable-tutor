import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  createFetchStub,
  errorResponse,
  jsonResponse,
  type StubRoute,
} from "./api-stub";
import { renderLiveRoute } from "./render-live-route";
import { renderRoute } from "./render-route";

const STUDENT_USER = {
  id: "u1",
  email: "student@ust.hk",
  role: "student" as const,
};

const ME = {
  ...STUDENT_USER,
  created_at: "2026-11-02T12:00:00+00:00",
};

const EMPTY_SESSIONS = { sessions: [] };

// The OTP input measures its password-manager badge with elementFromPoint,
// which jsdom does not implement. Stub it for this file so typing a code does
// not raise an unhandled timer error.
if (typeof document.elementFromPoint !== "function") {
  document.elementFromPoint = () => null;
}

/** Flipped by a successful login handler so the refresh after sign-in succeeds. */
let signedIn = false;
/** The registration domains the stubbed backend reports, in configured order. */
let allowedDomains: string[] = [];
/** Non-null makes `GET /api/auth/domains` fail, for the offline-config path. */
let domainsStatus: number | null = null;
let stub: ReturnType<typeof createFetchStub> | null = null;

beforeEach(() => {
  signedIn = false;
  allowedDomains = ["connect.ust.hk", "ust.hk"];
  domainsStatus = null;
});

afterEach(() => {
  stub?.restore();
  stub = null;
});

function liveRoutes(overrides: StubRoute[] = []): StubRoute[] {
  return [
    {
      method: "GET",
      path: "/api/auth/me",
      handler: () =>
        signedIn ? jsonResponse(ME) : errorResponse("not signed in", 401),
    },
    {
      method: "GET",
      path: "/api/sessions",
      handler: () => jsonResponse(EMPTY_SESSIONS),
    },
    {
      method: "GET",
      path: "/api/auth/domains",
      handler: () =>
        domainsStatus === null
          ? jsonResponse({ domains: allowedDomains })
          : errorResponse("domains unavailable", domainsStatus),
    },
    ...overrides,
  ];
}

function postRoute(path: string, handler: StubRoute["handler"]): StubRoute {
  return { method: "POST", path, handler };
}

function callsTo(path: string) {
  return stub?.calls.filter((call) => call.path === path) ?? [];
}

async function fillSignIn(email: string, password: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("live sign-in page", () => {
  it("signs in through the API and follows the session to the chat", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/login", () => {
          signedIn = true;
          return jsonResponse({ user: STUDENT_USER });
        }),
      ]),
    );
    const router = renderLiveRoute("/login");

    await fillSignIn("student@ust.hk", "long-enough");

    await waitFor(() => expect(router.state.location.pathname).toBe("/chat"));
    const logins = callsTo("/api/auth/login");
    expect(logins).toHaveLength(1);
    expect(logins[0].body).toEqual({
      email: "student@ust.hk",
      password: "long-enough",
    });
  });

  it("shows the invalid credentials copy when the password is wrong", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/login", () =>
          errorResponse("incorrect email or password", 401),
        ),
      ]),
    );
    const router = renderLiveRoute("/login");

    await fillSignIn("student@ust.hk", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Incorrect email or password.",
    );
    expect(router.state.location.pathname).toBe("/login");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("shows the not-verified copy for a pending account", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/login", () =>
          errorResponse("account is not verified", 403),
        ),
      ]),
    );
    renderLiveRoute("/login");

    await fillSignIn("student@ust.hk", "long-enough");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Verify your email address before signing in.",
    );
  });

  it("disables the submit control while the sign-in request is in flight", async () => {
    let resolveLogin!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => {
      resolveLogin = resolve;
    });
    stub = createFetchStub(
      liveRoutes([postRoute("/api/auth/login", () => pending)]),
    );
    renderLiveRoute("/login");

    await fillSignIn("student@ust.hk", "long-enough");

    expect(
      await screen.findByRole("button", { name: "Signing in" }),
    ).toBeDisabled();

    await act(async () => {
      resolveLogin(errorResponse("incorrect email or password", 401));
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Incorrect email or password.",
    );
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
    expect(callsTo("/api/auth/login")).toHaveLength(1);
  });

  it("prefills the email and explains the confirmed address from the verification link", async () => {
    stub = createFetchStub(liveRoutes());
    renderLiveRoute("/login?email=student%40ust.hk&verified=1");

    expect(await screen.findByLabelText("Email")).toHaveValue(
      "student@ust.hk",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Your email is confirmed. Sign in to continue.",
    );
  });

  it("explains the updated password from the reset link", async () => {
    stub = createFetchStub(liveRoutes());
    renderLiveRoute("/login?reset=1");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your password was updated. Sign in with the new password.",
    );
  });
});

describe("live registration page", () => {
  it("registers the account and opens verification for the returned email", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/register", () =>
          jsonResponse(
            {
              email: "student@ust.hk",
              role: "student",
              verification: "pending",
              email_delivery: "log",
            },
            { status: 201 },
          ),
        ),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/register");

    await user.type(await screen.findByLabelText("Email"), "student@ust.hk");
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/verify"),
    );
    expect(router.state.location.search).toBe("?email=student%40ust.hk");
    expect(await screen.findByText("student@ust.hk")).toBeInTheDocument();

    const registrations = callsTo("/api/auth/register");
    expect(registrations).toHaveLength(1);
    expect(registrations[0].body).toEqual({
      email: "student@ust.hk",
      password: "long-enough",
    });
  });

  it("shows the email-in-use copy for an existing account", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/register", () =>
          errorResponse("an account with this email already exists", 409),
        ),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/register");

    await user.type(await screen.findByLabelText("Email"), "student@ust.hk");
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "An account with this email already exists.",
    );
    expect(router.state.location.pathname).toBe("/register");
  });

  it("rejects a domain the backend does not report as allowed", async () => {
    allowedDomains = ["ust.hk"];
    stub = createFetchStub(liveRoutes());
    const user = userEvent.setup();
    renderLiveRoute("/register");

    await user.type(
      await screen.findByLabelText("Email"),
      "someone@connect.ust.hk",
    );
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid course email address.",
    );
    expect(callsTo("/api/auth/register")).toHaveLength(0);
    expect(callsTo("/api/auth/domains")).toHaveLength(1);
  });

  it("lets the backend validate the domain when the list cannot be loaded", async () => {
    domainsStatus = 500;
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/register", () =>
          jsonResponse(
            {
              email: "someone@department.example.edu",
              role: "student",
              verification: "pending",
              email_delivery: "log",
            },
            { status: 201 },
          ),
        ),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/register");

    await user.type(
      await screen.findByLabelText("Email"),
      "someone@department.example.edu",
    );
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/verify"),
    );
    expect(callsTo("/api/auth/register")).toHaveLength(1);
    expect(
      screen.queryByText("Enter a valid course email address."),
    ).not.toBeInTheDocument();
  });

  it("rejects an address outside the course domains before any network call", async () => {
    stub = createFetchStub(liveRoutes());
    const user = userEvent.setup();
    renderLiveRoute("/register");

    await user.type(await screen.findByLabelText("Email"), "someone@gmail.com");
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid course email address.",
    );
    expect(callsTo("/api/auth/register")).toHaveLength(0);
  });
});

describe("live verification page", () => {
  it("confirms the account and returns to sign-in with the verified notice", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/verify", (call) => {
          expect(call.body).toEqual({
            email: "student@ust.hk",
            code: "123456",
          });
          return jsonResponse({ email: "student@ust.hk", status: "active" });
        }),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/verify?email=student%40ust.hk");

    await user.type(
      await screen.findByLabelText("Verification code"),
      "123456",
    );
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/login"),
    );
    expect(router.state.location.search).toBe(
      "?email=student%40ust.hk&verified=1",
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your email is confirmed. Sign in to continue.",
    );
  });

  it("shows the invalid code copy for an expired code", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/verify", () =>
          errorResponse("invalid or expired verification code", 400),
        ),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/verify?email=student%40ust.hk");

    await user.type(
      await screen.findByLabelText("Verification code"),
      "000000",
    );
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That verification code is invalid or has expired.",
    );
    expect(router.state.location.pathname).toBe("/verify");
  });
});

describe("live reset request page", () => {
  it("confirms the reset link and repeats the backend log hint for log delivery", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/reset/request", () =>
          jsonResponse({ email: "student@ust.hk", email_delivery: "log" }),
        ),
      ]),
    );
    const user = userEvent.setup();
    renderLiveRoute("/reset");

    await user.type(await screen.findByLabelText("Email"), "student@ust.hk");
    await user.click(screen.getByRole("button", { name: "Send the link" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Check your inbox for the next step.");
    expect(alert).toHaveTextContent(
      "Development mode: the code is in the backend log.",
    );
    expect(callsTo("/api/auth/reset/request")[0]?.body).toEqual({
      email: "student@ust.hk",
    });
  });

  it("leaves out the log hint when the backend delivers the mail", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/reset/request", () =>
          jsonResponse({ email: "student@ust.hk", email_delivery: "smtp" }),
        ),
      ]),
    );
    const user = userEvent.setup();
    renderLiveRoute("/reset");

    await user.type(await screen.findByLabelText("Email"), "student@ust.hk");
    await user.click(screen.getByRole("button", { name: "Send the link" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Check your inbox for the next step.");
    expect(alert).not.toHaveTextContent(
      "Development mode: the code is in the backend log.",
    );
  });
});

describe("live reset confirmation page", () => {
  it("updates the password and returns to sign-in with the updated notice", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/reset", (call) => {
          expect(call.body).toEqual({
            token: "one-time-token",
            new_password: "new-password-1",
          });
          return jsonResponse({
            email: "student@ust.hk",
            sessions_invalidated: 1,
          });
        }),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/reset/confirm?token=one-time-token");

    await user.type(
      await screen.findByLabelText("New password"),
      "new-password-1",
    );
    await user.type(
      screen.getByLabelText("Confirm the new password"),
      "new-password-1",
    );
    await user.click(
      screen.getByRole("button", { name: "Update the password" }),
    );

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/login"),
    );
    expect(router.state.location.search).toBe("?reset=1");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your password was updated. Sign in with the new password.",
    );
  });

  it("shows the invalid reset token copy for an expired token", async () => {
    stub = createFetchStub(
      liveRoutes([
        postRoute("/api/auth/reset", () =>
          errorResponse("invalid or expired reset token", 400),
        ),
      ]),
    );
    const user = userEvent.setup();
    const router = renderLiveRoute("/reset/confirm?token=stale-token");

    await user.type(
      await screen.findByLabelText("New password"),
      "new-password-1",
    );
    await user.type(
      screen.getByLabelText("Confirm the new password"),
      "new-password-1",
    );
    await user.click(
      screen.getByRole("button", { name: "Update the password" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This reset link is missing or has expired. Request a new one.",
    );
    expect(router.state.location.pathname).toBe("/reset/confirm");
  });

  it("rejects a mismatched confirmation before any network call", async () => {
    stub = createFetchStub(liveRoutes());
    const user = userEvent.setup();
    renderLiveRoute("/reset/confirm?token=one-time-token");

    await user.type(
      await screen.findByLabelText("New password"),
      "new-password-1",
    );
    await user.type(
      screen.getByLabelText("Confirm the new password"),
      "new-password-2",
    );
    await user.click(
      screen.getByRole("button", { name: "Update the password" }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "The two passwords do not match.",
    );
    expect(callsTo("/api/auth/reset")).toHaveLength(0);
  });
});

describe("offline preview demo", () => {
  it("keeps the preview notice instead of calling the API", async () => {
    const user = userEvent.setup();
    renderRoute("/login");

    await user.type(screen.getByLabelText("Email"), "student@ust.hk");
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(
      screen.getByText("Preview build: this page uses sample data."),
    ).toBeInTheDocument();
  });
});
