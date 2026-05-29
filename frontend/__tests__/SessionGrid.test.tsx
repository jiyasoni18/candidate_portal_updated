import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SessionGrid from '../components/SessionGrid';
import { SessionSummary } from '../types/session';

const mockSessions: SessionSummary[] = [
  {
    session_id: 'abc-1',
    status: 'completed',
    created_at: '2024-01-15T10:30:00Z',
    job: { id: 'job-1', title: 'Senior Software Engineer' },
    resume_score: 82,
  },
  {
    session_id: 'abc-2',
    status: 'ready_to_start',
    created_at: '2024-02-20T09:00:00Z',
    job: { id: 'job-2', title: 'Product Manager' },
    resume_score: null,
  },
];

describe('SessionGrid', () => {
  it('renders empty-state message when sessions array is empty', () => {
    render(<SessionGrid sessions={[]} />);
    expect(screen.getByText(/no practice sessions yet/i)).toBeInTheDocument();
  });

  it('renders correct number of rows for mock data', () => {
    render(<SessionGrid sessions={mockSessions} />);
    expect(screen.getByText('Senior Software Engineer')).toBeInTheDocument();
    expect(screen.getByText('Product Manager')).toBeInTheDocument();
    // 2 data rows
    const rows = screen.getAllByRole('row');
    // 1 header row + 2 data rows
    expect(rows).toHaveLength(3);
  });

  it('displays — for null score', () => {
    render(<SessionGrid sessions={mockSessions} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
