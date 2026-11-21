import { ApiError, apiFetch, validateAssessment } from './api'
import type { Assessment } from './api'

export type AccountDetails = {
  display_name: string
  photo: string | null
  course: string
  semester: number | null
  goal: string
}
export type AccountProfile = AccountDetails & { email: string | null }
export type LoginConfig = { email_enabled: boolean; google_client_id: string | null }
export type GoogleLogin = { profile: AccountProfile } | { email: string; link_token: string }
export type HistoryItem = { id: string; profession: string; created_at: string }
export type SavedAssessment = HistoryItem & { assessment: Assessment }

export async function request<T>(path: string, method: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  }, signal)
  if (response.status === 204) return undefined as T
  let data: unknown = null
  try { data = await response.json() } catch { /* Error responses may have no body. */ }
  if (!response.ok) {
    const detail = typeof data === 'object' && data && 'detail' in data ? data.detail : null
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Não foi possível concluir. Tente novamente.')
  }
  if (data === null) throw new Error('A conta retornou uma resposta inválida. Tente novamente.')
  return data as T
}

export async function getAccount(signal?: AbortSignal) {
  try {
    return await request<AccountProfile>('/api/account', 'GET', undefined, signal)
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null
    throw err
  }
}
export const getLoginConfig = (signal?: AbortSignal) =>
  request<LoginConfig>('/api/auth/config', 'GET', undefined, signal)
export const requestCode = (email: string, linkAccount: boolean, signal?: AbortSignal) =>
  request<void>('/api/auth/email/request', 'POST', { email, link_account: linkAccount }, signal)
export const verifyCode = (email: string, code: string, linkToken?: string, linkAccount = false, signal?: AbortSignal) =>
  request<AccountProfile>('/api/auth/email/verify', 'POST', { email, code, link_token: linkToken, link_account: linkAccount }, signal)
export const getGoogleNonce = (signal: AbortSignal) =>
  request<{ nonce: string }>('/api/auth/google/nonce', 'GET', undefined, signal)
export const signInWithGoogle = (credential: string, signal: AbortSignal) =>
  request<GoogleLogin>('/api/auth/google', 'POST', { credential }, signal)
export const logout = () => request<void>('/api/auth/logout', 'POST')
export const updateProfile = (details: AccountDetails) => request<AccountProfile>('/api/account/profile', 'POST', details)

export const getHistory = (signal: AbortSignal) => request<{ items: HistoryItem[] }>('/api/history', 'GET', undefined, signal)
export async function openHistory(id: string) {
  const item = await request<SavedAssessment>('/api/history/' + encodeURIComponent(id), 'GET')
  return { ...item, assessment: validateAssessment(item.assessment) }
}
export const deleteHistory = (id: string) => request<void>('/api/history/' + encodeURIComponent(id), 'DELETE')
