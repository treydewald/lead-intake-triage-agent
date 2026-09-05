import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReviewDetailPage } from './ReviewDetailPage'
import * as api from '../lib/api'

afterEach(() => {
  vi.restoreAllMocks()
})

const ITEM = {
  id: 'item-1',
  run_id: 'run-abc12345',
  lead_id: 'lead-abc12345',
  draft_intent_label: 'buyer',
  confidence_score: 0.55,
  created_at: '2026-09-04T12:00:00Z',
  message_body: 'Interested in a quote for 20 units.',
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/reviews/run-abc12345']}>
      <Routes>
        <Route path="/reviews/:runId" element={<ReviewDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ReviewDetailPage', () => {
  it('renders the draft classification and submits an approve action', async () => {
    vi.spyOn(api, 'getReview').mockResolvedValue(ITEM)
    vi.spyOn(api, 'actionReview').mockResolvedValue({
      id: 'run-abc12345',
      lead_id: 'lead-abc12345',
      status: 'COMPLETED',
      created_at: '2026-09-04T12:00:00Z',
      updated_at: '2026-09-04T12:00:05Z',
      stage_traces: [],
    })

    renderDetail()

    await waitFor(() => expect(screen.getByText('buyer')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Submit' }))

    await waitFor(() => expect(screen.getByText(/Run status is now/)).toBeInTheDocument())
    expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    expect(api.actionReview).toHaveBeenCalledWith('run-abc12345', {
      action: 'approve',
      corrected_intent_label: undefined,
      reviewer_name: undefined,
    })
  })

  it('submits the optional reviewer name when supplied', async () => {
    vi.spyOn(api, 'getReview').mockResolvedValue(ITEM)
    vi.spyOn(api, 'actionReview').mockResolvedValue({
      id: 'run-abc12345',
      lead_id: 'lead-abc12345',
      status: 'COMPLETED',
      created_at: '2026-09-04T12:00:00Z',
      updated_at: '2026-09-04T12:00:05Z',
      stage_traces: [],
    })

    renderDetail()

    await waitFor(() => expect(screen.getByText('buyer')).toBeInTheDocument())

    await userEvent.type(screen.getByPlaceholderText('Your name (optional)'), 'Jordan')
    await userEvent.click(screen.getByRole('button', { name: 'Submit' }))

    await waitFor(() => expect(screen.getByText(/Run status is now/)).toBeInTheDocument())
    expect(api.actionReview).toHaveBeenCalledWith('run-abc12345', {
      action: 'approve',
      corrected_intent_label: undefined,
      reviewer_name: 'Jordan',
    })
  })

  it('blocks an edit submission with no corrected label', async () => {
    vi.spyOn(api, 'getReview').mockResolvedValue(ITEM)
    const actionSpy = vi.spyOn(api, 'actionReview')

    renderDetail()

    await waitFor(() => expect(screen.getByText('buyer')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('radio', { name: 'Edit' }))
    await userEvent.click(screen.getByRole('button', { name: 'Submit' }))

    expect(screen.getByText(/Enter a corrected classification/)).toBeInTheDocument()
    expect(actionSpy).not.toHaveBeenCalled()
  })

  it('shows an already-actioned message on a 409 response', async () => {
    vi.spyOn(api, 'getReview').mockResolvedValue(ITEM)
    vi.spyOn(api, 'actionReview').mockRejectedValue({ response: { status: 409 } })

    renderDetail()

    await waitFor(() => expect(screen.getByText('buyer')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Submit' }))

    await waitFor(() =>
      expect(screen.getByText(/already been actioned by someone else/)).toBeInTheDocument(),
    )
  })

  it('shows the lead message body and links to the full lead detail view', async () => {
    vi.spyOn(api, 'getReview').mockResolvedValue(ITEM)

    renderDetail()

    await waitFor(() =>
      expect(screen.getByText('Interested in a quote for 20 units.')).toBeInTheDocument(),
    )
    expect(screen.getByRole('link', { name: 'lead-abc' })).toHaveAttribute('href', '/leads/lead-abc12345')
  })

  it('shows a not-found state for a missing run id', async () => {
    vi.spyOn(api, 'getReview').mockRejectedValue({ response: { status: 404 } })

    renderDetail()

    await waitFor(() => expect(screen.getByText(/No review item found/)).toBeInTheDocument())
  })

  it('resets loading and re-fetches when navigating to a different run id', async () => {
    vi.spyOn(api, 'getReview')
      .mockResolvedValueOnce({ ...ITEM, run_id: 'run-one', draft_intent_label: 'buyer' })
      .mockResolvedValueOnce({ ...ITEM, run_id: 'run-two', draft_intent_label: 'seller' })

    const router = createMemoryRouter(
      [{ path: '/reviews/:runId', element: <ReviewDetailPage /> }],
      { initialEntries: ['/reviews/run-one'] },
    )
    render(<RouterProvider router={router} />)

    expect(await screen.findByText('buyer')).toBeInTheDocument()

    await act(async () => {
      router.navigate('/reviews/run-two')
    })

    expect(await screen.findByText('seller')).toBeInTheDocument()
    expect(api.getReview).toHaveBeenCalledWith('run-two')
  })

  it('shows recent activity for the lead and links to its full history', async () => {
    vi.spyOn(api, 'getReview').mockResolvedValue(ITEM)
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({
      lead_id: 'lead-abc12345',
      entries: [
        {
          kind: 'stage',
          run_id: 'run-abc12345',
          created_at: '2026-09-04T11:00:00Z',
          stage_key: 'intake_parsing',
          stage_label: 'Intake Parsing',
          status: 'COMPLETED',
          error: null,
          reviewer_action: null,
          corrected_intent_label: null,
          reviewer_name: null,
        },
      ],
    })

    renderDetail()

    await waitFor(() => expect(screen.getByText('Recent activity')).toBeInTheDocument())
    expect(screen.getByText('Intake Parsing')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View full history' })).toHaveAttribute(
      'href',
      '/leads/lead-abc12345/history',
    )
  })
})
