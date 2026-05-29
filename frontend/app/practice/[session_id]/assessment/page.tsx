"use client";

import { useState, useEffect, useRef, use } from "react";
import { useRouter } from "next/navigation";
import { fetchSession, ApiError } from "@/lib/api";
import type { InterviewAssessment, DimensionScore, TranscriptTurn } from "@/types/session";

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 80) return "text-emerald-400";
  if (score >= 68) return "text-indigo-400";
  if (score >= 52) return "text-amber-400";
  return "text-red-400";
}

function verdictBadge(verdict: string) {
  const v = verdict.toLowerCase();
  if (v.includes("high") || v.includes("excellent") || v.includes("strong"))
    return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (v.includes("good") || v.includes("moderate"))
    return "bg-indigo-500/15 text-indigo-300 border-indigo-500/30";
  if (v.includes("average") || v.includes("fair"))
    return "bg-amber-500/15 text-amber-300 border-amber-500/30";
  return "bg-red-500/15 text-red-300 border-red-500/30";
}

function qualityColor(quality: string) {
  if (quality === "complete") return "bg-emerald-500/15 text-emerald-400";
  if (quality === "partial") return "bg-amber-500/15 text-amber-400";
  return "bg-red-500/15 text-red-400";
}

// Matches the actual LLM output keys: technical, job_fit, communication, confidence
const DIM_ACCENT: Record<string, { bar: string; score: string }> = {
  technical:    { bar: "bg-indigo-500",  score: "text-indigo-400"  },
  job_fit:      { bar: "bg-emerald-500", score: "text-emerald-400" },
  communication:{ bar: "bg-amber-500",   score: "text-amber-400"   },
  confidence:   { bar: "bg-purple-500",  score: "text-purple-400"  },
};

// ── Dimension card ────────────────────────────────────────────────────────────

function DimensionCard({ dimKey, dim }: { dimKey: string; dim: DimensionScore }) {
  const accent = DIM_ACCENT[dimKey] ?? { bar: "bg-zinc-500", score: "text-zinc-300" };
  const hasStrengths = dim.strengths?.length > 0;
  const hasGaps = dim.gaps?.length > 0;

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 flex flex-col gap-4">
      {/* Title + score */}
      <div className="flex items-center justify-between">
        <span className="text-zinc-100 font-semibold text-sm">{dim.label}</span>
        <span className={`${accent.score} font-bold text-lg tabular-nums`}>
          {dim.score}
          <span className="text-zinc-500 text-xs font-normal">/{dim.max_score}</span>
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-700 rounded-full h-1.5">
        <div
          className={`${accent.bar} h-1.5 rounded-full transition-all`}
          style={{ width: `${Math.min(dim.score, 100)}%` }}
        />
      </div>

      {/* Verdict badge */}
      <span className={`self-start text-xs px-2.5 py-0.5 rounded border font-medium ${verdictBadge(dim.verdict)}`}>
        Verdict: {dim.verdict}
      </span>

      {/* Evidence quote */}
      {dim.evidence && (
        <p className="text-zinc-400 text-xs italic leading-relaxed border-l-2 border-slate-600 pl-3">
          "{dim.evidence}"
        </p>
      )}

      {/* Strengths + Gaps */}
      {(hasStrengths || hasGaps) && (
        <div className={`grid gap-4 pt-1 ${hasStrengths && hasGaps ? "grid-cols-2" : "grid-cols-1"}`}>
          {hasStrengths && (
            <div>
              <p className="text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
                Strengths
              </p>
              <ul className="space-y-1.5">
                {dim.strengths.map((s, i) => (
                  <li key={i} className="text-zinc-300 text-xs flex items-start gap-1.5">
                    <span className="text-emerald-500 shrink-0 mt-0.5">•</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {hasGaps && (
            <div>
              <p className="text-red-400 text-xs font-semibold uppercase tracking-wider mb-2">
                Gaps
              </p>
              <ul className="space-y-1.5">
                {dim.gaps.map((g, i) => (
                  <li key={i} className="text-zinc-300 text-xs flex items-start gap-1.5">
                    <span className="text-red-400 shrink-0 mt-0.5">•</span>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Transcript view ───────────────────────────────────────────────────────────

function TranscriptView({ turns }: { turns: TranscriptTurn[] }) {
  if (!turns.length) {
    return <p className="text-zinc-500 text-sm">No transcript available.</p>;
  }

  return (
    <div className="space-y-3">
      {turns.map((turn, i) => {
        const isAgent = turn.speaker === "agent";
        return (
          <div key={i} className={`flex gap-3 ${isAgent ? "" : "flex-row-reverse"}`}>
            {/* Avatar */}
            <div
              className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                isAgent
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-700 text-zinc-300"
              }`}
            >
              {isAgent ? "AI" : "C"}
            </div>
            {/* Bubble */}
            <div
              className={`max-w-[78%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                isAgent
                  ? "bg-slate-800 border border-slate-700 text-zinc-300"
                  : "bg-indigo-600/20 border border-indigo-500/30 text-zinc-200"
              }`}
            >
              <span className={`block text-xs font-semibold mb-1 ${isAgent ? "text-indigo-400" : "text-zinc-400"}`}>
                {isAgent ? "Aria (AI Interviewer)" : "Candidate"}
              </span>
              {turn.text}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Loading / Error ───────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 gap-6">
      <div className="relative flex items-center justify-center">
        <span className="absolute inline-flex h-16 w-16 rounded-full bg-indigo-500/30 animate-ping" />
        <span className="relative inline-flex h-10 w-10 rounded-full bg-indigo-500" />
      </div>
      <p className="text-zinc-400 text-sm">Generating your assessment scorecard...</p>
    </main>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 gap-4">
      <p className="text-red-400 text-sm">{message}</p>
    </main>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "scorecard" | "transcript";

export default function AssessmentPage({
  params,
}: {
  params: Promise<{ session_id: string }>;
}) {
  const { session_id } = use(params);
  const router = useRouter();

  const [assessment, setAssessment] = useState<InterviewAssessment | null>(null);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("scorecard");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await fetchSession(session_id);
        if (data.status === "completed") {
          clearInterval(intervalRef.current!);
          setAssessment(data.interview_assessment);
          setTranscript(data.transcript ?? []);
          setCompleted(true);
        } else if (data.status === "grading_failed") {
          clearInterval(intervalRef.current!);
          setError("Assessment grading failed. Please check server logs or try again.");
        }
      } catch (err) {
        clearInterval(intervalRef.current!);
        setError(err instanceof ApiError ? err.detail : "Failed to load assessment.");
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [session_id]);

  if (error) return <ErrorState message={error} />;
  if (!completed || !assessment) return <LoadingState />;

  const pct = Math.round(assessment.completion_ratio * 100);

  return (
    <div className="min-h-screen bg-slate-900 text-zinc-100">
      {/* Top bar */}
      <div className="border-b border-slate-800 px-8 py-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-zinc-100">Interview Assessment Report</span>
        <button
          onClick={() => router.push("/dashboard")}
          className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-zinc-400 border border-slate-700 transition-colors"
        >
          Dashboard
        </button>
      </div>

      <div className="max-w-5xl mx-auto px-8 py-8 space-y-8">

        {/* Score header */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-4">
              <div>
                <span className="text-zinc-400 text-sm font-medium">Practice Score: </span>
                <span className={`text-2xl font-bold tabular-nums ${scoreColor(assessment.overall_score)}`}>
                  {assessment.overall_score}/100
                </span>
              </div>
              {assessment.candidate_level && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-slate-700 text-zinc-400 border border-slate-600 capitalize">
                  {assessment.candidate_level}
                </span>
              )}
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <span className={`text-sm font-semibold px-3 py-1 rounded border ${verdictBadge(assessment.practice_verdict)}`}>
                {assessment.practice_verdict}
              </span>
            </div>
          </div>

          {assessment.summary && (
            <p className="text-zinc-300 text-sm leading-relaxed">{assessment.summary}</p>
          )}

          {assessment.advance_reasoning && (
            <p className="mt-3 text-zinc-500 text-xs italic border-l-2 border-slate-600 pl-3">
              {assessment.advance_reasoning}
            </p>
          )}

          {/* Completion bar */}
          <div className="mt-5 pt-5 border-t border-slate-700">
            <div className="flex justify-between text-xs text-zinc-500 mb-1.5">
              <span>
                Session completion
                {assessment.interview_quality && (
                  <span className={`ml-2 px-1.5 py-0.5 rounded text-xs ${qualityColor(assessment.interview_quality)}`}>
                    {assessment.interview_quality}
                  </span>
                )}
              </span>
              <span>{pct}% · {assessment.turns_analyzed} turns</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-1.5">
              <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-800 flex gap-0">
          {(["scorecard", "transcript"] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2.5 text-sm font-medium capitalize transition-colors border-b-2 ${
                activeTab === tab
                  ? "text-zinc-100 border-indigo-500"
                  : "text-zinc-500 hover:text-zinc-300 border-transparent"
              }`}
            >
              {tab === "scorecard" ? "Scorecard" : `Transcript (${transcript.length} turns)`}
            </button>
          ))}
        </div>

        {/* Scorecard tab */}
        {activeTab === "scorecard" && (
          <div className="space-y-8">

            {/* Overall strengths / gaps / red flags */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <p className="text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-3">
                  Overall Strengths
                </p>
                {assessment.overall_strengths.length > 0 ? (
                  <ul className="space-y-2">
                    {assessment.overall_strengths.map((s, i) => (
                      <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                        <span className="text-emerald-500 shrink-0 mt-0.5">•</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-zinc-500 text-xs">None identified</p>
                )}
              </div>

              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <p className="text-amber-400 text-xs font-semibold uppercase tracking-wider mb-3">
                  Overall Gaps
                </p>
                {assessment.overall_gaps.length > 0 ? (
                  <ul className="space-y-2">
                    {assessment.overall_gaps.map((g, i) => (
                      <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                        <span className="text-amber-400 shrink-0 mt-0.5">•</span>
                        {g}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-zinc-500 text-xs">None identified</p>
                )}
              </div>

              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <p className="text-red-400 text-xs font-semibold uppercase tracking-wider mb-3">
                  Red Flags
                </p>
                {(assessment.red_flags ?? []).length > 0 ? (
                  <ul className="space-y-2">
                    {assessment.red_flags!.map((f, i) => (
                      <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                        <span className="text-red-400 shrink-0 mt-0.5">⚠</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-zinc-500 text-xs">None identified</p>
                )}
              </div>
            </div>

            {/* Dimension cards */}
            <div>
              <p className="text-zinc-500 text-xs font-semibold uppercase tracking-wider mb-4">
                Dimension Breakdown
              </p>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {Object.entries(assessment.dimension_scores).map(([key, dim]) => (
                  <DimensionCard key={key} dimKey={key} dim={dim} />
                ))}
              </div>
            </div>

            {/* Technical probes */}
            {assessment.technical_round_probes.length > 0 && (
              <div>
                <p className="text-zinc-500 text-xs font-semibold uppercase tracking-wider mb-4">
                  Prepare for These Questions
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {assessment.technical_round_probes.map((probe, i) => (
                    <div
                      key={i}
                      className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 flex flex-col gap-2"
                    >
                      <span className="text-indigo-400 text-xs font-bold">#{i + 1}</span>
                      <p className="text-zinc-300 text-sm leading-relaxed">{probe}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Transcript tab */}
        {activeTab === "transcript" && (
          <div className="bg-slate-800/30 border border-slate-700 rounded-xl p-6">
            <p className="text-zinc-500 text-xs font-semibold uppercase tracking-wider mb-6">
              Full Interview Transcript
            </p>
            <TranscriptView turns={transcript} />
          </div>
        )}

      </div>
    </div>
  );
}
