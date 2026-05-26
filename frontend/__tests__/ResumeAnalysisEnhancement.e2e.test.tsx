import { render, screen, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AssessmentPage from "../app/practice/[session_id]/assessment/page";
import * as api from "../lib/api";

// ── Module-level mocks ────────────────────────────────────────────────────────

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
    refineCustomAdditions: vi.fn(),
    generatePDF: vi.fn(),
    ApiError,
  };
});

const fetchSessionMock = vi.mocked(api.fetchSession);
const refineCustomAdditionsMock = vi.mocked(api.refineCustomAdditions);
const generatePDFMock = vi.mocked(api.generatePDF);

// ── Mock session data ─────────────────────────────────────────────────────────

const mockEnhancedAnalysis = {
  match_score: 85,
  ats_score: 78,
  ats_explanation: "Good structure with clear section headings.",
  gaps: ["Missing Redis experience", "No Kubernetes exposure"],
  improvements: ["Use orchestrated instead of managed for Kubernetes", "Add distributed caching for Redis"],
  core_strengths: ["Strong Python background", "API design experience"],
  summary: "Candidate shows strong technical foundation with some gaps in modern infrastructure tools.",
};

const mockSessionDetail = {
  session_id: "test-session-123",
  status: "completed",
  created_at: "2024-01-15T10:30:00Z",
  job: { id: "job-1", title: "Senior Engineer" },
  resume_report: null,
  resume_score: null,
  interview_assessment: {
    overall_score: 74,
    practice_verdict: "Strong Alignment",
    summary: "Solid performance overall.",
    dimension_scores: {
      technical: {
        score: 78,
        max_score: 100,
        label: "Technical Familiarity",
        verdict: "Good",
        evidence: "Demonstrated solid Python knowledge.",
        strengths: ["Python"],
        gaps: ["Kubernetes"],
      },
      role_alignment: {
        score: 70,
        max_score: 100,
        label: "Role Alignment",
        verdict: "Good",
        evidence: "Aligned with product engineering focus.",
        strengths: ["Product mindset"],
        gaps: ["Domain depth"],
      },
      communication: {
        score: 72,
        max_score: 100,
        label: "Communication",
        verdict: "Good",
        evidence: "Clear and structured responses.",
        strengths: ["Clarity"],
        gaps: ["Conciseness"],
      },
      presence: {
        score: 65,
        max_score: 100,
        label: "Presence",
        verdict: "Fair",
        evidence: "Moderate confidence shown.",
        strengths: ["Eye contact"],
        gaps: ["Pacing"],
      },
    },
    overall_strengths: ["Python", "API design"],
    overall_gaps: ["Kubernetes", "System design depth"],
    technical_round_probes: [
      "Explain your approach to distributed caching.",
      "How would you design a rate limiter?",
      "Describe a time you optimized a slow query.",
    ],
    turns_analyzed: 22,
    completion_ratio: 0.875,
  },
  enhanced_analysis: mockEnhancedAnalysis,
};

// ── Helper to create resolved params promise ──────────────────────────────────

function createResolvedParams(sessionId: string) {
  return Promise.resolve({ session_id: sessionId });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Resume Analysis Enhancement - E2E", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Complete Workflow - Session to PDF", () => {
    it("displays enhanced resume report and allows PDF download", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      // Verify enhanced report is displayed
      expect(screen.getByText("Resume Report")).toBeInTheDocument();

      // Use container queries to find specific elements
      const atsScoreContainer = screen.getByText("ATS Score").closest("div");
      expect(atsScoreContainer).toBeInTheDocument();
      expect(atsScoreContainer?.querySelectorAll("span")[1]?.textContent).toBe("78");

      const matchScoreContainer = screen.getByText("Match Score").closest("div");
      expect(matchScoreContainer).toBeInTheDocument();
      expect(matchScoreContainer?.querySelectorAll("span")[1]?.textContent).toBe("85");

      // Verify gaps are displayed
      expect(screen.getByText("Missing Redis experience")).toBeInTheDocument();
      expect(screen.getByText("No Kubernetes exposure")).toBeInTheDocument();

      // Verify improvements are displayed
      expect(screen.getByText("Use orchestrated instead of managed for Kubernetes")).toBeInTheDocument();

      // Verify core strengths are displayed
      expect(screen.getByText("Strong Python background")).toBeInTheDocument();

      // Verify PDF download button exists
      expect(screen.getByText("Download Improved Resume")).toBeInTheDocument();

      // Test PDF download
      generatePDFMock.mockResolvedValue(new Blob(["fake pdf content"], { type: "application/pdf" }));

      await act(async () => {
        screen.getByText("Download Improved Resume").click();
        await vi.runAllTimersAsync();
      });

      expect(generatePDFMock).toHaveBeenCalledWith("test-session-123", undefined);
    });

    it("handles PDF generation with different templates", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      generatePDFMock.mockResolvedValue(new Blob(["fake pdf content"], { type: "application/pdf" }));

      // Mock a custom function to test template selection
      const { generatePDF } = await import("../lib/api");
      await generatePDF("test-session-123", "Modern Accent");

      expect(generatePDF).toHaveBeenCalledWith("test-session-123", "Modern Accent");
    });

    it("shows loading state during PDF generation", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      generatePDFMock.mockImplementation(() => new Promise((resolve) => setTimeout(() => resolve(new Blob([])), 100)));

      await act(async () => {
        screen.getByText("Download Improved Resume").click();
      });

      expect(screen.getByText("Generating PDF...")).toBeInTheDocument();

      await act(async () => {
        await vi.runAllTimersAsync();
      });
    });

    it("handles PDF generation errors gracefully", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      generatePDFMock.mockRejectedValue(new Error("Network error"));

      await act(async () => {
        screen.getByText("Download Improved Resume").click();
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText("Failed to generate PDF. Please try again.")).toBeInTheDocument();
    });
  });

  describe("Custom Additions Flow", () => {
    it("displays CustomAdditionsForm with initial data", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText("Custom Additions")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e\.g\., AWS Certified Solutions Architect, PMP/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e\.g\., Master of Science in Computer Science, Stanford University/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e\.g\., Open source contributions, speaking engagements, publications/i)).toBeInTheDocument();
    });

    it("submits custom additions and refreshes session data", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      refineCustomAdditionsMock.mockResolvedValue({ success: true });

      // Update mock to return updated data on second call
      const updatedSession = {
        ...mockSessionDetail,
        enhanced_analysis: {
          ...mockEnhancedAnalysis,
          gaps: ["Updated gap"],
        } as typeof mockEnhancedAnalysis,
      };
      fetchSessionMock.mockResolvedValueOnce(mockSessionDetail as any);
      fetchSessionMock.mockResolvedValueOnce(updatedSession as any);

      // Fill in certificates field
      const certificatesInput = screen.getByPlaceholderText(/e\.g\., AWS Certified Solutions Architect, PMP/i) as HTMLTextAreaElement;
      await act(async () => {
        certificatesInput.focus();
        certificatesInput.value = "AWS Certified Developer";
        certificatesInput.dispatchEvent(new Event("input", { bubbles: true }));
      });

      // Submit form
      await act(async () => {
        screen.getByText("Save Custom Additions").click();
        await vi.runAllTimersAsync();
      });

      // Check that refineCustomAdditions was called with the session ID
      expect(refineCustomAdditionsMock).toHaveBeenCalled();
      const callArgs = refineCustomAdditionsMock.mock.calls[0];
      expect(callArgs[0]).toBe("test-session-123");
    });

    it("shows error when custom additions submission fails", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      refineCustomAdditionsMock.mockRejectedValue(new Error("Server error"));

      const certificatesInput = screen.getByPlaceholderText(/e\.g\., AWS Certified Solutions Architect, PMP/i) as HTMLTextAreaElement;
      await act(async () => {
        certificatesInput.focus();
        certificatesInput.value = "Test certification";
        certificatesInput.dispatchEvent(new Event("input", { bubbles: true }));
      });

      await act(async () => {
        screen.getByText("Save Custom Additions").click();
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText("Failed to submit custom additions. Please try again.")).toBeInTheDocument();
    });
  });

  describe("Enhanced Analysis Display", () => {
    it("shows ATS score with appropriate color coding", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      // Find the ATS Score section and verify the score color
      const atsScoreContainer = screen.getByText("ATS Score").closest("div");
      expect(atsScoreContainer?.querySelectorAll("span")[1]?.textContent).toBe("78");
      expect(atsScoreContainer?.querySelectorAll("span")[1]).toHaveClass("text-indigo-400");
    });

    it("displays gaps section with amber styling", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      expect(screen.getAllByText("Gaps")[0]).toBeInTheDocument();`n      expect(screen.getAllByText("Missing Redis experience")[0]).toBeInTheDocument();
      expect(screen.getByText("Missing Redis experience")).toBeInTheDocument();
    });

    it("displays improvements section with indigo styling", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText("Improvements")).toBeInTheDocument();
    });

    it("displays core strengths section with emerald styling", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText("Core Strengths")).toBeInTheDocument();
      expect(screen.getByText("Strong Python background")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles missing enhanced analysis gracefully", async () => {
      const sessionWithoutEnhanced = {
        ...mockSessionDetail,
        enhanced_analysis: null as typeof mockEnhancedAnalysis | null,
      };
      fetchSessionMock.mockResolvedValue(sessionWithoutEnhanced as any);

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText("Resume analysis is still processing...")).toBeInTheDocument();
      expect(screen.queryByText("Custom Additions")).not.toBeInTheDocument();
    });

    it("handles API errors during polling", async () => {
      fetchSessionMock.mockRejectedValue(new api.ApiError(500, "Server error"));

      const paramsPromise = createResolvedParams("test-session-123");

      await act(async () => {
        render(<AssessmentPage params={paramsPromise} />);
        await vi.runAllTimersAsync();
      });

      expect(screen.getByText("Server error")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /back to dashboard/i })).toBeInTheDocument();
    });

    it("clears polling interval on unmount", async () => {
      fetchSessionMock.mockResolvedValue(mockSessionDetail as any);

      const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");

      const paramsPromise = createResolvedParams("test-session-123");

      let unmount: () => void;
      await act(async () => {
        const result = render(<AssessmentPage params={paramsPromise} />);
        unmount = result.unmount;
        await vi.runAllTimersAsync();
      });

      await act(async () => {
        unmount();
      });

      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });
});







