import { render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import * as api from './lib/api'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('renders the landing page with links to the main views on the home route', async () => {
    vi.spyOn(api, 'listLeads').mockResolvedValue({ items: [], total: 12, page: 1, page_size: 1 })
    vi.spyOn(api, 'listReviews').mockResolvedValue([])
    vi.spyOn(api, 'listBenchmarkRuns').mockResolvedValue([])

    render(<App />)
    const main = screen.getByRole('main')

    expect(
      within(main).getByRole('heading', { name: /Automated classification, routing, and review/i }),
    ).toBeInTheDocument()
    expect(within(main).getByRole('link', { name: /Observability/i })).toHaveAttribute('href', '/leads')
    expect(within(main).getByRole('link', { name: /Review Queue/i })).toHaveAttribute('href', '/reviews')
    expect(within(main).getByRole('link', { name: /Benchmark/i })).toHaveAttribute('href', '/benchmark')
    expect(within(main).getByRole('link', { name: /Analytics/i })).toHaveAttribute('href', '/analytics')

    await waitFor(() => expect(within(main).getByText('12')).toBeInTheDocument())
  })
})
