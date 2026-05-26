import Link from 'next/link';
import { SessionSummary } from '@/types/session';
import StatusBadge from './StatusBadge';

interface SessionGridProps {
  sessions: SessionSummary[];
}

export default function SessionGrid({ sessions }: SessionGridProps) {
  if (sessions.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No practice sessions yet. Start your first one above.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm text-left text-zinc-300">
        <thead className="text-xs text-zinc-500 uppercase bg-zinc-800/50">
          <tr>
            <th className="px-4 py-3">Target Role</th>
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
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
