"use client";

import type { EnhancedAnalysis } from "@/types/session";

interface ResumeReportProps {
  enhancedAnalysis: EnhancedAnalysis | null;
}

export default function ResumeReport({ enhancedAnalysis }: ResumeReportProps) {
  if (!enhancedAnalysis) {
    return (
      <div className="w-full max-w-2xl">
        <h2 className="text-zinc-100 font-semibold mb-4">Resume Report</h2>
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 text-center">
          <p className="text-zinc-500 text-sm">Resume analysis is still processing...</p>
        </div>
      </div>
    );
  }

  const { ats_score, match_score, gaps, improvements, core_strengths, summary } = enhancedAnalysis;

  return (
    <div className="w-full max-w-2xl">
      <h2 className="text-zinc-100 font-semibold mb-4">Resume Report</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
          <span className="text-zinc-500 text-xs font-medium uppercase tracking-wider">ATS Score</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-3xl font-bold ${getScoreColor(ats_score)}`}>{ats_score}</span>
            <span className="text-zinc-500 text-sm">/100</span>
          </div>
          <p className="text-zinc-400 text-xs mt-2 leading-relaxed">
            {enhancedAnalysis.ats_explanation}
          </p>
        </div>
        
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
          <span className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Match Score</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-3xl font-bold ${getScoreColor(match_score)}`}>{match_score}</span>
            <span className="text-zinc-500 text-sm">/100</span>
          </div>
          <p className="text-zinc-400 text-xs mt-2 leading-relaxed">
            {enhancedAnalysis.summary}
          </p>
        </div>
      </div>

      {core_strengths && core_strengths.length > 0 && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 mb-4">
          <h3 className="text-emerald-400 font-semibold text-sm mb-3">Core Strengths</h3>
          <ul className="space-y-2">
            {core_strengths.map((strength, i) => (
              <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                <span className="text-emerald-500 mt-0.5">✓</span>
                {strength}
              </li>
            ))}
          </ul>
        </div>
      )}

      {gaps && gaps.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-5 mb-4">
          <h3 className="text-amber-400 font-semibold text-sm mb-3">Gaps</h3>
          <ul className="space-y-2">
            {gaps.map((gap, i) => (
              <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                <span className="text-amber-500 mt-0.5">•</span>
                {gap}
              </li>
            ))}
          </ul>
        </div>
      )}

      {improvements && improvements.length > 0 && (
        <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl p-5">
          <h3 className="text-indigo-400 font-semibold text-sm mb-3">Improvements</h3>
          <ul className="space-y-2">
            {improvements.map((improvement, i) => (
              <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
                <span className="text-indigo-500 mt-0.5">→</span>
                {improvement}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function getScoreColor(score: number | null | undefined): string {
  if (score == null) return "text-zinc-400";
  if (score >= 80) return "text-emerald-400";
  if (score >= 68) return "text-indigo-400";
  if (score >= 52) return "text-amber-400";
  return "text-red-400";
}
