"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchSession, refineWithGaps, generatePDF, ApiError } from "@/lib/api";
import type { SessionDetail } from "@/types/session";

// ── GapCard ───────────────────────────────────────────────────────────────────

function GapCard({
  index,
  gap,
  note,
  onChange,
}: {
  index: number;
  gap: string;
  note: string;
  onChange: (index: number, value: string) => void;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
      <div className="flex items-start gap-3 mb-4">
        <span className="text-amber-400 font-bold mt-0.5 shrink-0">!</span>
        <p className="text-zinc-200 text-sm leading-relaxed">{gap}</p>
      </div>
      
      <div className="mb-4 flex flex-wrap items-center gap-4 bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
        <span className="text-sm text-zinc-400">Do you have experience for this gap?</span>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
            <input 
              type="radio" 
              name={`gap-exp-${index}`} 
              className="accent-indigo-500"
              onChange={() => onChange(index, "")} 
              defaultChecked 
            />
            Yes, I'll write it
          </label>
          <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
            <input 
              type="radio" 
              name={`gap-exp-${index}`} 
              className="accent-indigo-500"
              onChange={() => {
                const skill = gap.split(':')[0] || 'this skill';
                onChange(index, `GENERATE_PROJECT: ${skill}`);
              }}
            />
            No, generate a basic project
          </label>
        </div>
      </div>

      <textarea
        value={note}
        onChange={(e) => onChange(index, e.target.value)}
        placeholder="Describe your experience, or let the AI generate a project if you selected 'No' above..."
        rows={3}
        className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
      />
    </div>
  );
}

// ── ImprovementsList ──────────────────────────────────────────────────────────

function ImprovementsList({
  improvements,
  selected,
  onToggle,
}: {
  improvements: string[];
  selected: Set<number>;
  onToggle: (index: number) => void;
}) {
  if (improvements.length === 0) return null;

  return (
    <div>
      <h2 className="text-zinc-100 font-semibold text-base mb-1">Terminology Improvements</h2>
      <p className="text-zinc-500 text-xs mb-4">
        Select the keyword and phrasing improvements to apply to your resume.
      </p>
      <div className="space-y-2">
        {improvements.map((item, i) => (
          <label
            key={i}
            className="flex items-start gap-3 bg-slate-800/50 border border-slate-700 rounded-xl p-4 cursor-pointer hover:border-indigo-500/50 transition-colors"
          >
            <input
              type="checkbox"
              checked={selected.has(i)}
              onChange={() => onToggle(i)}
              className="mt-0.5 accent-indigo-500 shrink-0 w-4 h-4"
            />
            <span className="text-zinc-300 text-sm leading-relaxed">{item}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

// ── CustomAdditionsField ──────────────────────────────────────────────────────

function CustomAdditionsField({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <h2 className="text-zinc-100 font-semibold text-base mb-1">Custom Additions</h2>
      <p className="text-zinc-500 text-xs mb-3">
        Add any extra content you want included in your resume.
      </p>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Add certifications, education, or other content..."
        rows={5}
        className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3 text-sm text-zinc-200 placeholder-zinc-600 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
      />
      <p className="text-zinc-600 text-xs mt-2 leading-relaxed">
        Tip: prefix lines with <code className="text-indigo-400">certificate:</code> or{" "}
        <code className="text-indigo-400">education:</code> to place them in the correct resume
        section (e.g., <code className="text-zinc-500">certificate: AWS Solutions Architect</code>).
      </p>
    </div>
  );
}

// ── TemplatePicker ────────────────────────────────────────────────────────────

const TEMPLATES = ["Classic ATS with black", "Classic ATS with blue", "Two Column with black", "Two Column with blue"] as const;
type Template = (typeof TEMPLATES)[number];

function TemplatePicker({
  selected,
  onSelect,
}: {
  selected: Template;
  onSelect: (t: Template) => void;
}) {
  return (
    <div>
      <h2 className="text-zinc-100 font-semibold text-base mb-1">PDF Template</h2>
      <p className="text-zinc-500 text-xs mb-3">Choose the visual style for your resume.</p>
      <div className="flex flex-wrap gap-2">
        {TEMPLATES.map((t) => (
          <button
            key={t}
            onClick={() => onSelect(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
              selected === t
                ? "bg-indigo-600 border-indigo-500 text-white"
                : "bg-slate-800 border-slate-700 text-zinc-400 hover:border-slate-500 hover:text-zinc-200"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── RefinedItemCard ───────────────────────────────────────────────────────────
// approved: null = default (treated as approved), true = explicitly approved, false = rejected

function RefinedItemCard({
  label,
  content,
  approved,
  onApprove,
  onReject,
}: {
  label: string;
  content: string;
  approved: boolean | null;
  onApprove: () => void;
  onReject: () => void;
}) {
  const isRejected = approved === false;
  const isApproved = approved === true || approved === null;

  return (
    <div
      className={`bg-slate-800/50 border rounded-xl p-5 transition-all ${
        isRejected
          ? "border-red-500/30 opacity-50"
          : "border-slate-700"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <p className="text-zinc-400 text-xs font-medium uppercase tracking-wide">{label}</p>
        {isRejected ? (
          <span className="text-xs font-semibold text-red-400 bg-red-500/10 border border-red-500/20 rounded-full px-2 py-0.5 shrink-0">
            Rejected
          </span>
        ) : (
          <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5 shrink-0">
            Approved
          </span>
        )}
      </div>
      <p className="text-zinc-200 text-sm leading-relaxed mb-4">{content}</p>
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
            isApproved
              ? "bg-emerald-600 border-emerald-500 text-white"
              : "bg-slate-700 border-slate-600 text-zinc-400 hover:border-emerald-500/50 hover:text-emerald-400"
          }`}
        >
          Approve
        </button>
        <button
          onClick={onReject}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
            isRejected
              ? "bg-red-600 border-red-500 text-white"
              : "bg-slate-700 border-slate-600 text-zinc-400 hover:border-red-500/50 hover:text-red-400"
          }`}
        >
          Reject
        </button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ResumeUpgradeWizardPage({
  params,
}: {
  params: Promise<{ session_id: string }>;
}) {
  const { session_id } = use(params);
  const router = useRouter();

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Step 1 state
  const [gapNotes, setGapNotes] = useState<Record<string, string>>({});
  const [selectedImprovements, setSelectedImprovements] = useState<Set<number>>(new Set());
  const [customAdditions, setCustomAdditions] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<Template>("Classic ATS with black");
  const [isRefining, setIsRefining] = useState(false);
  const [refineError, setRefineError] = useState<string | null>(null);

  // Step 2 state
  const [step, setStep] = useState<"input" | "review">("input");
  const [refinedGaps, setRefinedGaps] = useState<Record<string, string>>({});
  const [refinedCustomItems, setRefinedCustomItems] = useState<string[]>([]);
  // null = default (approved), true = explicitly approved, false = rejected
  const [approvedGaps, setApprovedGaps] = useState<Record<string, boolean | null>>({});
  const [approvedCustomItems, setApprovedCustomItems] = useState<Record<number, boolean | null>>({});
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Fetch session on mount
  useEffect(() => {
    fetchSession(session_id)
      .then((data) => {
        setSession(data);
        // Do not pre-select improvements by default
        setSelectedImprovements(new Set());
      })
      .catch((err) => {
        setLoadError(err instanceof ApiError ? err.detail : "Failed to load session.");
      });
  }, [session_id]);

  const handleGapNoteChange = (index: number, value: string) => {
    setGapNotes((prev) => ({ ...prev, [String(index)]: value }));
  };

  const handleToggleImprovement = (index: number) => {
    setSelectedImprovements((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  // Step 1 → Step 2: call /refine and transition to review
  const handleRefine = async () => {
    if (!session) return;
    setIsRefining(true);
    setRefineError(null);

    try {
      const improvements = session.enhanced_analysis?.improvements ?? [];
      const selectedImprovementStrings = improvements.filter((_, i) =>
        selectedImprovements.has(i)
      );

      const gapSelections: Record<string, string> = {};
      Object.entries(gapNotes).forEach(([key, val]) => {
        if (val.trim()) gapSelections[key] = val.trim();
      });

      const result = await refineWithGaps(
        session_id,
        customAdditions,
        gapSelections,
        selectedImprovementStrings
      );

      const gaps = result.refined_gaps ?? {};
      const customItems = result.refined_custom_items ?? [];

      setRefinedGaps(gaps);
      setRefinedCustomItems(customItems);
      // Default all items to null (approved)
      setApprovedGaps(Object.fromEntries(Object.keys(gaps).map((k) => [k, null])));
      setApprovedCustomItems(Object.fromEntries(customItems.map((_, i) => [i, null])));
      setStep("review");
    } catch (err) {
      setRefineError(
        err instanceof ApiError ? err.detail : "Failed to refine inputs. Please try again."
      );
    } finally {
      setIsRefining(false);
    }
  };

  // Step 2: persist only approved items via /refine (pre_refined=true), then generate PDF
  const handleGenerate = async () => {
    if (!session) return;
    setIsGenerating(true);
    setGenerateError(null);

    try {
      // Collect approved gap paragraphs (null = default approved, true = explicitly approved)
      const approvedGapSelections: Record<string, string> = {};
      Object.entries(refinedGaps).forEach(([key, content]) => {
        if (approvedGaps[key] !== false) {
          approvedGapSelections[key] = content;
        }
      });

      // Collect approved custom items
      const approvedCustomLines = refinedCustomItems.filter(
        (_, i) => approvedCustomItems[i] !== false
      );

      // Persist only approved content via /refine with pre_refined=true (skips LLM)
      await refineWithGaps(
        session_id,
        approvedCustomLines.join("\n"),
        approvedGapSelections,
        [],
        true
      );

      // Generate and download the PDF
      const blob = await generatePDF(session_id, selectedTemplate);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `improved-resume-${session_id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setGenerateError(
        err instanceof ApiError ? err.detail : "Failed to generate resume. Please try again."
      );
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Loading state ──────────────────────────────────────────────────────────
  if (!session && !loadError) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 gap-6">
        <div className="relative flex items-center justify-center">
          <span className="absolute inline-flex h-16 w-16 rounded-full bg-indigo-500/30 animate-ping" />
          <span className="relative inline-flex h-10 w-10 rounded-full bg-indigo-500" />
        </div>
        <p className="text-zinc-400 text-sm">Loading session...</p>
      </main>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (loadError) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 gap-4">
        <p className="text-red-400 text-sm">{loadError}</p>
        <Link
          href={`/practice/${session_id}`}
          className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Back to Report
        </Link>
      </main>
    );
  }

  const gaps = session!.enhanced_analysis?.gaps ?? [];
  const improvements = session!.enhanced_analysis?.improvements ?? [];

  // ── Step 2: Refinement Review ──────────────────────────────────────────────
  if (step === "review") {
    const gapEntries = Object.entries(refinedGaps);
    return (
      <main className="min-h-screen bg-slate-900 text-zinc-100">
        {/* Top nav */}
        <div className="border-b border-slate-800 px-6 py-3 flex items-center justify-between">
          <div>
            <span className="text-sm font-semibold text-zinc-100">Resume Upgrade Wizard</span>
            <p className="text-zinc-500 text-xs mt-0.5">
              Review each refined item and approve or reject before generating
            </p>
          </div>
          <button
            onClick={() => setStep("input")}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-zinc-400 border border-slate-700 transition-colors"
          >
            ← Back to Inputs
          </button>
        </div>

        <div className="max-w-3xl mx-auto px-6 py-8 space-y-10">
          {/* Refined gap paragraphs */}
          {gapEntries.length > 0 && (
            <div>
              <h2 className="text-zinc-100 font-semibold text-base mb-1">Refined Gap Responses</h2>
              <p className="text-zinc-500 text-xs mb-4">
                Review each AI-refined paragraph and approve or reject it.
              </p>
              <div className="space-y-4">
                {gapEntries.map(([key, content]) => {
                  const gapIndex = parseInt(key, 10);
                  const label = gaps[gapIndex] ?? `Gap ${gapIndex + 1}`;
                  return (
                    <RefinedItemCard
                      key={key}
                      label={label}
                      content={content}
                      approved={approvedGaps[key] ?? null}
                      onApprove={() =>
                        setApprovedGaps((prev) => ({ ...prev, [key]: true }))
                      }
                      onReject={() =>
                        setApprovedGaps((prev) => ({ ...prev, [key]: false }))
                      }
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* Refined custom addition items */}
          {refinedCustomItems.length > 0 && (
            <div>
              <h2 className="text-zinc-100 font-semibold text-base mb-1">
                Refined Custom Additions
              </h2>
              <p className="text-zinc-500 text-xs mb-4">
                Review each AI-refined custom addition and approve or reject it.
              </p>
              <div className="space-y-4">
                {refinedCustomItems.map((content, i) => (
                  <RefinedItemCard
                    key={i}
                    label={`Custom Addition ${i + 1}`}
                    content={content}
                    approved={approvedCustomItems[i] ?? null}
                    onApprove={() =>
                      setApprovedCustomItems((prev) => ({ ...prev, [i]: true }))
                    }
                    onReject={() =>
                      setApprovedCustomItems((prev) => ({ ...prev, [i]: false }))
                    }
                  />
                ))}
              </div>
            </div>
          )}

          {/* Template picker (still editable in review step) */}
          <TemplatePicker selected={selectedTemplate} onSelect={setSelectedTemplate} />

          {/* Generate button */}
          <div className="pb-8">
            {generateError && (
              <p className="text-red-400 text-sm mb-4 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                {generateError}
              </p>
            )}
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors text-sm"
            >
              {isGenerating ? "Generating..." : "Generate Upgraded Resume"}
            </button>
          </div>
        </div>
      </main>
    );
  }

  // ── Step 1: Input Collection ───────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-slate-900 text-zinc-100">
      {/* Top nav */}
      <div className="border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold text-zinc-100">Resume Upgrade Wizard</span>
          <p className="text-zinc-500 text-xs mt-0.5">
            Review gaps, select improvements, and generate your upgraded resume
          </p>
        </div>
        <button
          onClick={() => router.push(`/practice/${session_id}`)}
          className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-zinc-400 border border-slate-700 transition-colors"
        >
          ← Back to Report
        </button>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-10">



        {/* Gaps section */}
        <div>
          <h2 className="text-zinc-100 font-semibold text-base mb-1">Address Your Gaps</h2>
          <p className="text-zinc-500 text-xs mb-4">
            For each gap, describe relevant experience or projects you have that address it.
          </p>
          {gaps.length === 0 ? (
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-5 flex items-center gap-3">
              <span className="text-emerald-400 text-lg">✓</span>
              <p className="text-emerald-400 text-sm font-medium">No gaps detected</p>
            </div>
          ) : (
            <div className="space-y-4">
              {gaps.map((gap, i) => (
                <GapCard
                  key={i}
                  index={i}
                  gap={gap}
                  note={gapNotes[String(i)] ?? ""}
                  onChange={handleGapNoteChange}
                />
              ))}
            </div>
          )}
        </div>

        {/* Improvements section */}
        <ImprovementsList
          improvements={improvements}
          selected={selectedImprovements}
          onToggle={handleToggleImprovement}
        />

        {/* Custom additions */}
        <CustomAdditionsField value={customAdditions} onChange={setCustomAdditions} />

        {/* Template picker */}
        <TemplatePicker selected={selectedTemplate} onSelect={setSelectedTemplate} />

        {/* Refine button */}
        <div className="pb-8">
          {refineError && (
            <p className="text-red-400 text-sm mb-4 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
              {refineError}
            </p>
          )}
          <button
            onClick={handleRefine}
            disabled={isRefining}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors text-sm"
          >
            {isRefining ? "Refining..." : "Refine My Inputs"}
          </button>
        </div>
      </div>
    </main>
  );
}
