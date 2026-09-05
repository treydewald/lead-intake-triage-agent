import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ReviewQueuePage } from './ReviewQueuePage'
import * as api from '../lib/api'

describe('ReviewQueuePage', () => {
  it('renders pending review items returned by the API', async () => {
    vi.spyOn(api, 'listReviews').mockResolvedValue([
      {
        id: 'item-1',
        run_id: 'run-abc12345',
        lead_id: 'lead-abc12345',
        draft_intent_label: 'buyer',
        confidence_score: 0.55,
        created_at: '2026-09-04T12:00:00Z',
        message_body: 'Looking for pricing.',
      },
    ])

    render(
      <MemoryRouter>
        <ReviewQueuePage />
      </MemoryRouter>,
    )

    const table = await screen.findByRole('table')
    expect(within(table).getByText('lead-abc')).toBeInTheDocument()
    expect(within(table).getByText('buyer')).toBeInTheDocument()
    expect(within(table).getByText('0.55')).toBeInTheDocument()
  })

  it('shows an empty state when there are no pending reviews', async () => {
    vi.spyOn(api, 'listReviews').mockResolvedValue([])

    render(
      <MemoryRouter>
        <ReviewQueuePage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('No leads awaiting review')).toBeInTheDocument())
  })
})
