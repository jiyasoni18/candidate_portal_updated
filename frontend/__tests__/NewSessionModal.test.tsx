import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import NewSessionModal from "../components/NewSessionModal";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock the api module
vi.mock("../lib/api", () => ({
  initializeSession: vi.fn(),
}));

describe("NewSessionModal", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when open is false", () => {
    render(<NewSessionModal open={false} onClose={onClose} />);
    expect(screen.queryByText("New Practice Session")).not.toBeInTheDocument();
  });

  it("renders the form when open is true", () => {
    render(<NewSessionModal open={true} onClose={onClose} />);
    expect(screen.getByText("New Practice Session")).toBeInTheDocument();
    expect(screen.getByLabelText("Job Title")).toBeInTheDocument();
    expect(screen.getByLabelText("Job Description")).toBeInTheDocument();
  });

  it("shows file field error and does not call fetch when submitting without a file", async () => {
    render(<NewSessionModal open={true} onClose={onClose} />);

    fireEvent.change(screen.getByLabelText("Job Title"), {
      target: { value: "Software Engineer" },
    });
    fireEvent.change(screen.getByLabelText("Job Description"), {
      target: { value: "Some job description text" },
    });

    fireEvent.click(screen.getByRole("button", { name: /start session/i }));

    await waitFor(() => {
      expect(screen.getByText("A PDF resume is required.")).toBeInTheDocument();
    });

    const { initializeSession } = await import("../lib/api");
    expect(initializeSession).not.toHaveBeenCalled();
  });

  it("shows job title field error when submitting without a title", async () => {
    render(<NewSessionModal open={true} onClose={onClose} />);

    fireEvent.change(screen.getByLabelText("Job Description"), {
      target: { value: "Some job description text" },
    });

    fireEvent.click(screen.getByRole("button", { name: /start session/i }));

    await waitFor(() => {
      expect(screen.getByText("Job title is required.")).toBeInTheDocument();
    });
  });

  it("shows file validation error when a non-PDF file is dropped", async () => {
    render(<NewSessionModal open={true} onClose={onClose} />);

    const dropZone = screen.getByText(/drag & drop/i).closest("div")!;
    const nonPdfFile = new File(["content"], "resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    fireEvent.drop(dropZone, {
      dataTransfer: { files: [nonPdfFile] },
    });

    await waitFor(() => {
      expect(screen.getByText("Only PDF files are accepted.")).toBeInTheDocument();
    });
  });

  it("submit button is disabled and shows spinner while submitting", async () => {
    const { initializeSession } = await import("../lib/api");
    // Return a promise that never resolves to keep submitting state active
    (initializeSession as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<NewSessionModal open={true} onClose={onClose} />);

    fireEvent.change(screen.getByLabelText("Job Title"), {
      target: { value: "Software Engineer" },
    });
    fireEvent.change(screen.getByLabelText("Job Description"), {
      target: { value: "Some job description text" },
    });

    // Attach a PDF file via the hidden input
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const pdfFile = new File(["pdf content"], "resume.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [pdfFile] } });

    const submitButton = screen.getByRole("button", { name: /start session/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /submitting/i })).toBeDisabled();
    });
  });
});
