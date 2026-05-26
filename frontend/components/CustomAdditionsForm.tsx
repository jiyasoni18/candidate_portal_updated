"use client";

import { useState } from "react";

interface CustomAdditionsFormProps {
  sessionId: string;
  initialAdditions?: string;
  onSubmit: (additions: string) => Promise<void>;
}

export default function CustomAdditionsForm({
  sessionId,
  initialAdditions = "",
  onSubmit,
}: CustomAdditionsFormProps) {
  const [certificates, setCertificates] = useState(initialAdditions.includes("[CERTIFICATES]")
    ? extractSection(initialAdditions, "[CERTIFICATES]", "[EDUCATION]")
    : "");
  const [education, setEducation] = useState(initialAdditions.includes("[EDUCATION]")
    ? extractSection(initialAdditions, "[EDUCATION]", "[ADDITIONAL]")
    : "");
  const [additional, setAdditional] = useState(initialAdditions.includes("[ADDITIONAL]")
    ? extractSection(initialAdditions, "[ADDITIONAL]", null)
    : "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function extractSection(text: string, startMarker: string, endMarker: string | null): string {
    const startIndex = text.indexOf(startMarker);
    if (startIndex === -1) return "";
    
    let contentStart = startIndex + startMarker.length;
    let contentEnd = text.length;
    
    if (endMarker) {
      const endIndex = text.indexOf(endMarker, contentStart);
      if (endIndex !== -1) {
        contentEnd = endIndex;
      }
    }
    
    return text.substring(contentStart, contentEnd).trim();
  }

  function buildAdditionsText(): string {
    const parts: string[] = [];
    
    if (certificates.trim()) {
      parts.push("[CERTIFICATES]");
      parts.push(certificates.trim());
    }
    
    if (education.trim()) {
      parts.push("[EDUCATION]");
      parts.push(education.trim());
    }
    
    if (additional.trim()) {
      parts.push("[ADDITIONAL]");
      parts.push(additional.trim());
    }
    
    return parts.join("\n\n");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    
    try {
      const additionsText = buildAdditionsText();
      await onSubmit(additionsText);
    } catch (err) {
      setError("Failed to submit custom additions. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <h3 className="text-zinc-100 font-semibold mb-4">Custom Additions</h3>
      <p className="text-zinc-500 text-xs mb-4">
        Add any additional information to include in your improved resume. Use the sections below to categorize your additions.
      </p>
      
      <div className="space-y-4">
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
          <label className="block text-zinc-300 text-sm font-medium mb-2">
            Certificates
          </label>
          <textarea
            value={certificates}
            onChange={(e) => setCertificates(e.target.value)}
            placeholder="e.g., AWS Certified Solutions Architect, PMP"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-zinc-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all min-h-[80px]"
          />
        </div>
        
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
          <label className="block text-zinc-300 text-sm font-medium mb-2">
            Education
          </label>
          <textarea
            value={education}
            onChange={(e) => setEducation(e.target.value)}
            placeholder="e.g., Master of Science in Computer Science, Stanford University"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-zinc-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all min-h-[80px]"
          />
        </div>
        
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
          <label className="block text-zinc-300 text-sm font-medium mb-2">
            Additional
          </label>
          <textarea
            value={additional}
            onChange={(e) => setAdditional(e.target.value)}
            placeholder="e.g., Open source contributions, speaking engagements, publications"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-zinc-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all min-h-[80px]"
          />
        </div>
      </div>
      
      {error && (
        <p className="text-red-400 text-xs mt-3">
          {error}
        </p>
      )}
      
      <div className="mt-4 flex justify-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {isSubmitting ? "Saving..." : "Save Custom Additions"}
        </button>
      </div>
    </form>
  );
}
