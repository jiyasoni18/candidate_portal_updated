interface StatusBadgeProps {
  status: 'completed' | 'ready_to_start' | 'parsing' | 'scoring' | string;
}

const STATUS_CLASSES: Record<string, string> = {
  completed: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  ready_to_start: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20',
  parsing: 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse',
  scoring: 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse',
};

const FALLBACK_CLASSES = 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20';

function toLabel(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const classes = STATUS_CLASSES[status] ?? FALLBACK_CLASSES;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>
      {toLabel(status)}
    </span>
  );
}
