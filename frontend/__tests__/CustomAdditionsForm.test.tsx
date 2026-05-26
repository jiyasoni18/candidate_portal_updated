import { render, screen, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import CustomAdditionsForm from "../components/CustomAdditionsForm";

vi.mock("../lib/api", () => ({
  refineCustomAdditions: vi.fn(),
}));

describe("CustomAdditionsForm", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it("renders form with all three sections", () => {
    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions=""
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText("Custom Additions")).toBeInTheDocument();
    expect(screen.getByText("Certificates")).toBeInTheDocument();
    expect(screen.getByText("Education")).toBeInTheDocument();
    expect(screen.getByText("Additional")).toBeInTheDocument();
    expect(screen.getByText("Save Custom Additions")).toBeInTheDocument();
  });

  it("pre-fills sections with initialAdditions data", () => {
    const initialAdditions = `[CERTIFICATES]
AWS Certified Solutions Architect

[EDUCATION]
Master of Science in Computer Science, Stanford University

[ADDITIONAL]
Open source contributor to several projects`;

    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions={initialAdditions}
        onSubmit={mockOnSubmit}
      />
    );

    const certInput = screen.getByPlaceholderText(/e\.g\., AWS Certified Solutions Architect, PMP/i);
    const eduInput = screen.getByPlaceholderText(/e\.g\., Master of Science in Computer Science, Stanford University/i);
    const addInput = screen.getByPlaceholderText(/e\.g\., Open source contributions, speaking engagements, publications/i);

    expect(certInput).toHaveValue("AWS Certified Solutions Architect");
    expect(eduInput).toHaveValue("Master of Science in Computer Science, Stanford University");
    expect(addInput).toHaveValue("Open source contributor to several projects");
  });

  it("allows editing certificate section", async () => {
    const user = userEvent.setup();
    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions=""
        onSubmit={mockOnSubmit}
      />
    );

    const certInput = screen.getByPlaceholderText(/e\.g\., AWS Certified Solutions Architect, PMP/i);
    await act(async () => {
      await user.type(certInput, "PMP Certification");
    });

    expect(certInput).toHaveValue("PMP Certification");
  });

  it("allows editing education section", async () => {
    const user = userEvent.setup();
    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions=""
        onSubmit={mockOnSubmit}
      />
    );

    const eduInput = screen.getByPlaceholderText(/e\.g\., Master of Science in Computer Science, Stanford University/i);
    await act(async () => {
      await user.type(eduInput, "PhD in Engineering, MIT");
    });

    expect(eduInput).toHaveValue("PhD in Engineering, MIT");
  });

  it("allows editing additional section", async () => {
    const user = userEvent.setup();
    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions=""
        onSubmit={mockOnSubmit}
      />
    );

    const addInput = screen.getByPlaceholderText(/e\.g\., Open source contributions, speaking engagements, publications/i);
    await act(async () => {
      await user.type(addInput, "Tech speaker at local meetups");
    });

    expect(addInput).toHaveValue("Tech speaker at local meetups");
  });

  it("calls onSubmit with properly formatted additions text", async () => {
    const user = userEvent.setup();
    mockOnSubmit.mockResolvedValue({ success: true });

    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions=""
        onSubmit={mockOnSubmit}
      />
    );

    const certInput = screen.getByPlaceholderText(/e\.g\., AWS Certified Solutions Architect, PMP/i);
    const eduInput = screen.getByPlaceholderText(/e\.g\., Master of Science in Computer Science, Stanford University/i);
    const addInput = screen.getByPlaceholderText(/e\.g\., Open source contributions, speaking engagements, publications/i);

    await act(async () => {
      await user.type(certInput, "PMP");
      await user.type(eduInput, "MBA");
      await user.type(addInput, "Blog writer");
    });

    const submitBtn = screen.getByText("Save Custom Additions");
    await act(async () => {
      await user.click(submitBtn);
    });

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    });

    const submittedText = mockOnSubmit.mock.calls[0][0];
    expect(submittedText).toContain("[CERTIFICATES]");
    expect(submittedText).toContain("PMP");
    expect(submittedText).toContain("[EDUCATION]");
    expect(submittedText).toContain("MBA");
    expect(submittedText).toContain("[ADDITIONAL]");
    expect(submittedText).toContain("Blog writer");
  });

  it("shows error message when submission fails", async () => {
    const user = userEvent.setup();
    mockOnSubmit.mockRejectedValue(new Error("Network error"));

    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions=""
        onSubmit={mockOnSubmit}
      />
    );

    const submitBtn = screen.getByText("Save Custom Additions");
    await act(async () => {
      await user.click(submitBtn);
    });

    expect(screen.getByText("Failed to submit custom additions. Please try again.")).toBeInTheDocument();
  });

  it("disables submit button while submitting", async () => {
    const user = userEvent.setup();
    mockOnSubmit.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));

    render(
      <CustomAdditionsForm
        sessionId="test-session"
        initialAdditions=""
        onSubmit={mockOnSubmit}
      />
    );

    const submitBtn = screen.getByText("Save Custom Additions");
    await act(async () => {
      await user.click(submitBtn);
    });

    expect(submitBtn).toBeDisabled();
    expect(submitBtn).toHaveTextContent("Saving...");
  });
});
