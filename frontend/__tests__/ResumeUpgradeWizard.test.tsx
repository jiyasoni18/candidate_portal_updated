import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
import ResumeUpgradeWizardPage from "../app/practice/[session_id]/upgrade/page";
import * as api from "../lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("../lib/api", () => {
  class ApiError extends Error {
    status: number;
    detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  }
  return {
    fetchSession: vi.fn(),
    refineWithGaps: vi.fn(),
    generatePDF: vi.fn(),
    ApiError,
  };
});

const fetchSessionMock = vi.mocked(api.fetchSession);
const refineWithGapsMock = vi.mocked(api.refineWithGaps);
const generatePDFMock = vi.mocked(api.generatePDF);

const sessionWithData = {
  session_id: "sess-abc",
  status: "ready_to_start",
  created_at: "2024-01-01T00:00:00Z",
  job: { id: "job-1", title: "Software Engineer" },
  resume_report: null,
  resume_score: null,
  interview_assessment: null,
  enhanced_analysis: {
    ats_score: 75,
    ats_explanation: "",
    improvements: ["Use 'engineered' instead of 'worked on'", "Add quantified metrics"],
    match_score: 80,
    gaps: ["No Kubernetes experience", "Missing CI/CD pipeline knowledge"],
    strengths: ["Strong Python skills"],
    summary: "Good candidate",
    section_scores: {},
    section_reasons: {},
    mandatory_skills_check: [],
    good_to_have_check: [],
    flags: {},
  },
};

const sessionNoGapsNoImprovements = {
  ...sessionWithData,
  enhanced_analysis: {
    ...sessionWithData.enhanced_analysis,
    gaps: [],
    improvements: [],
  },
};

const refineResponse = {
  session_id: "sess-abc",
  status: "ok",
  refined_gaps: {
    "0": "Refined paragraph for Kubernetes gap.",
    "1": "Refined paragraph for CI/CD gap.",
  },
  refined_custom_items: ["Refined custom item one.", "Refined custom item two."],
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ResumeUpgradeWizardPage", () => {
  // ── Gap cards ──────────────────────────────────────────────────────────────

  it("renders gap cards with correct text and textarea", async () => {
    fetchSessionMock.mockResolvedValue(sessionWithData as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("No Kubernetes experience")).toBeInTheDocument();
      expect(screen.getByText("Missing CI/CD pipeline knowledge")).toBeInTheDocument();
    });

    const textareas = screen.getAllByPlaceholderText(
      /Describe your experience or project that addresses this gap/i
    );
    expect(textareas).toHaveLength(2);
  });

  it("shows 'No gaps detected' when gaps array is empty", async () => {
    fetchSessionMock.mockResolvedValue(sessionNoGapsNoImprovements as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("No gaps detected")).toBeInTheDocument();
    });
  });

  // ── Improvements checkboxes ────────────────────────────────────────────────

  it("renders improvement checkboxes checked by default", async () => {
    fetchSessionMock.mockResolvedValue(sessionWithData as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("Use 'engineered' instead of 'worked on'")).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole("checkbox");
    checkboxes.forEach((cb) => expect(cb).toBeChecked());
  });

  it("toggles improvement checkbox on click", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("Use 'engineered' instead of 'worked on'")).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes[0]).toBeChecked();

    await act(async () => {
      await user.click(checkboxes[0]);
    });

    expect(checkboxes[0]).not.toBeChecked();
  });

  it("hides improvements section when improvements array is empty", async () => {
    fetchSessionMock.mockResolvedValue(sessionNoGapsNoImprovements as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.queryByText("Terminology Improvements")).not.toBeInTheDocument();
    });
  });

  // ── Refine button ──────────────────────────────────────────────────────────

  it("shows 'Refine My Inputs' button in step 1", async () => {
    fetchSessionMock.mockResolvedValue(sessionWithData as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("Refine My Inputs")).toBeInTheDocument();
    });
  });

  it("disables refine button while refining", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    refineWithGapsMock.mockImplementation(() => new Promise(() => {}));

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("Refine My Inputs")).toBeInTheDocument();
    });

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    expect(screen.getByText("Refining...")).toBeDisabled();
  });

  it("shows inline error and re-enables button when refine fails", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    const { ApiError } = api as any;
    refineWithGapsMock.mockRejectedValue(new ApiError(500, "Internal server error"));

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("Refine My Inputs")).toBeInTheDocument();
    });

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => {
      expect(screen.getByText("Internal server error")).toBeInTheDocument();
      expect(screen.getByText("Refine My Inputs")).not.toBeDisabled();
    });
  });

  // ── Step 2: Refinement Review ──────────────────────────────────────────────

  it("transitions to review step and renders RefinedItemCards after successful refine", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    refineWithGapsMock.mockResolvedValue(refineResponse as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("Refine My Inputs")).toBeInTheDocument();
    });

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => {
      expect(screen.getByText("Refined paragraph for Kubernetes gap.")).toBeInTheDocument();
      expect(screen.getByText("Refined paragraph for CI/CD gap.")).toBeInTheDocument();
      expect(screen.getByText("Refined custom item one.")).toBeInTheDocument();
      expect(screen.getByText("Refined custom item two.")).toBeInTheDocument();
    });
  });

  it("defaults all refined items to approved state", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    refineWithGapsMock.mockResolvedValue(refineResponse as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => screen.getByText("Refine My Inputs"));

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => {
      // All 4 items should show "Approved" badge
      const approvedBadges = screen.getAllByText("Approved");
      expect(approvedBadges).toHaveLength(4);
    });
  });

  it("marks item as rejected when Reject is clicked", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    refineWithGapsMock.mockResolvedValue(refineResponse as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => screen.getByText("Refine My Inputs"));

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => screen.getByText("Refined paragraph for Kubernetes gap."));

    const rejectButtons = screen.getAllByText("Reject");
    await act(async () => {
      await user.click(rejectButtons[0]);
    });

    await waitFor(() => {
      expect(screen.getByText("Rejected")).toBeInTheDocument();
    });
  });

  it("shows 'Generate Upgraded Resume' button in review step", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    refineWithGapsMock.mockResolvedValue(refineResponse as any);

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => screen.getByText("Refine My Inputs"));

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => {
      expect(screen.getByText("Generate Upgraded Resume")).toBeInTheDocument();
    });
  });

  // ── Generate flow ──────────────────────────────────────────────────────────

  it("calls refineWithGaps with pre_refined=true then generatePDF on generate click", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    refineWithGapsMock.mockResolvedValue(refineResponse as any);
    generatePDFMock.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));

    // Mock URL.createObjectURL and revokeObjectURL
    const createObjectURL = vi.fn(() => "blob:mock-url");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { value: createObjectURL, writable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeObjectURL, writable: true });

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => screen.getByText("Refine My Inputs"));

    // Go to review step
    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => screen.getByText("Generate Upgraded Resume"));

    // Click generate
    await act(async () => {
      await user.click(screen.getByText("Generate Upgraded Resume"));
    });

    await waitFor(() => {
      // Second refineWithGaps call should have pre_refined=true
      expect(refineWithGapsMock).toHaveBeenCalledTimes(2);
      const secondCall = refineWithGapsMock.mock.calls[1];
      expect(secondCall[4]).toBe(true); // preRefined flag
      // generatePDF should be called with session_id and template
      expect(generatePDFMock).toHaveBeenCalledWith("sess-abc", "Classic ATS");
    });
  });

  it("only includes approved items in the persist call", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    refineWithGapsMock.mockResolvedValue(refineResponse as any);
    generatePDFMock.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));

    Object.defineProperty(URL, "createObjectURL", { value: vi.fn(() => "blob:mock"), writable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), writable: true });

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => screen.getByText("Refine My Inputs"));

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => screen.getByText("Refined paragraph for Kubernetes gap."));

    // Reject the first gap item
    const rejectButtons = screen.getAllByText("Reject");
    await act(async () => {
      await user.click(rejectButtons[0]);
    });

    await act(async () => {
      await user.click(screen.getByText("Generate Upgraded Resume"));
    });

    await waitFor(() => {
      const secondCall = refineWithGapsMock.mock.calls[1];
      const gapSelections = secondCall[2] as Record<string, string>;
      // Gap "0" was rejected, should not be in the persist call
      expect(gapSelections["0"]).toBeUndefined();
      // Gap "1" was not rejected, should be included
      expect(gapSelections["1"]).toBe("Refined paragraph for CI/CD gap.");
    });
  });

  it("shows inline error and re-enables button when generate fails", async () => {
    const user = userEvent.setup();
    fetchSessionMock.mockResolvedValue(sessionWithData as any);
    const { ApiError } = api as any;
    // First call (refine step) succeeds, second call (persist step) fails
    refineWithGapsMock
      .mockResolvedValueOnce(refineResponse as any)
      .mockRejectedValueOnce(new ApiError(500, "Persist failed"));

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => screen.getByText("Refine My Inputs"));

    await act(async () => {
      await user.click(screen.getByText("Refine My Inputs"));
    });

    await waitFor(() => screen.getByText("Generate Upgraded Resume"));

    await act(async () => {
      await user.click(screen.getByText("Generate Upgraded Resume"));
    });

    await waitFor(() => {
      expect(screen.getByText("Persist failed")).toBeInTheDocument();
      expect(screen.getByText("Generate Upgraded Resume")).not.toBeDisabled();
    });
  });

  // ── Load error state ───────────────────────────────────────────────────────

  it("shows error state with Back to Report link when session fetch fails", async () => {
    const { ApiError } = api as any;
    fetchSessionMock.mockRejectedValue(new ApiError(404, "Session not found"));

    await act(async () => {
      render(<ResumeUpgradeWizardPage params={Promise.resolve({ session_id: "sess-abc" })} />);
    });

    await waitFor(() => {
      expect(screen.getByText("Session not found")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /back to report/i })).toHaveAttribute(
        "href",
        "/practice/sess-abc"
      );
    });
  });
});
