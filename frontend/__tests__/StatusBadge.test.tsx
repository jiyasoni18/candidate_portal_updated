import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusBadge from '../components/StatusBadge';

describe('StatusBadge', () => {
  it('renders completed with emerald classes', () => {
    const { container } = render(<StatusBadge status="completed" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('bg-emerald-500/10');
    expect(badge.className).toContain('text-emerald-400');
  });

  it('renders ready_to_start with indigo classes', () => {
    const { container } = render(<StatusBadge status="ready_to_start" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('bg-indigo-500/10');
    expect(badge.className).toContain('text-indigo-400');
  });

  it('renders parsing with amber animate-pulse classes', () => {
    const { container } = render(<StatusBadge status="parsing" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('bg-amber-500/10');
    expect(badge.className).toContain('animate-pulse');
  });

  it('renders scoring with amber animate-pulse classes', () => {
    const { container } = render(<StatusBadge status="scoring" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('bg-amber-500/10');
    expect(badge.className).toContain('animate-pulse');
  });

  it('renders unknown status with zinc fallback classes', () => {
    const { container } = render(<StatusBadge status="unknown_status" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.className).toContain('bg-zinc-500/10');
    expect(badge.className).toContain('text-zinc-400');
  });
});
