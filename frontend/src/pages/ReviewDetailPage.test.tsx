import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
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

  it('shows a not-found state for a missing run id', async () => {
    vi.spyOn(api, 'getReview').mockRejectedValue({ response: { status: 404 } })

    renderDetail()

    await waitFor(() => expect(screen.getByText(/No review item found/)).toBeInTheDocument())
  })
})
