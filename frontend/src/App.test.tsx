import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the landing page with links to the main views on the home route', () => {
    render(<App />)
    const main = screen.getByRole('main')
    expect(within(main).getByRole('heading', { name: /Lead Intake Triage/i })).toBeInTheDocument()
    expect(within(main).getByRole('link', { name: /Observability/i })).toHaveAttribute('href', '/leads')
    expect(within(main).getByRole('link', { name: /Review Queue/i })).toHaveAttribute('href', '/reviews')
    expect(within(main).getByRole('link', { name: /Benchmark/i })).toHaveAttribute('href', '/benchmark')
  })
})
