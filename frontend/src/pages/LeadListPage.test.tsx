import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LeadListPage } from './LeadListPage'
import * as api from '../lib/api'

afterEach(() => {
  vi.restoreAllMocks()
})

const ONE_LEAD_RESPONSE = {
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
}

describe('LeadListPage', () => {
  it('renders leads returned by the API', async () => {
    vi.spyOn(api, 'listLeads').mockResolvedValue(ONE_LEAD_RESPONSE)

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

  it('shows an error state when the lead fetch fails', async () => {
    vi.spyOn(api, 'listLeads').mockRejectedValue(new Error('network error'))

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Failed to load leads.')).toBeInTheDocument()
  })

  it('shows dashes for the summary counts when they fail to load', async () => {
    vi.spyOn(api, 'listLeads').mockImplementation(async (params) => {
      if (params?.status === 'awaiting_review' || params?.status === 'auto_processed') {
        throw new Error('count failed')
      }
      return ONE_LEAD_RESPONSE
    })

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('—')).toHaveLength(2))
  })

  it('refetches with the selected status filter and resets to page 1', async () => {
    const user = userEvent.setup()
    const listSpy = vi.spyOn(api, 'listLeads').mockResolvedValue(ONE_LEAD_RESPONSE)

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getAllByText('lead-abc').length).toBeGreaterThan(0))
    listSpy.mockClear()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter by status' }), 'Awaiting review')

    await waitFor(() =>
      expect(listSpy).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'awaiting_review', page: 1 }),
      ),
    )
  })

  it('refetches with the selected channel filter', async () => {
    const user = userEvent.setup()
    const listSpy = vi.spyOn(api, 'listLeads').mockResolvedValue(ONE_LEAD_RESPONSE)

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getAllByText('lead-abc').length).toBeGreaterThan(0))
    listSpy.mockClear()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter by channel' }), 'Email')

    await waitFor(() =>
      expect(listSpy).toHaveBeenCalledWith(expect.objectContaining({ source_channel: 'email' })),
    )
  })

  it('refetches with the selected sort order', async () => {
    const user = userEvent.setup()
    const listSpy = vi.spyOn(api, 'listLeads').mockResolvedValue(ONE_LEAD_RESPONSE)

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getAllByText('lead-abc').length).toBeGreaterThan(0))
    listSpy.mockClear()

    await user.selectOptions(screen.getByRole('combobox', { name: 'Sort by' }), 'Confidence: high to low')

    await waitFor(() =>
      expect(listSpy).toHaveBeenCalledWith(expect.objectContaining({ sort: 'confidence_desc' })),
    )
  })

  it('paginates forward and back, disabling Previous on the first page', async () => {
    const user = userEvent.setup()
    const listSpy = vi.spyOn(api, 'listLeads').mockResolvedValue({ ...ONE_LEAD_RESPONSE, total: 25 })

    render(
      <MemoryRouter>
        <LeadListPage />
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getAllByText('lead-abc').length).toBeGreaterThan(0))

    expect(screen.getByText('Page 1 of 3 (25 total)')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Next' }))

    await waitFor(() => expect(screen.getByText('Page 2 of 3 (25 total)')).toBeInTheDocument())
    expect(listSpy).toHaveBeenCalledWith(expect.objectContaining({ page: 2 }))
    expect(screen.getByRole('button', { name: 'Previous' })).not.toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Previous' }))

    await waitFor(() => expect(screen.getByText('Page 1 of 3 (25 total)')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
  })
})
