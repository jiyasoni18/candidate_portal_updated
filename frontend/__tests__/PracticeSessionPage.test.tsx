import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PracticeSessionPage from "../app/practice/[session_id]/page";
import * as api from "../lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock next/link
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

// Mock the api module
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
    ApiError,
  };
});

const fetchSessionMock = vi.mocked(api.fetchSession);

const baseSession = {
  session_id: "test-session-123",
  status: "parsing",
  created_at: "2024-01-15T10:30:00Z",
  job: { id: "job-1", title: "Senior Engineer" },
  resume_report: null,
  resume_score: null,
};

const readySession = {
  ...baseSession,
  status: "ready_to_start",
  resume_score: 82,
  resume_report: {
    score: 82,
    reference_to_jd: "Strong match for the role.",
    strengths: ["Python expertise", "API design"],
    weaknesses: ["No Kubernetes experience"],
  },
};

describe("PracticeSessionPage", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ── ProcessingCanvas ──────────────────────────────────────────────────────

  it('renders parsing message when status is "parsing"', async () => {
    fetchSessionMock.mockResolvedValue({ ...baseSession, status: "parsing" } as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(
      screen.getByText("Aria is parsing your resume structural text layout...")
    ).toBeInTheDocument();
  });

  it('renders scoring message when status is "scoring"', async () => {
    fetchSessionMock.mockResolvedValue({ ...baseSession, status: "scoring" } as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(
      screen.getByText(
        "Gemini is cross-referencing your background history against the target Job Description..."
      )
    ).toBeInTheDocument();
  });

  // ── ScoreMeter ────────────────────────────────────────────────────────────

  it("applies emerald classes for score >= 75", async () => {
    fetchSessionMock.mockResolvedValue({
      ...readySession,
      resume_report: { ...readySession.resume_report, score: 80 },
    } as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    const scoreEl = screen.getByText("80");
    expect(scoreEl.className).toContain("text-emerald-400");
    expect(screen.getByText("High Alignment")).toBeInTheDocument();
  });

  it("applies indigo classes for score >= 60 and < 75", async () => {
    fetchSessionMock.mockResolvedValue({
      ...readySession,
      resume_report: { ...readySession.resume_report, score: 65 },
    } as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    const scoreEl = screen.getByText("65");
    expect(scoreEl.className).toContain("text-indigo-400");
    expect(screen.getByText("Moderate Alignment")).toBeInTheDocument();
  });

  it("applies amber classes for score < 60", async () => {
    fetchSessionMock.mockResolvedValue({
      ...readySession,
      resume_report: { ...readySession.resume_report, score: 45 },
    } as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    const scoreEl = screen.getByText("45");
    expect(scoreEl.className).toContain("text-amber-400");
    expect(screen.getByText("Gaps Flagged")).toBeInTheDocument();
  });

  // ── StrengthsCard & WeaknessesCard ────────────────────────────────────────

  it("renders correct item counts for strengths and weaknesses", async () => {
    fetchSessionMock.mockResolvedValue(readySession as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Python expertise")).toBeInTheDocument();
    expect(screen.getByText("API design")).toBeInTheDocument();
    expect(screen.getByText("No Kubernetes experience")).toBeInTheDocument();
  });

  it("renders strengths card without error when items is empty", async () => {
    fetchSessionMock.mockResolvedValue({
      ...readySession,
      resume_report: { ...readySession.resume_report, strengths: [] },
    } as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Core Strengths")).toBeInTheDocument();
  });

  it("renders weaknesses card without error when items is empty", async () => {
    fetchSessionMock.mockResolvedValue({
      ...readySession,
      resume_report: { ...readySession.resume_report, weaknesses: [] },
    } as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Preparation Gaps")).toBeInTheDocument();
  });

  // ── ErrorState ────────────────────────────────────────────────────────────

  it("renders ErrorState with dashboard link when fetchSession throws ApiError", async () => {
    const { ApiError } = api as any;
    fetchSessionMock.mockRejectedValue(new ApiError(404, "Session not found."));

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Session not found.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to dashboard/i })).toHaveAttribute(
      "href",
      "/dashboard"
    );
  });

  // ── Polling lifecycle ─────────────────────────────────────────────────────

  it("calls clearInterval when status reaches ready_to_start", async () => {
    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");
    fetchSessionMock.mockResolvedValue(readySession as any);

    await act(async () => {
      render(<PracticeSessionPage params={{ session_id: "test-session-123" }} />);
      await vi.runAllTimersAsync();
    });

    expect(clearIntervalSpy).toHaveBeenCalled();
  });

  it("calls clearInterval on component unmount", async () => {
    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");
    fetchSessionMock.mockResolvedValue({ ...baseSession, status: "parsing" } as any);

    let unmount: () => void;
    await act(async () => {
      const result = render(
        <PracticeSessionPage params={{ session_id: "test-session-123" }} />
      );
      unmount = result.unmount;
      await vi.runAllTimersAsync();
    });

    await act(async () => {
      unmount();
    });

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
