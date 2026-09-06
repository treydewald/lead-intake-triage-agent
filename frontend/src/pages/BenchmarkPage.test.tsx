import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

    await waitFor(() => expect(screen.getByText('Run History & Trend')).toBeInTheDocument())
    const runHistoryTable = screen.getByRole('table', { name: 'Run history' })
    // header row + one row per run (2 runs)
    expect(within(runHistoryTable).getAllByRole('row')).toHaveLength(3)
    expect(within(runHistoryTable).getByText('Viewing')).toBeInTheDocument()

    await userEvent.click(screen.getByText(new Date(OLDER_RUN.created_at).toLocaleString()))

    await waitFor(() => expect(api.getBenchmarkRun).toHaveBeenLastCalledWith(OLDER_RUN.id))
  })

  function readCandidateCount(label: string): string {
    const container = screen.getByText(/Candidate threshold/).closest('div') as HTMLElement
    const labelNode = within(container).getByText(label)
    return labelNode.nextElementSibling?.textContent ?? ''
  }

  it('renders the collapsed Threshold Simulator and updates counts on slider change', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([RUN])
    vi.spyOn(api, 'getBenchmarkRun').mockResolvedValue(RUN)
    vi.spyOn(api, 'getConfidenceThreshold').mockResolvedValue({ confidence_threshold: 0.7 })

    render(<BenchmarkPage />)

    await waitFor(() => expect(screen.getByText('Threshold Simulator')).toBeInTheDocument())

    // RUN has one case at confidence 0.9 (correct) and one at 0.4 (incorrect). At the
    // live 0.7 threshold only the 0.9 case auto-processes.
    await waitFor(() => expect(screen.getByText('Live threshold (0.70)')).toBeInTheDocument())
    const slider = screen.getByLabelText('Candidate confidence threshold') as HTMLInputElement
    expect(slider.value).toBe('0.7')
    expect(readCandidateCount('Auto-processed')).toBe('1')
    expect(readCandidateCount('Wrong, auto-approved')).toBe('0')

    fireEvent.change(slider, { target: { value: '0' } })

    // At threshold 0.0 both cases (0.9 and 0.4) auto-process, including the wrong one.
    await waitFor(() => expect(readCandidateCount('Auto-processed')).toBe('2'))
    expect(readCandidateCount('Wrong, auto-approved')).toBe('1')
  })

  it('shows an error state when the run list fails to load', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockRejectedValue(new Error('network error'))

    render(<BenchmarkPage />)

    await waitFor(() =>
      expect(screen.getByText('Failed to load benchmark runs.')).toBeInTheDocument(),
    )
  })

  it('runs a new benchmark and displays its result on success', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([])
    vi.spyOn(api, 'runBenchmark').mockResolvedValue(RUN)

    render(<BenchmarkPage />)

    await waitFor(() => expect(screen.getByText(/No benchmark runs yet/)).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /Run Benchmark/ }))

    await waitFor(() => expect(screen.getAllByText('50.0%').length).toBeGreaterThan(0))
    expect(api.runBenchmark).toHaveBeenCalledTimes(1)
  })

  it('shows an error state when running a new benchmark fails', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([])
    vi.spyOn(api, 'runBenchmark').mockRejectedValue(new Error('server error'))

    render(<BenchmarkPage />)

    await waitFor(() => expect(screen.getByText(/No benchmark runs yet/)).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /Run Benchmark/ }))

    await waitFor(() => expect(screen.getByText('Benchmark run failed.')).toBeInTheDocument())
  })

  it('shows an error state when switching to a different run fails', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([RUN, OLDER_RUN])
    vi.spyOn(api, 'getBenchmarkRun').mockImplementation((runId: string) =>
      runId === OLDER_RUN.id ? Promise.reject(new Error('not found')) : Promise.resolve(RUN),
    )

    render(<BenchmarkPage />)

    await waitFor(() => expect(screen.getByText('Run History & Trend')).toBeInTheDocument())
    await userEvent.click(screen.getByText(new Date(OLDER_RUN.created_at).toLocaleString()))

    await waitFor(() =>
      expect(screen.getByText('Failed to load that benchmark run.')).toBeInTheDocument(),
    )
  })

  it('re-bases the Threshold Simulator on the newly-selected run after switching', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([RUN, OLDER_RUN])
    vi.spyOn(api, 'getBenchmarkRun').mockImplementation((runId: string) =>
      Promise.resolve(runId === OLDER_RUN.id ? OLDER_RUN : RUN),
    )
    vi.spyOn(api, 'getConfidenceThreshold').mockResolvedValue({ confidence_threshold: 0.7 })

    render(<BenchmarkPage />)

    // RUN has 2 cases; at the live 0.7 threshold, 1 auto-processes (confidence 0.9).
    await waitFor(() => expect(readCandidateCount('Auto-processed')).toBe('1'))

    await userEvent.click(screen.getByText(new Date(OLDER_RUN.created_at).toLocaleString()))

    // OLDER_RUN has zero cases - the simulator re-bases to reflect it, not RUN's stale counts.
    await waitFor(() => expect(readCandidateCount('Auto-processed')).toBe('0'))
  })
})
