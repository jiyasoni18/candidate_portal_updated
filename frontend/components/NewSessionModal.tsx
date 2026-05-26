"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, UploadCloud, X } from "lucide-react";
import { initializeSession } from "@/lib/api";

interface NewSessionModalProps {
  open: boolean;
  onClose: () => void;
}

export default function NewSessionModal({ open, onClose }: NewSessionModalProps) {
  const router = useRouter();

  const [jobTitle, setJobTitle] = useState("");
  const [jdText, setJdText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset all state when modal closes
  useEffect(() => {
    if (!open) {
      setJobTitle("");
      setJdText("");
      setFile(null);
      setSubmitting(false);
      setFieldErrors({});
      setSubmitError(null);
      setDragOver(false);
    }
  }, [open]);

  // --- File handling ---
  function validateAndSetFile(selected: File) {
    if (!selected.name.toLowerCase().endsWith(".pdf")) {
      setFieldErrors((prev) => ({ ...prev, file: "Only PDF files are accepted." }));
      return;
    }
    setFieldErrors((prev) => { const next = { ...prev }; delete next.file; return next; });
    setFile(selected);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) validateAndSetFile(dropped);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (selected) validateAndSetFile(selected);
  }

  // --- Validation ---
  function validate(): boolean {
    const errors: Record<string, string> = {};
    if (!jobTitle.trim()) errors.jobTitle = "Job title is required.";
    if (!jdText.trim()) errors.jdText = "Job description is required.";
    if (!file) errors.file = "A PDF resume is required.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  // --- Submission ---
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      const formData = new FormData();
      formData.append("file", file!);
      formData.append("jd_text", jdText);

      const { session_id } = await initializeSession(formData);
      router.push(`/practice/${session_id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Submission failed. Please try again.";
      setSubmitError(message);
      setSubmitting(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-xl bg-slate-800 border border-zinc-700 shadow-2xl p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-zinc-100">New Practice Session</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-100 transition-colors"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {/* Job Title */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1" htmlFor="jobTitle">
              Job Title
            </label>
            <input
              id="jobTitle"
              type="text"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="e.g. Senior Software Engineer"
              className="w-full rounded-lg bg-slate-900 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {fieldErrors.jobTitle && (
              <p className="mt-1 text-xs text-red-400">{fieldErrors.jobTitle}</p>
            )}
          </div>

          {/* Job Description */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1" htmlFor="jdText">
              Job Description
            </label>
            <textarea
              id="jdText"
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              rows={4}
              placeholder="Paste the job description here..."
              className="w-full rounded-lg bg-slate-900 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
            {fieldErrors.jdText && (
              <p className="mt-1 text-xs text-red-400">{fieldErrors.jdText}</p>
            )}
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">
              Resume (PDF)
            </label>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 cursor-pointer transition-colors ${
                dragOver
                  ? "border-indigo-500 bg-indigo-500/10"
                  : "border-zinc-600 hover:border-zinc-500 bg-slate-900"
              }`}
            >
              <UploadCloud size={24} className="text-zinc-400" />
              {file ? (
                <p className="text-sm text-zinc-300">{file.name}</p>
              ) : (
                <p className="text-sm text-zinc-500">
                  Drag & drop a PDF or <span className="text-indigo-400 underline">browse</span>
                </p>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileInput}
              />
            </div>
            {fieldErrors.file && (
              <p className="mt-1 text-xs text-red-400">{fieldErrors.file}</p>
            )}
          </div>

          {/* Submit error */}
          {submitError && (
            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {submitError}
            </p>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg text-zinc-400 hover:text-zinc-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium transition-colors"
            >
              {submitting && <Loader2 size={16} className="animate-spin" />}
              {submitting ? "Submitting…" : "Start Session"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
