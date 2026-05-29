"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { fetchSessions } from "@/lib/api";
import type { SessionSummary } from "@/types/session";
import SessionGrid from "@/components/SessionGrid";
import NewSessionModal from "@/components/NewSessionModal";

export default function DashboardPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    fetchSessions()
      .then((data) => setSessions(data))
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to load sessions.";
        setError(message);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-zinc-100">Welcome back, Candidate</h1>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors"
        >
          <Plus size={16} />
          New Practice Session
        </button>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3" aria-label="Loading sessions">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-12 rounded-lg bg-zinc-800/60 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Session grid */}
      {!loading && !error && <SessionGrid sessions={sessions} />}

      {/* New session modal */}
      <NewSessionModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}
