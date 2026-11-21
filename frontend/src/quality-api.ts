import { request } from './account-api'

export const reportLabels = {
  accuracy: 'Informação incorreta',
  answer_key: 'Questão ou gabarito incorreto',
  clarity: 'Explicação confusa',
  accessibility: 'Barreira de acessibilidade',
  inappropriate: 'Conteúdo inadequado',
} as const

export type ReportCategory = keyof typeof reportLabels

export type QualityFilters = {
  windowDays: number
  model: string
  promptVersion: string
  career: string
}

type JobStatus = 'queued' | 'running' | 'ready' | 'failed' | 'needs_review'
type FailureReason = 'quota' | 'provider_503' | 'unavailable' | 'timeout' | 'invalid_response' | 'other'

type Generation = {
  restricted: boolean
  total: number | null
  by_status: Record<JobStatus, number> | null
  failures: Record<FailureReason, number> | null
  rejection_rate: number | null
  latency_ms: { average: number; samples: number } | null
  input_tokens: { total: number; samples: number } | null
  output_tokens: { total: number; samples: number } | null
  cost_usd: number | null
}

export type QualitySnapshot = {
  window_days: number
  generation: Generation
  reports: Record<ReportCategory, number | null>
  progress: {
    learners: number | null
    lessons_completed: number | null
    modules_mastered: number | null
  }
  models: string[]
  prompt_versions: number[]
  careers: string[]
  privacy_minimum: number
}

export const getAdminAccess = (signal?: AbortSignal) =>
  request<{ allowed: boolean }>('/api/admin/access', 'GET', undefined, signal)

export function readQuality(filters: QualityFilters, signal: AbortSignal) {
  const query = new URLSearchParams({ window_days: String(filters.windowDays) })
  if (filters.model) query.set('model', filters.model)
  if (filters.promptVersion) query.set('prompt_version', filters.promptVersion)
  if (filters.career) query.set('career', filters.career)
  return request<QualitySnapshot>('/api/admin/quality?' + query, 'GET', undefined, signal)
}

export const submitContentReport = (lessonId: string, category: ReportCategory, signal: AbortSignal) =>
  request<void>('/api/content-reports', 'POST', { lesson_id: lessonId, category }, signal)
