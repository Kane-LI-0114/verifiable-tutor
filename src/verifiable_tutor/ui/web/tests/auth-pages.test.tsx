import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderRoute } from "./render-route";

describe("authentication pages", () => {
  it("renders the sign-in form and account links", () => {
    renderRoute("/login");

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(
      screen.queryByText(/Register with a connect\.ust\.hk/),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create one" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Forgot your password?" }),
    ).toBeInTheDocument();
  });

  it("keeps the preview and language controls reachable while signed out", () => {
    renderRoute("/login");

    expect(
      screen.getByRole("button", { name: "Preview controls" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "中文" })).toBeInTheDocument();
  });

  it("explains a short password at sign-in as invalid credentials, not as a password rule", async () => {
    const user = userEvent.setup();
    renderRoute("/login");

    await user.type(screen.getByLabelText("Email"), "student@ust.hk");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByText("Incorrect email or password.")).toBeInTheDocument();
    expect(
      screen.queryByText("Use at least 8 characters."),
    ).not.toBeInTheDocument();
  });

  it("uses the same invalid credentials copy on the Chinese sign-in page", async () => {
    const user = userEvent.setup();
    renderRoute("/login", { lang: "zh" });

    await user.type(screen.getByLabelText("邮箱"), "student@ust.hk");
    await user.type(screen.getByLabelText("密码"), "short");
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(screen.getByText("邮箱或密码不正确。")).toBeInTheDocument();
    expect(screen.queryByText("密码至少 8 位。")).not.toBeInTheDocument();
  });

  it("renders the registration form and its domain rule", () => {
    renderRoute("/register");

    expect(
      screen.getByRole("heading", { name: "Create a student account" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Register with a connect\.ust\.hk or ust\.hk address/),
    ).toBeInTheDocument();
  });

  it("rejects a registration address outside the course domains", async () => {
    const user = userEvent.setup();
    renderRoute("/register");

    await user.type(screen.getByLabelText("Email"), "someone@gmail.com");
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(
      screen.getByText("Enter a valid course email address."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Development mode: the code is in the server log."),
    ).not.toBeInTheDocument();
  });

  it("accepts a registration address in the course domains", async () => {
    const user = userEvent.setup();
    renderRoute("/register");

    await user.type(screen.getByLabelText("Email"), "Student@Connect.UST.HK");
    await user.type(screen.getByLabelText("Password"), "long-enough");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(
      screen.getByText("Development mode: the code is in the server log."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Enter a valid course email address."),
    ).not.toBeInTheDocument();
  });

  it("requires all six digits on the verification page", async () => {
    const user = userEvent.setup();
    renderRoute("/verify?email=student@ust.hk");

    expect(
      screen.getByRole("heading", { name: "Confirm your email" }),
    ).toBeInTheDocument();
    expect(screen.getByText("student@ust.hk")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(screen.getByText("Enter all 6 digits.")).toBeInTheDocument();
  });

  it("explains why the verification resend control is unavailable", () => {
    renderRoute("/verify?email=student@ust.hk");

    const resend = screen.getByRole("button", { name: "Send the code again" });

    expect(resend).toBeDisabled();
    expect(resend).toHaveAttribute("title", "Not available in this build.");
  });

  it("renders the reset request form", () => {
    renderRoute("/reset");

    expect(
      screen.getByRole("heading", { name: "Reset your password" }),
    ).toBeInTheDocument();
  });

  it("asks for a new password when the reset link carries a token", () => {
    renderRoute("/reset/confirm?token=one-time-token");

    expect(
      screen.getByRole("heading", { name: "Set a new password" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Choose a new password for your course account."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("New password")).toBeInTheDocument();
  });

  it("explains that a reset link without a token is missing or expired", () => {
    renderRoute("/reset/confirm");

    expect(
      screen.getByRole("heading", { name: "Set a new password" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "This reset link is missing or has expired. Request a new one.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Send the link" })).toHaveAttribute(
      "href",
      "/reset",
    );
    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
  });
});
