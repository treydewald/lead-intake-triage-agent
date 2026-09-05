import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
})

export interface LeadListItem {
  lead_id: string
  run_id: string
  status: string
  source_channel: string | null
  confidence_score: number | null
  created_at: string
  updated_at: string
}

export interface LeadListResponse {
  items: LeadListItem[]
  total: number
  page: number
  page_size: number
}

export interface ListLeadsParams {
  status?: string
  source_channel?: string
  sort?: 'created_desc' | 'confidence_asc' | 'confidence_desc'
  page?: number
  page_size?: number
}

export interface StageDetail {
  stage_key: string
  stage_label: string
  status: 'COMPLETED' | 'FAILED' | 'NOT_YET_RUN'
  decision: Record<string, unknown> | null
  error: string | null
  created_at: string | null
}

export interface LeadDetail {
  lead_id: string
  run_id: string
  status: string
  source_channel: string | null
  confidence_score: number | null
  created_at: string
  updated_at: string
  failed_stage: string | null
  error: string | null
  stages: StageDetail[]
}

export async function listLeads(params: ListLeadsParams = {}): Promise<LeadListResponse> {
  const response = await api.get<LeadListResponse>('/leads', { params })
  return response.data
}

export async function getLeadDetail(leadId: string): Promise<LeadDetail> {
  const response = await api.get<LeadDetail>(`/leads/${leadId}`)
  return response.data
}

export interface BenchmarkCase {
  case_id: string
  category: string
  expected_label: string | null
  is_ambiguous: boolean
  predicted_label: string | null
  confidence: number | null
  correct: boolean | null
  consistent: boolean
}

export interface BenchmarkRunSummary {
  id: string
  created_at: string
  model_used: string
  repeats: number
  total_cases: number
  accuracy: number
  consistency: number
}

export interface BenchmarkRun extends BenchmarkRunSummary {
  cases: BenchmarkCase[]
}

export async function runBenchmark(repeats = 3): Promise<BenchmarkRun> {
  const response = await api.post<BenchmarkRun>('/benchmark/run', null, { params: { repeats } })
  return response.data
}

export async function listBenchmarkRuns(): Promise<BenchmarkRunSummary[]> {
  const response = await api.get<{ items: BenchmarkRunSummary[] }>('/benchmark/runs')
  return response.data.items
}

export async function getBenchmarkRun(runId: string): Promise<BenchmarkRun> {
  const response = await api.get<BenchmarkRun>(`/benchmark/runs/${runId}`)
  return response.data
}
