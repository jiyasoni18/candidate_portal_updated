import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ResumeReport from "../components/ResumeReport";

describe("ResumeReport", () => {
  it("renders loading state when enhancedAnalysis is null", () => {
    render(<ResumeReport enhancedAnalysis={null} />);

    expect(screen.getByText("Resume Report")).toBeInTheDocument();
    expect(screen.getByText("Resume analysis is still processing...")).toBeInTheDocument();
  });

  it("renders ATS Score and Match Score when data is available", () => {
    const enhancedAnalysis = {
      match_score: 85,
      ats_score: 78,
      ats_explanation: "Good keyword usage detected",
      gaps: ["Python", "Django"],
      improvements: ["Use 'Python' instead of 'python'"],
      core_strengths: ["Problem solving", "Communication"],
      summary: "Strong alignment with job description",
      explanation: "The resume matches well with the job requirements",
    };

    render(<ResumeReport enhancedAnalysis={enhancedAnalysis} />);

    expect(screen.getByText("ATS Score")).toBeInTheDocument();
    expect(screen.getByText("78")).toBeInTheDocument();
    expect(screen.getByText("Match Score")).toBeInTheDocument();
    expect(screen.getByText("85")).toBeInTheDocument();
  });

  it("displays core strengths section when available", () => {
    const enhancedAnalysis = {
      match_score: 85,
      ats_score: 78,
      ats_explanation: "Good keyword usage detected",
      gaps: [],
      improvements: [],
      core_strengths: ["Python", "System Design"],
      summary: "Strong alignment",
      explanation: "Good match",
    };

    render(<ResumeReport enhancedAnalysis={enhancedAnalysis} />);

    expect(screen.getByText("Core Strengths")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("System Design")).toBeInTheDocument();
  });

  it("displays gaps section when available", () => {
    const enhancedAnalysis = {
      match_score: 85,
      ats_score: 78,
      ats_explanation: "Good keyword usage detected",
      gaps: ["Kubernetes", "AWS"],
      improvements: [],
      core_strengths: [],
      summary: "Strong alignment",
      explanation: "Good match",
    };

    render(<ResumeReport enhancedAnalysis={enhancedAnalysis} />);

    expect(screen.getByText("Gaps")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    expect(screen.getByText("AWS")).toBeInTheDocument();
  });

  it("displays improvements section when available", () => {
    const enhancedAnalysis = {
      match_score: 85,
      ats_score: 78,
      ats_explanation: "Good keyword usage detected",
      gaps: [],
      improvements: ["Use 'Python' instead of 'python'", "Add project links"],
      core_strengths: [],
      summary: "Strong alignment",
      explanation: "Good match",
    };

    render(<ResumeReport enhancedAnalysis={enhancedAnalysis} />);

    expect(screen.getByText("Improvements")).toBeInTheDocument();
    expect(screen.getByText("Use 'Python' instead of 'python'")).toBeInTheDocument();
    expect(screen.getByText("Add project links")).toBeInTheDocument();
  });

  it("applies correct color classes based on ATS score", () => {
    const enhancedAnalysis = {
      match_score: 85,
      ats_score: 92,
      ats_explanation: "Excellent ATS score",
      gaps: [],
      improvements: [],
      core_strengths: [],
      summary: "Excellent match",
      explanation: "Perfect match",
    };

    render(<ResumeReport enhancedAnalysis={enhancedAnalysis} />);

    expect(screen.getByText("92")).toHaveClass("text-emerald-400");
  });

  it("applies correct color classes based on match score", () => {
    const enhancedAnalysis = {
      match_score: 45,
      ats_score: 78,
      ats_explanation: "Good keyword usage detected",
      gaps: [],
      improvements: [],
      core_strengths: [],
      summary: "Weak match",
      explanation: "Needs improvement",
    };

    render(<ResumeReport enhancedAnalysis={enhancedAnalysis} />);

    expect(screen.getByText("45")).toHaveClass("text-red-400");
  });
});
