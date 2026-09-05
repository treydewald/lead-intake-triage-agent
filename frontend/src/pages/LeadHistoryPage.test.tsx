import { act, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LeadHistoryPage } from './LeadHistoryPage'
import * as api from '../lib/api'

afterEach(() => {
  vi.restoreAllMocks()
})

function renderHistory() {
  return render(
    <MemoryRouter initialEntries={['/leads/lead-abc12345/history']}>
      <Routes>
        <Route path="/leads/:leadId/history" element={<LeadHistoryPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LeadHistoryPage', () => {
  it('renders stage and review-action entries in order', async () => {
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({
      lead_id: 'lead-abc12345',
      entries: [
        {
          kind: 'stage',
          run_id: 'run-1',
          created_at: '2026-09-04T12:00:00Z',
          stage_key: 'intake_parsing',
          stage_label: 'Intake Parsing',
          status: 'COMPLETED',
          error: null,
          reviewer_action: null,
          corrected_intent_label: null,
          reviewer_name: null,
        },
        {
          kind: 'review_action',
          run_id: 'run-1',
          created_at: '2026-09-04T12:05:00Z',
          stage_key: null,
          stage_label: null,
          status: null,
          error: null,
          reviewer_action: 'approve',
          corrected_intent_label: null,
          reviewer_name: 'Jordan',
        },
      ],
    })

    renderHistory()

    await waitFor(() => expect(screen.getByText('Intake Parsing')).toBeInTheDocument())
    expect(screen.getByText('Approved')).toBeInTheDocument()
    expect(screen.getByText(/by Jordan/)).toBeInTheDocument()
  })

  it('falls back to "Reviewer" when no reviewer name was supplied', async () => {
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({
      lead_id: 'lead-abc12345',
      entries: [
        {
          kind: 'review_action',
          run_id: 'run-1',
          created_at: '2026-09-04T12:05:00Z',
          stage_key: null,
          stage_label: null,
          status: null,
          error: null,
          reviewer_action: 'reject',
          corrected_intent_label: null,
          reviewer_name: null,
        },
      ],
    })

    renderHistory()

    await waitFor(() => expect(screen.getByText('Rejected')).toBeInTheDocument())
    expect(screen.getByText(/by Reviewer/)).toBeInTheDocument()
  })

  it('shows a not-found state for a missing lead id', async () => {
    vi.spyOn(api, 'getLeadHistory').mockRejectedValue({ response: { status: 404 } })

    renderHistory()

    await waitFor(() => expect(screen.getByText(/No lead found/)).toBeInTheDocument())
  })

  it('resets loading and re-fetches when navigating to a different lead id', async () => {
    vi.spyOn(api, 'getLeadHistory')
      .mockResolvedValueOnce({ lead_id: 'lead-one', entries: [] })
      .mockResolvedValueOnce({ lead_id: 'lead-two', entries: [] })

    const router = createMemoryRouter(
      [{ path: '/leads/:leadId/history', element: <LeadHistoryPage /> }],
      { initialEntries: ['/leads/lead-one/history'] },
    )
    render(<RouterProvider router={router} />)

    expect(await screen.findByText(/Full history — lead-one/)).toBeInTheDocument()

    await act(async () => {
      router.navigate('/leads/lead-two/history')
    })

    expect(await screen.findByText(/Full history — lead-two/)).toBeInTheDocument()
    expect(api.getLeadHistory).toHaveBeenCalledWith('lead-two')
  })
})
