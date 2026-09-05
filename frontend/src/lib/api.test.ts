import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  actionReview,
  api,
  getBenchmarkRun,
  getLeadDetail,
  getLeadHistory,
  getReview,
  listBenchmarkRuns,
  listLeads,
  listReviews,
  runBenchmark,
} from './api'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api client', () => {
  it('listLeads sends the given params to GET /leads and returns the response data', async () => {
    const data = { items: [], total: 0, page: 1, page_size: 10 }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await listLeads({ status: 'failed', page: 2 })

    expect(getSpy).toHaveBeenCalledWith('/leads', { params: { status: 'failed', page: 2 } })
    expect(result).toBe(data)
  })

  it('getLeadDetail calls GET /leads/:leadId and returns the response data', async () => {
    const data = { lead_id: 'lead-1' }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getLeadDetail('lead-1')

    expect(getSpy).toHaveBeenCalledWith('/leads/lead-1')
    expect(result).toBe(data)
  })

  it('getLeadHistory calls GET /leads/:leadId/history and returns the response data', async () => {
    const data = { lead_id: 'lead-1', entries: [] }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getLeadHistory('lead-1')

    expect(getSpy).toHaveBeenCalledWith('/leads/lead-1/history')
    expect(result).toBe(data)
  })

  it('runBenchmark defaults repeats to 3 and returns the response data', async () => {
    const data = { id: 'run-1' }
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data })

    const result = await runBenchmark()

    expect(postSpy).toHaveBeenCalledWith('/benchmark/run', null, { params: { repeats: 3 } })
    expect(result).toBe(data)
  })

  it('runBenchmark passes a custom repeats value through', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: {} })

    await runBenchmark(5)

    expect(postSpy).toHaveBeenCalledWith('/benchmark/run', null, { params: { repeats: 5 } })
  })

  it('listBenchmarkRuns unwraps the items array from the response', async () => {
    const items = [{ id: 'run-1' }]
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: { items } })

    const result = await listBenchmarkRuns()

    expect(getSpy).toHaveBeenCalledWith('/benchmark/runs')
    expect(result).toBe(items)
  })

  it('getBenchmarkRun calls GET /benchmark/runs/:runId and returns the response data', async () => {
    const data = { id: 'run-1' }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getBenchmarkRun('run-1')

    expect(getSpy).toHaveBeenCalledWith('/benchmark/runs/run-1')
    expect(result).toBe(data)
  })

  it('listReviews calls GET /reviews and returns the response data', async () => {
    const data = [{ id: 'review-1' }]
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await listReviews()

    expect(getSpy).toHaveBeenCalledWith('/reviews')
    expect(result).toBe(data)
  })

  it('getReview calls GET /reviews/:runId and returns the response data', async () => {
    const data = { id: 'review-1' }
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data })

    const result = await getReview('run-1')

    expect(getSpy).toHaveBeenCalledWith('/reviews/run-1')
    expect(result).toBe(data)
  })

  it('actionReview posts the action payload to /reviews/:runId/action', async () => {
    const data = { id: 'review-1', status: 'auto_processed' }
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data })
    const payload = { action: 'approve' as const }

    const result = await actionReview('run-1', payload)

    expect(postSpy).toHaveBeenCalledWith('/reviews/run-1/action', payload)
    expect(result).toBe(data)
  })
})
