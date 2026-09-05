import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { LeadListPage } from './LeadListPage'
import * as api from '../lib/api'

describe('LeadListPage', () => {
  it('renders leads returned by the API', async () => {
    vi.spyOn(api, 'listLeads').mockResolvedValue({
      items: [
        {
          lead_id: 'lead-abc12345',
          run_id: 'run-1',
          status: 'auto_processed',
          source_channel: 'web_form',
          confidence_score: 0.92,
          created_at: '2026-09-04T12:00:00Z',
          updated_at: '2026-09-04T12:00:01Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    })

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('lead-abc').length).toBeGreaterThan(0))
    expect(screen.getAllByText('Auto-processed').length).toBeGreaterThan(0)
    expect(screen.getByText('web_form')).toBeInTheDocument()
  })

  it('shows an empty state when there are no leads', async () => {
    vi.spyOn(api, 'listLeads').mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText('No leads found')).toBeInTheDocument())
  })
})
