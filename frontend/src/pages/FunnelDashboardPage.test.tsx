import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FunnelDashboardPage } from './FunnelDashboardPage'
import * as api from '../lib/api'

afterEach(() => {
  vi.restoreAllMocks()
})

const FULL_DASHBOARD = {
  total_leads: 5,
  by_status: [
    { status: 'auto_processed', count: 4 },
    { status: 'awaiting_review', count: 1 },
  ],
  by_source_channel: [
    { source_channel: 'web_form', count: 3, avg_confidence: 0.82 },
    { source_channel: 'email', count: 2, avg_confidence: 0.45 },
  ],
  avg_resolution_seconds: 125,
  reviewer_throughput: [{ reviewer_name: 'Alice', actioned_count: 2, avg_resolution_seconds: 90 }],
}

describe('FunnelDashboardPage', () => {
  it('renders stat tiles and both tables from a full response', async () => {
    vi.spyOn(api, 'getFunnelDashboard').mockResolvedValue(FULL_DASHBOARD)

    render(<FunnelDashboardPage />)

    await waitFor(() => expect(screen.getByText('5')).toBeInTheDocument())
    expect(screen.getByText('1')).toBeInTheDocument() // awaiting review stat
    expect(screen.getByText('2m 5s')).toBeInTheDocument() // avg resolution

    expect(screen.getByText('web form')).toBeInTheDocument()
    expect(screen.getByText('email')).toBeInTheDocument()

    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('1m 30s')).toBeInTheDocument()
  })

  it('renders the page-level empty state when there are zero leads', async () => {
    vi.spyOn(api, 'getFunnelDashboard').mockResolvedValue({
      total_leads: 0,
      by_status: [],
      by_source_channel: [],
      avg_resolution_seconds: null,
      reviewer_throughput: [],
    })

    render(<FunnelDashboardPage />)

    await waitFor(() =>
      expect(screen.getByText(/No leads have entered the pipeline yet/i)).toBeInTheDocument(),
    )
  })

  it('renders the reviewer-table empty state when leads exist but no review has been actioned', async () => {
    vi.spyOn(api, 'getFunnelDashboard').mockResolvedValue({
      total_leads: 3,
      by_status: [{ status: 'auto_processed', count: 3 }],
      by_source_channel: [{ source_channel: 'web_form', count: 3, avg_confidence: 0.9 }],
      avg_resolution_seconds: 42,
      reviewer_throughput: [],
    })

    render(<FunnelDashboardPage />)

    await waitFor(() => expect(screen.getByText(/No reviews actioned yet/i)).toBeInTheDocument())
    // Page-level empty state must not also render when leads exist.
    expect(screen.queryByText(/No leads have entered the pipeline yet/i)).not.toBeInTheDocument()
  })

  it('shows an error state when the request fails', async () => {
    vi.spyOn(api, 'getFunnelDashboard').mockRejectedValue(new Error('boom'))

    render(<FunnelDashboardPage />)

    await waitFor(() => expect(screen.getByText(/Failed to load the funnel dashboard/i)).toBeInTheDocument())
  })
})
