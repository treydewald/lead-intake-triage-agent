import { act, render, screen } from '@testing-library/react'
import { createMemoryRouter, MemoryRouter, Route, RouterProvider, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LeadDetailPage } from './LeadDetailPage'
import * as api from '../lib/api'

afterEach(() => {
  vi.restoreAllMocks()
})

const BASE_LEAD = {
  lead_id: 'lead-abc12345',
  run_id: 'run-abc12345',
  source_channel: 'webform',
  confidence_score: 0.91,
  created_at: '2026-09-04T12:00:00Z',
  updated_at: '2026-09-04T12:00:05Z',
  failed_stage: null,
  error: null,
}

function renderDetail(leadId = 'lead-abc12345') {
  return render(
    <MemoryRouter initialEntries={[`/leads/${leadId}`]}>
      <Routes>
        <Route path="/leads/:leadId" element={<LeadDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LeadDetailPage', () => {
  it('renders the full stage-trace timeline with a completed decision and an unrun stage', async () => {
    vi.spyOn(api, 'getLeadDetail').mockResolvedValue({
      ...BASE_LEAD,
      status: 'auto_processed',
      stages: [
        {
          stage_key: 'intake_parsing',
          stage_label: 'Intake Parsing',
          status: 'COMPLETED',
          decision: { normalized: true },
          error: null,
          created_at: '2026-09-04T12:00:01Z',
        },
      ],
    })
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({ lead_id: 'lead-abc12345', entries: [] })

    renderDetail()

    expect(await screen.findByText('Intake Parsing')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
    // The other 5 stages in STAGE_ORDER have no matching entry in `stages`, so they all
    // render as NOT_YET_RUN — expect all 5, not a single unique match.
    expect(screen.getAllByText('Not yet run')).toHaveLength(5)
    expect(screen.getByText('auto processed')).toBeInTheDocument()
    expect(screen.getByText('No activity recorded yet.')).toBeInTheDocument()
  })

  it('shows the failed-pipeline banner with the failed stage and error message', async () => {
    vi.spyOn(api, 'getLeadDetail').mockResolvedValue({
      ...BASE_LEAD,
      status: 'failed',
      failed_stage: 'hubspot_crm_write',
      error: 'HubSpot API returned 500',
      stages: [],
    })
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({ lead_id: 'lead-abc12345', entries: [] })

    renderDetail()

    expect(await screen.findByText(/Pipeline failed at HubSpot CRM Write/)).toBeInTheDocument()
    expect(screen.getByText('HubSpot API returned 500')).toBeInTheDocument()
  })

  it('shows the in-progress banner for a mid-pipeline lead', async () => {
    vi.spyOn(api, 'getLeadDetail').mockResolvedValue({
      ...BASE_LEAD,
      status: 'in_progress',
      stages: [],
    })
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({ lead_id: 'lead-abc12345', entries: [] })

    renderDetail()

    expect(
      await screen.findByText('This lead is still mid-pipeline — later stages have not run yet.'),
    ).toBeInTheDocument()
  })

  it('shows a not-found state for a missing lead id', async () => {
    vi.spyOn(api, 'getLeadDetail').mockRejectedValue({ response: { status: 404 } })
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({ lead_id: 'missing-lead', entries: [] })

    renderDetail('missing-lead')

    expect(await screen.findByText(/No lead found with id "missing-lead"/)).toBeInTheDocument()
  })

  it('shows an error state on an unexpected failure', async () => {
    vi.spyOn(api, 'getLeadDetail').mockRejectedValue({ response: { status: 500 } })
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({ lead_id: 'lead-abc12345', entries: [] })

    renderDetail()

    expect(await screen.findByText('Failed to load lead detail.')).toBeInTheDocument()
  })

  it('shows recent activity and links to the full history page', async () => {
    vi.spyOn(api, 'getLeadDetail').mockResolvedValue({
      ...BASE_LEAD,
      status: 'auto_processed',
      stages: [],
    })
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({
      lead_id: 'lead-abc12345',
      entries: [
        {
          kind: 'stage',
          run_id: 'run-abc12345',
          created_at: '2026-09-04T12:00:01Z',
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

    // "Intake Parsing" renders twice: once as a NOT_YET_RUN stage card (stages: []
    // above), once as this timeline row's heading — its raw uppercase status text is
    // unique to the timeline row, since the stage-card panel renders a humanized label
    // ("Not yet run") instead.
    await screen.findByText('COMPLETED')
    expect(screen.getAllByRole('heading', { name: 'Intake Parsing', level: 3 })).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'View full history' })).toHaveAttribute(
      'href',
      '/leads/lead-abc12345/history',
    )
  })

  it('resets loading and re-fetches when navigating to a different lead id', async () => {
    vi.spyOn(api, 'getLeadDetail')
      .mockResolvedValueOnce({ ...BASE_LEAD, lead_id: 'lead-one', status: 'auto_processed', stages: [] })
      .mockResolvedValueOnce({ ...BASE_LEAD, lead_id: 'lead-two', status: 'auto_processed', stages: [] })
    vi.spyOn(api, 'getLeadHistory').mockResolvedValue({ lead_id: 'lead-one', entries: [] })

    const router = createMemoryRouter(
      [{ path: '/leads/:leadId', element: <LeadDetailPage /> }],
      { initialEntries: ['/leads/lead-one'] },
    )
    render(<RouterProvider router={router} />)

    expect(await screen.findByText('Lead lead-one')).toBeInTheDocument()

    await act(async () => {
      router.navigate('/leads/lead-two')
    })

    expect(await screen.findByText('Lead lead-two')).toBeInTheDocument()
    expect(api.getLeadDetail).toHaveBeenCalledWith('lead-two')
  })
})
