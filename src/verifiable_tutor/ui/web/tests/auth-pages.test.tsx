import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderRoute } from "./render-route";

describe("authentication pages", () => {
  it("renders the sign-in form with the course domain hint and account links", () => {
    renderRoute("/login");

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(
      screen.getByText(/Registration is limited to connect\.ust\.hk/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create one" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Forgot your password?" }),
    ).toBeInTheDocument();
  });

  it("rejects a short password before any network call", async () => {
    const user = userEvent.setup();
    renderRoute("/login");

    await user.type(screen.getByLabelText("Email"), "student@ust.hk");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByText("Use at least 8 characters.")).toBeInTheDocument();
  });

  it("renders the registration form and its domain rule", () => {
    renderRoute("/register");

    expect(
      screen.getByRole("heading", { name: "Create a student account" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Registration is limited to connect\.ust\.hk/),
    ).toBeInTheDocument();
  });

  it("requires all six digits on the verification page", async () => {
    const user = userEvent.setup();
    renderRoute("/verify?email=student@ust.hk");

    expect(
      screen.getByRole("heading", { name: "Confirm your email" }),
    ).toBeInTheDocument();
    expect(screen.getByText("student@ust.hk")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(screen.getByText("Enter all six digits.")).toBeInTheDocument();
  });

  it("renders the reset request and the reset confirmation forms", () => {
    renderRoute("/reset");
    expect(
      screen.getByRole("heading", { name: "Reset your password" }),
    ).toBeInTheDocument();

    renderRoute("/reset/confirm?token=one-time-token");
    expect(
      screen.getByRole("heading", { name: "Set a new password" }),
    ).toBeInTheDocument();
  });
});
