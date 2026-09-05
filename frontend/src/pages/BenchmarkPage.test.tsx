import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { BenchmarkPage } from './BenchmarkPage'
import * as api from '../lib/api'

afterEach(() => {
  vi.restoreAllMocks()
})

const RUN = {
  id: 'run-1',
  created_at: '2026-09-04T12:00:00Z',
  model_used: 'llama3.2:3b',
  repeats: 3,
  total_cases: 2,
  accuracy: 0.5,
  consistency: 1,
  cases: [
    {
      case_id: 'buyer-001',
      category: 'buyer',
      expected_label: 'buyer',
      is_ambiguous: false,
      predicted_label: 'buyer',
      confidence: 0.9,
      correct: true,
      consistent: true,
    },
    {
      case_id: 'spam-001',
      category: 'spam',
      expected_label: 'spam',
      is_ambiguous: false,
      predicted_label: 'browser',
      confidence: 0.4,
      correct: false,
      consistent: true,
    },
  ],
}

const OLDER_RUN = {
  id: 'run-0',
  created_at: '2026-09-01T12:00:00Z',
  model_used: 'llama3.2:3b',
  repeats: 3,
  total_cases: 2,
  accuracy: 1,
  consistency: 1,
  cases: [],
}

describe('BenchmarkPage', () => {
  it('renders the latest run and lists its misclassified case', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([RUN])
    vi.spyOn(api, 'getBenchmarkRun').mockResolvedValue(RUN)

    render(<BenchmarkPage />)

    await waitFor(() => expect(screen.getAllByText('50.0%').length).toBeGreaterThan(0))
    expect(screen.getByText('spam-001')).toBeInTheDocument()
    expect(screen.getByText('Misclassified')).toBeInTheDocument()
    expect(screen.queryByText('buyer-001')).not.toBeInTheDocument()
  })

  it('shows an empty state when there are no runs yet', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([])

    render(<BenchmarkPage />)

    await waitFor(() =>
      expect(screen.getByText(/No benchmark runs yet/)).toBeInTheDocument(),
    )
  })

  it('lists prior runs in Run History and switches the displayed run on click', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([RUN, OLDER_RUN])
    vi.spyOn(api, 'getBenchmarkRun').mockImplementation((runId: string) =>
      Promise.resolve(runId === OLDER_RUN.id ? OLDER_RUN : RUN),
    )

    render(<BenchmarkPage />)

    await waitFor(() => expect(screen.getByText('Run History')).toBeInTheDocument())
    const runHistoryTable = screen.getByRole('table', { name: 'Run history' })
    // header row + one row per run (2 runs)
    expect(within(runHistoryTable).getAllByRole('row')).toHaveLength(3)
    expect(within(runHistoryTable).getByText('Viewing')).toBeInTheDocument()

    await userEvent.click(screen.getByText(new Date(OLDER_RUN.created_at).toLocaleString()))

    await waitFor(() => expect(api.getBenchmarkRun).toHaveBeenLastCalledWith(OLDER_RUN.id))
  })
})
