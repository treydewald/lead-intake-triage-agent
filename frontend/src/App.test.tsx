import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the observability placeholder on the home route', () => {
    render(<App />)
    expect(screen.getByText(/Observability view/i)).toBeInTheDocument()
  })
})
