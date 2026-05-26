import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AssessmentPage from "../app/practice/[session_id]/assessment/page";
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
  return { fetchSession: vi.fn(), ApiError };
});

const fetchSessionMock = vi.mocked(api.fetchSession);

const fullAssessment = {
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
};

const completedSession = {
  session_id: "test-session-123",
  status: "completed",
  created_at: "2024-01-15T10:30:00Z",
  job: { id: "job-1", title: "Senior Engineer" },
  resume_report: null,
  resume_score: null,
  interview_assessment: fullAssessment,
};

describe("AssessmentPage", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders loading state initially", async () => {
    fetchSessionMock.mockResolvedValue({ ...completedSession, status: "interviewing" } as any);

    await act(async () => {
      render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
    });

    expect(screen.getByText("Generating your assessment scorecard...")).toBeInTheDocument();
  });

  it("renders practice_verdict and overall_score when completed", async () => {
    fetchSessionMock.mockResolvedValue(completedSession as any);

    await act(async () => {
      render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Strong Alignment")).toBeInTheDocument();
    expect(screen.getByText("74")).toBeInTheDocument();
  });

  it("renders all 4 dimension labels", async () => {
    fetchSessionMock.mockResolvedValue(completedSession as any);

    await act(async () => {
      render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Technical Familiarity")).toBeInTheDocument();
    expect(screen.getByText("Role Alignment")).toBeInTheDocument();
    expect(screen.getByText("Communication")).toBeInTheDocument();
    expect(screen.getByText("Presence")).toBeInTheDocument();
  });

  it("renders all 3 technical probe strings", async () => {
    fetchSessionMock.mockResolvedValue(completedSession as any);

    await act(async () => {
      render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Explain your approach to distributed caching.")).toBeInTheDocument();
    expect(screen.getByText("How would you design a rate limiter?")).toBeInTheDocument();
    expect(screen.getByText("Describe a time you optimized a slow query.")).toBeInTheDocument();
  });

  it("renders completion ratio and turns analyzed", async () => {
    fetchSessionMock.mockResolvedValue(completedSession as any);

    await act(async () => {
      render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("88%")).toBeInTheDocument();
    expect(screen.getByText("22 turns analyzed")).toBeInTheDocument();
  });

  it("shows processing message when interview_assessment is null on completed session", async () => {
    fetchSessionMock.mockResolvedValue({
      ...completedSession,
      interview_assessment: null,
    } as any);

    await act(async () => {
      render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Assessment is still processing...")).toBeInTheDocument();
  });

  it("renders error state with dashboard link on fetch failure", async () => {
    const { ApiError } = api as any;
    fetchSessionMock.mockRejectedValue(new ApiError(500, "Server error."));

    await act(async () => {
      render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Server error.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to dashboard/i })).toHaveAttribute(
      "href",
      "/dashboard"
    );
  });

  it("clears polling interval on unmount", async () => {
    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");
    fetchSessionMock.mockResolvedValue({ ...completedSession, status: "interviewing" } as any);

    let unmount: () => void;
    await act(async () => {
      const result = render(<AssessmentPage params={{ session_id: "test-session-123" }} />);
      unmount = result.unmount;
      await vi.runAllTimersAsync();
    });

    await act(async () => {
      unmount();
    });

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
