import { request } from './account-api'

export type ThemeAudioFormat = 'video' | 'audiobook' | 'podcast'
export type ThemeAssessmentKind = 'quiz' | 'simulation'
export type ThemeJob = {
  status: 'idle' | 'queued' | 'running' | 'ready' | 'failed' | 'needs_review'
  attempts: number
  retry_after_seconds: number
  error: { detail: string; retryable: boolean } | null
}
export type ThemeOption = { id: string; label: string }
export type ThemeQuestion = { id: string; prompt: string; options: ThemeOption[] }
export type ThemeGrade = {
  items: { question_id: string; correct: boolean; feedback: string }[]
  correct: number
  total: number
}
export type ThemePack = {
  slides: { title: string; points: string[]; narration: string; diagram?: string[] | null }[]
  chapter: { title: string; sections: { title: string; text: string }[] }
  podcast: { title: string; turns: { speaker: 'host' | 'expert'; text: string }[] }
  map: { topic: string; branches: { label: string; details: string[] }[] }
  quiz: ThemeQuestion[]
  simulation: ThemeQuestion[]
}
export type ThemeState = {
  study: ThemeJob
  content: ThemePack | null
  audio: Record<ThemeAudioFormat, ThemeJob & { segments: number }>
  text_available: boolean
  audio_available: boolean
}

const path = (lessonId: string) => '/api/lessons/' + encodeURIComponent(lessonId) + '/materials'
export const readTheme = (lessonId: string, signal: AbortSignal) =>
  request<ThemeState>(path(lessonId), 'GET', undefined, signal)
export const generateTheme = (lessonId: string, retryAttempt: number | undefined, signal: AbortSignal) =>
  request<ThemeState>(path(lessonId), 'POST', { consent: true, retry_attempt: retryAttempt }, signal)
export const generateThemeAudio = (
  lessonId: string, format: ThemeAudioFormat, retryAttempt: number | undefined, signal: AbortSignal,
) => request<ThemeState>(path(lessonId) + '/audio/' + format, 'POST',
  { consent: true, retry_attempt: retryAttempt }, signal)
export const themeAudioSource = (lessonId: string, format: ThemeAudioFormat, index: number) =>
  path(lessonId) + '/audio/' + format + '/' + index
export const gradeTheme = (
  lessonId: string, kind: ThemeAssessmentKind, answers: Record<string, string>, signal: AbortSignal,
) => request<ThemeGrade>(path(lessonId) + '/' + kind + '/grade', 'POST', { answers }, signal)
