import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderRoute } from "./render-route";

async function chooseType(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(screen.getByRole("combobox", { name: "Question type" }));
  await user.click(screen.getByRole("option", { name }));
}

describe("practice page", () => {
  it("shows the unavailable notice, the settings, and a single-choice question", () => {
    renderRoute("/practice");

    expect(
      screen.getByRole("heading", { name: "Practice and self-test" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Practice execution is not available"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Which MPI collective leaves the reduced value on every rank?"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("MPI_Allreduce")).toBeInTheDocument();
    expect(screen.getByText("1 point")).toBeInTheDocument();
  });

  it("asks for an answer instead of grading an empty submission", async () => {
    const user = userEvent.setup();
    renderRoute("/practice");

    await user.click(screen.getByRole("button", { name: "Submit the answer" }));

    expect(
      screen.getByText("Add an answer before you submit this question."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Partially correct")).not.toBeInTheDocument();
    expect(screen.queryByText("Test results")).not.toBeInTheDocument();
  });

  it("keeps code test results off a choice question", async () => {
    const user = userEvent.setup();
    renderRoute("/practice");

    await user.click(screen.getByLabelText("MPI_Allreduce"));
    await user.click(screen.getByRole("button", { name: "Submit the answer" }));

    expect(screen.getByText("Partially correct")).toBeInTheDocument();
    expect(screen.queryByText("Test results")).not.toBeInTheDocument();
  });

  it("switches to a short answer question with a text area", async () => {
    const user = userEvent.setup();
    renderRoute("/practice");

    await chooseType(user, "Short answer");

    expect(
      screen.getByText(
        "Explain in one or two sentences why the softmax in attention needs the row maximum.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Your answer")).toBeInTheDocument();
  });

  it("confirms before running a code answer and then shows test results", async () => {
    const user = userEvent.setup();
    renderRoute("/practice");

    await chooseType(user, "Code");
    await user.type(screen.getByLabelText("Your answer"), "MPI_Allreduce(local, global, count, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);");
    await user.click(screen.getByRole("button", { name: "Submit the answer" }));

    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByText("Run this code on TACC?"),
    ).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Run the code" }));

    expect(screen.getByText("5 of 5")).toBeInTheDocument();
    expect(screen.getByText("2 of 2 cases passed")).toBeInTheDocument();
    expect(screen.getByText("Correct")).toBeInTheDocument();
  });

  it("shows the structure-only solution tab", async () => {
    const user = userEvent.setup();
    renderRoute("/practice");

    await user.click(screen.getByRole("tab", { name: "My solution" }));

    expect(
      screen.getByRole("heading", { name: "Explain my solution" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Line-anchored explanations arrive with the teaching package/),
    ).toBeInTheDocument();
  });
});
