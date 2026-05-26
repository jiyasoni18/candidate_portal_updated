"use client";

import { useState, useEffect, useRef, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchSession, ApiError } from "@/lib/api";
import type { SessionDetail, MandatorySkillCheck, SectionScores } from "@/types/session";

// ── ProcessingCanvas ──────────────────────────────────────────────────────────

function ProcessingCanvas({ status }: { status: string | null }) {
  const messages: Record<string, string> = {
    parsing: "Aria is parsing your resume structural text layout...",
    scoring: "Gemini is cross-referencing your background against the Job Description...",
  };
  const message = (status && messages[status]) ?? "Initializing your practice session...";
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 gap-6">
      <div className="relative flex items-center justify-center">
        <span className="absolute inline-flex h-16 w-16 rounded-full bg-indigo-500/30 animate-ping" />
        <span className="relative inline-flex h-10 w-10 rounded-full bg-indigo-500" />
      </div>
      <p className="text-zinc-400 text-center max-w-md px-4 text-sm leading-relaxed">{message}</p>
      {status && (
        <span className="text-xs text-zinc-600 bg-slate-800 px-3 py-1 rounded-full">{status}</span>
      )}
    </main>
  );
}

// ── Score helpers ─────────────────────────────────────────────────────────────

function getScoreStyle(score: number | null) {
  if (score === null) return { color: "text-zinc-500", border: "border-zinc-700" };
  if (score >= 75) return { color: "text-emerald-400", border: "border-emerald-500/40" };
  if (score >= 60) return { color: "text-indigo-400", border: "border-indigo-500/40" };
  return { color: "text-amber-400", border: "border-amber-500/40" };
}

// ── Section constants ─────────────────────────────────────────────────────────

const SECTION_LABELS: Record<string, string> = {
  experience: "Experience",
  core_skills: "Core Skills",
  good_to_have: "Good-to-Have",
  consistency: "Consistency",
  education: "Education",
  ai_holistic: "AI Holistic",
};

const SECTION_MAX: Record<string, number> = {
  experience: 20,
  core_skills: 30,
  good_to_have: 15,
  consistency: 15,
  education: 10,
  ai_holistic: 10,
};

// ── Mandatory skills table ────────────────────────────────────────────────────

const STATUS_STYLE: Record<string, string> = {
  "PRESENT + PROVEN": "text-emerald-400",
  "PRESENT + WEAK": "text-amber-400",
  ABSENT: "text-red-400",
};

function SkillsTable({ skills }: { skills: MandatorySkillCheck[] }) {
  return (
    <div>
      <span className="text-zinc-500 text-xs font-medium uppercase tracking-wider block mb-3">
        Mandatory Skills Check
      </span>
      <div className="border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-800/50">
              <th className="text-left px-4 py-2.5 text-zinc-500 text-xs font-medium">Skill</th>
              <th className="text-left px-4 py-2.5 text-zinc-500 text-xs font-medium">Status</th>
              <th className="text-left px-4 py-2.5 text-zinc-500 text-xs font-medium hidden md:table-cell">
                Evidence
              </th>
            </tr>
          </thead>
          <tbody>
            {skills.map((s, i) => (
              <tr key={i} className="border-b border-slate-800 last:border-0">
                <td className="px-4 py-2.5 text-zinc-300 font-medium">{s.skill}</td>
                <td
                  className={`px-4 py-2.5 font-medium text-xs ${STATUS_STYLE[s.status] ?? "text-zinc-400"}`}
                >
                  {s.status}
                </td>
                <td className="px-4 py-2.5 text-zinc-500 text-xs hidden md:table-cell">
                  {s.evidence}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── ListCard ──────────────────────────────────────────────────────────────────

const accentMap = {
  emerald: {
    heading: "text-emerald-400",
    icon: "text-emerald-500",
    bg: "bg-emerald-500/5 border-emerald-500/20",
  },
  amber: {
    heading: "text-amber-400",
    icon: "text-amber-500",
    bg: "bg-amber-500/5 border-amber-500/20",
  },
  indigo: {
    heading: "text-indigo-400",
    icon: "text-indigo-500",
    bg: "bg-indigo-500/5 border-indigo-500/20",
  },
};

function ListCard({
  title,
  items,
  accent,
  icon,
}: {
  title: string;
  items: string[];
  accent: keyof typeof accentMap;
  icon: string;
}) {
  const { heading, icon: iconColor, bg } = accentMap[accent];
  return (
    <div className={`border rounded-xl p-5 h-full ${bg}`}>
      <h3 className={`font-semibold text-sm mb-3 ${heading}`}>{title}</h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-zinc-300 text-sm flex items-start gap-2">
            <span className={`${iconColor} mt-0.5 shrink-0 font-bold`}>{icon}</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Tab types ─────────────────────────────────────────────────────────────────

type Tab = "overview" | "section_scores" | "section_reasons" | "skills_check" | "alerts";

// ── Section descriptions ──────────────────────────────────────────────────────

const SECTION_DESC: Record<string, string> = {
  experience: "Years + quality of work experience",
  core_skills: "Non-negotiable skill coverage",
  good_to_have: "Bonus skills and preferred qualifications",
  consistency: "Job tenure and career stability",
  education: "Degree level and institution quality",
  ai_holistic: "Holistic signals not captured by other sections",
};

const SECTION_COLORS: Record<string, string> = {
  experience: "bg-indigo-500",
  core_skills: "bg-red-500",
  good_to_have: "bg-emerald-500",
  consistency: "bg-amber-500",
  education: "bg-purple-500",
  ai_holistic: "bg-sky-500",
};

const SECTION_DOT: Record<string, string> = {
  experience: "bg-indigo-400",
  core_skills: "bg-red-400",
  good_to_have: "bg-emerald-400",
  consistency: "bg-amber-400",
  education: "bg-purple-400",
  ai_holistic: "bg-sky-400",
};

// ── AlignmentReport ───────────────────────────────────────────────────────────

function AlignmentReport({ session }: { session: SessionDetail }) {
  const router = useRouter();
  const report = session.resume_report;
  const e = session.enhanced_analysis;
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const matchScore = e?.match_score ?? report?.score ?? null;
  const atsScore = e?.ats_score ?? null;
  const summary = e?.summary ?? report?.reference_to_jd ?? "";
  const strengths = (e?.strengths?.length ? e.strengths : report?.strengths) ?? [];
  const gaps = (e?.gaps?.length ? e.gaps : report?.weaknesses) ?? [];
  const improvements = e?.improvements ?? [];
  const hasSectionScores = e?.section_scores && Object.keys(e.section_scores).length > 0;
  const hasSkillsCheck = (e?.mandatory_skills_check?.length ?? 0) > 0;
  const flags = e?.flags;
  const alertCount =
    (flags?.integrity_alert ? 1 : 0) +
    (flags?.unexplained_gap_found ? 1 : 0) +
    (flags?.freelance_flag ? 1 : 0) +
    (flags?.jd_title_skill_failed ? 1 : 0);

  // Hire recommendation based on match score
  const isMatch = matchScore !== null && matchScore >= 70;
  const matchLabel = matchScore === null ? "—" : isMatch ? "Good Fit" : "Needs Work";
  const matchLabelColor = isMatch ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" : "text-amber-400 bg-amber-500/10 border-amber-500/30";

  const tabs: { id: Tab; label: string; badge?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "section_scores", label: "Section Scores" },
    { id: "section_reasons", label: "Section Reasons" },
    { id: "skills_check", label: "Skills Check" },
    { id: "alerts", label: "Alerts", badge: alertCount },
  ];

  return (
    <main className="h-screen bg-slate-900 flex flex-col overflow-hidden">

      {/* ── Top nav ── */}
      <div className="shrink-0 border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold text-zinc-100">Resume Alignment Report</span>
          <p className="text-zinc-500 text-xs mt-0.5">AI assessment: scores, skill checks, flags, and gap analysis</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => router.push("/dashboard")}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-zinc-400 border border-slate-700 transition-colors"
          >
            Dashboard
          </button>
          <button
            onClick={() => router.push(`/practice/${session.session_id}/upgrade`)}
            className="px-4 py-1.5 text-xs rounded-lg bg-slate-700 hover:bg-slate-600 text-zinc-100 font-semibold border border-slate-600 transition-colors"
          >
            Upgrade Resume ↑
          </button>
          <button
            onClick={() => router.push(`/interview/${session.session_id}`)}
            className="px-4 py-1.5 text-xs rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors"
          >
            Start Interview →
          </button>
        </div>
      </div>

      {/* ── Score header ── */}
      <div className="shrink-0 border-b border-slate-800 px-8 py-6 flex items-center gap-8">
        {/* JD Match */}
        <div className="flex items-end gap-2">
          <span className={`text-7xl font-bold tabular-nums leading-none ${getScoreStyle(matchScore).color}`}>
            {matchScore ?? "—"}
          </span>
          <span className="text-zinc-500 text-sm mb-1">out of 100</span>
        </div>

        <div className="w-px h-12 bg-slate-700" />

        {/* Fit badge */}
        <div className="flex flex-col gap-1">
          <span className={`text-sm font-semibold px-3 py-1 rounded-full border ${matchLabelColor}`}>
            {matchLabel}
          </span>
          <span className="text-zinc-500 text-xs">JD Match</span>
        </div>

        <div className="w-px h-12 bg-slate-700" />

        {/* ATS Score */}
        <div className="flex flex-col gap-1">
          <span className={`text-3xl font-bold tabular-nums ${getScoreStyle(atsScore).color}`}>
            {atsScore ?? "—"}
          </span>
          <span className="text-zinc-500 text-xs">ATS Score</span>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="shrink-0 border-b border-slate-800 px-8 flex gap-0">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-4 py-3 text-sm font-medium transition-colors flex items-center gap-1.5 ${
                isActive
                  ? "text-zinc-100 border-b-2 border-indigo-500"
                  : "text-zinc-500 hover:text-zinc-300 border-b-2 border-transparent"
              }`}
            >
              {tab.label}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="text-xs bg-red-500/20 text-red-400 border border-red-500/30 rounded-full px-1.5 py-0.5 leading-none">
                  {tab.badge}
                </span>
              )}
              {tab.badge === 0 && (
                <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full px-1.5 py-0.5 leading-none">
                  ✓
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Tab content ── */}
      <div className="flex-1 overflow-y-auto px-8 py-6">

        {/* OVERVIEW */}
        {activeTab === "overview" && (
          <div className="space-y-6 w-full">
            {summary && (
              <div>
                <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider mb-2">Summary</p>
                <p className="text-zinc-200 text-base leading-relaxed">{summary}</p>
              </div>
            )}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
              {strengths.length > 0 && (
                <ListCard title="Strengths" items={strengths} accent="emerald" icon="✓" />
              )}
              {gaps.length > 0 && (
                <ListCard title="Gaps" items={gaps} accent="amber" icon="!" />
              )}
              {improvements.length > 0 && (
                <ListCard title="Terminology Improvements" items={improvements} accent="indigo" icon="→" />
              )}
            </div>
          </div>
        )}

        {/* SECTION SCORES */}
        {activeTab === "section_scores" && (
          <div className="w-full space-y-1">
            <p className="text-zinc-500 text-sm mb-6">
              Scores are broken into 5 weighted sections (total 90 pts) + an AI Holistic score (10 pts).
            </p>
            {hasSectionScores ? (
              Object.entries(e!.section_scores).map(([key, val]) => {
                const max = SECTION_MAX[key] ?? 10;
                const pct = val != null ? Math.round((val / max) * 100) : 0;
                const label = SECTION_LABELS[key] ?? key;
                const desc = SECTION_DESC[key] ?? "";
                const bar = SECTION_COLORS[key] ?? "bg-indigo-500";
                const dot = SECTION_DOT[key] ?? "bg-indigo-400";
                return (
                  <div key={key} className="py-5 border-b border-slate-800 last:border-0">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${dot}`} />
                        <span className="text-zinc-100 font-semibold text-sm">{label}</span>
                      </div>
                      <div className="flex items-baseline gap-1">
                        <span className={`text-xl font-bold tabular-nums ${pct >= 75 ? "text-emerald-400" : pct >= 50 ? "text-indigo-400" : "text-amber-400"}`}>
                          {val ?? 0}
                        </span>
                        <span className="text-zinc-500 text-xs">/ {max}</span>
                      </div>
                    </div>
                    {desc && <p className="text-zinc-500 text-xs mb-3 ml-4">{desc}</p>}
                    <div className="w-full bg-slate-800 rounded-full h-2.5">
                      <div className={`${bar} h-2.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-zinc-500 text-sm">Section scores not available.</p>
            )}
          </div>
        )}

        {/* SECTION REASONS */}
        {activeTab === "section_reasons" && (
          <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-4">
            {e?.section_reasons && Object.keys(e.section_reasons).length > 0 ? (
              Object.entries(e.section_reasons).map(([key, reason]) => {
                const label = SECTION_LABELS[key] ?? key;
                const dot = SECTION_DOT[key] ?? "bg-indigo-400";
                return (
                  <div key={key} className="bg-slate-800/40 border border-slate-700 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${dot}`} />
                      <span className="text-zinc-100 font-semibold text-sm">{label}</span>
                    </div>
                    <p className="text-zinc-400 text-sm leading-relaxed">{reason}</p>
                  </div>
                );
              })
            ) : (
              <p className="text-zinc-500 text-sm">Section reasons not available.</p>
            )}
          </div>
        )}

        {/* SKILLS CHECK */}
        {activeTab === "skills_check" && (
          <div className="w-full">
            {hasSkillsCheck ? (
              <SkillsTable skills={e!.mandatory_skills_check} />
            ) : (
              <p className="text-zinc-500 text-sm">Skills check not available.</p>
            )}
          </div>
        )}

        {/* ALERTS */}
        {activeTab === "alerts" && (
          <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-4">
            {alertCount === 0 ? (
              <div className="flex items-center gap-3 bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-5">
                <span className="text-emerald-400 text-xl">✓</span>
                <div>
                  <p className="text-emerald-400 font-semibold text-sm">No alerts</p>
                  <p className="text-zinc-500 text-xs mt-0.5">No date issues, gaps, or flags were detected.</p>
                </div>
              </div>
            ) : (
              <>
                {flags?.integrity_alert && (
                  <AlertCard
                    title="Date Integrity Alert"
                    desc="One or more dates on the resume appear inconsistent or suspicious."
                    color="red"
                    violations={flags.date_integrity_violations}
                  />
                )}
                {flags?.unexplained_gap_found && (
                  <AlertCard
                    title="Unexplained Employment Gap"
                    desc="There is a gap in employment history with no stated reason."
                    color="amber"
                  />
                )}
                {flags?.freelance_flag && (
                  <AlertCard
                    title="Mostly Freelance Experience"
                    desc="The majority of experience is freelance or contract, which may not align with this role's requirements."
                    color="amber"
                  />
                )}
                {flags?.jd_title_skill_failed && (
                  <AlertCard
                    title="Primary JD Skill Not Proven"
                    desc="The core skill required by the job title is not backed by concrete evidence in the resume."
                    color="red"
                  />
                )}
              </>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

// ── AlertCard ─────────────────────────────────────────────────────────────────

function AlertCard({
  title,
  desc,
  color,
  violations,
}: {
  title: string;
  desc: string;
  color: "red" | "amber";
  violations?: string[];
}) {
  const cls =
    color === "red"
      ? "bg-red-500/5 border-red-500/20 text-red-400"
      : "bg-amber-500/5 border-amber-500/20 text-amber-400";
  return (
    <div className={`border rounded-xl p-5 ${cls}`}>
      <p className="font-semibold text-sm mb-1">⚠ {title}</p>
      <p className="text-zinc-400 text-xs leading-relaxed">{desc}</p>
      {violations && violations.length > 0 && (
        <ul className="mt-3 space-y-1">
          {violations.map((v, i) => (
            <li key={i} className="text-zinc-500 text-xs">• {v}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── ErrorState ────────────────────────────────────────────────────────────────

function ErrorState({ message }: { message: string }) {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 gap-4">
      <p className="text-red-400 text-sm">{message}</p>
      <Link
        href="/dashboard"
        className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Back to Dashboard
      </Link>
    </main>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PracticeSessionPage({
  params,
}: {
  params: Promise<{ session_id: string }>;
}) {
  const { session_id } = use(params);
  const sessionId = session_id;

  const [status, setStatus] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await fetchSession(sessionId);
        setStatus(data.status);
        if (data.status === "ready_to_start") {
          clearInterval(intervalRef.current!);
          setSessionDetail(data);
        }
      } catch (err) {
        clearInterval(intervalRef.current!);
        setError(err instanceof ApiError ? err.detail : "Failed to load session.");
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [sessionId]);

  if (error) return <ErrorState message={error} />;
  if (status === "ready_to_start" && sessionDetail)
    return <AlignmentReport session={sessionDetail} />;
  return <ProcessingCanvas status={status} />;
}
