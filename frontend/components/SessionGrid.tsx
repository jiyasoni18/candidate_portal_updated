"use client";

import Link from 'next/link';
import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { SessionSummary } from '@/types/session';
import StatusBadge from './StatusBadge';
import { downloadResume, deleteSession } from '@/lib/api';

interface SessionGridProps {
  sessions: SessionSummary[];
}

export default function SessionGrid({ sessions: initialSessions }: SessionGridProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>(initialSessions);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  async function handleDelete(sessionId: string) {
    setDeletingId(sessionId);
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } catch {
      alert('Failed to delete session. Please try again.');
    } finally {
      setDeletingId(null);
      setConfirmId(null);
    }
  }

  if (sessions.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No practice sessions yet. Start your first one above.
      </div>
    );
  }

  return (
    <>
      {/* Confirm Delete Dialog */}
      {confirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-800 border border-zinc-700 rounded-xl shadow-2xl p-6 w-full max-w-sm mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
                <Trash2 size={18} className="text-red-400" />
              </div>
              <div>
                <h3 className="text-zinc-100 font-semibold text-sm">Delete Session?</h3>
                <p className="text-zinc-400 text-xs mt-0.5">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-zinc-400 text-sm mb-5">
              This will permanently delete the session, resume file, and all analysis data associated with it.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmId(null)}
                className="px-4 py-2 text-sm font-medium rounded-lg text-zinc-300 bg-slate-700 hover:bg-slate-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(confirmId)}
                disabled={deletingId === confirmId}
                className="px-4 py-2 text-sm font-medium rounded-lg text-white bg-red-600 hover:bg-red-500 disabled:opacity-60 transition-colors"
              >
                {deletingId === confirmId ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full text-sm text-left text-zinc-300">
          <thead className="text-xs text-zinc-500 uppercase bg-zinc-800/50">
            <tr>
              <th className="px-4 py-3">Target Role</th>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {sessions.map((session) => {
              const isReady = session.status === 'ready_to_start';
              const isCompleted = session.status === 'completed';
              return (
                <tr key={session.session_id} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 font-medium text-zinc-100">{session.job.title}</td>
                  <td className="px-4 py-3 text-zinc-400">{session.job.company_name || '—'}</td>
                  <td className="px-4 py-3 text-zinc-400">
                    {new Date(session.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={session.status} />
                  </td>
                  <td className="px-4 py-3 text-zinc-400">
                    {session.resume_score !== null ? session.resume_score : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {isReady && (
                        <Link
                          href={`/practice/${session.session_id}`}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors whitespace-nowrap"
                        >
                          Start Interview
                        </Link>
                      )}
                      {isCompleted && (
                        <Link
                          href={`/practice/${session.session_id}/assessment`}
                          className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-zinc-300 text-xs font-medium rounded-lg transition-colors whitespace-nowrap"
                        >
                          View Results
                        </Link>
                      )}
                      {session.resume_score !== null && (
                        <Link
                          href={`/practice/${session.session_id}`}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-zinc-400 hover:text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition-colors whitespace-nowrap"
                        >
                          Resume Report
                        </Link>
                      )}
                      <button
                        onClick={async () => {
                          try {
                            await downloadResume(session.session_id);
                          } catch {
                            alert('Could not load resume.');
                          }
                        }}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-zinc-400 hover:text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition-colors whitespace-nowrap"
                      >
                        View Resume
                      </button>
                      {/* Delete button */}
                      <button
                        onClick={() => setConfirmId(session.session_id)}
                        title="Delete session"
                        className="p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
