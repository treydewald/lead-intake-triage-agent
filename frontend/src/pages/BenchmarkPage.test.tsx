import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BenchmarkPage } from './BenchmarkPage'
import * as api from '../lib/api'

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

describe('BenchmarkPage', () => {
  it('renders the latest run and lists its misclassified case', async () => {
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([RUN])
    vi.spyOn(api, 'getBenchmarkRun').mockResolvedValue(RUN)

    render(<BenchmarkPage />)

    await waitFor(() => expect(screen.getByText('50.0%')).toBeInTheDocument())
    expect(screen.getByText('100.0%')).toBeInTheDocument()
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
})
