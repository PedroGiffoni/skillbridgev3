export type AnswerOption = { value: number; label: string }
export type Competency = { id: string; name: string; description: string; question: string; expected_level: number; options: AnswerOption[] }
export type Questionnaire = { profession: string; competencies: Competency[]; clarification: string; source_mode: 'gemini'; notice: string; token: string }
export type Answer = { competency_id: string; self_level: number; example: string }
export type Gap = { competency_id: string; name: string; expected_level: number; self_level: number; gap: number }
export type Week = { week: number; title: string; objective: string; actions: string[]; deliverable: string }
export type V3Week = Week & {
  competency_ids: string[]
  estimated_minutes: number
  review: string
  prerequisite_weeks: number[]
}
type AssessmentContent = {
  gaps: Gap[]
  summary: string
  strengths: string[]
  priorities: string[]
  limitations: string[]
  source_mode: 'gemini'
  notice: string
}
export type LegacyAssessment = AssessmentContent & { weeks: Week[]; plan_version?: never; source_assessment_id?: never }
export type V3Assessment = AssessmentContent & { weeks: V3Week[]; plan_version: 3; source_assessment_id: string }
export type Assessment = LegacyAssessment | V3Assessment
export type Profile = { profession: string; course: string; semester: number | null; consent: boolean }

const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null
const text = (v: unknown): v is string => typeof v === 'string' && v.length <= 24000
const texts = (v: unknown): v is string[] => Array.isArray(v) && v.length <= 8 && v.every(text)
const level = (v: unknown): v is number => Number.isInteger(v) && Number(v) >= 0 && Number(v) <= 4
const source = (v: unknown) => v === 'gemini'
const normalizedLabel = (v: string) => v.normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase('pt-BR')
const answerOptions = (v: unknown): v is AnswerOption[] => Array.isArray(v) && v.length === 5 &&
  v.every((o, i) => object(o) && o.value === i && typeof o.label === 'string' && o.label.trim().length >= 12 && o.label.length <= 220) &&
  new Set(v.map(o => normalizedLabel(o.label))).size === 5
const competency = (v: unknown): v is Competency => object(v) && text(v.id) && text(v.name) && text(v.description) && text(v.question) && level(v.expected_level) && answerOptions(v.options)

export function validateQuestionnaire(v: unknown): Questionnaire {
  if (!object(v) || !text(v.profession) || !text(v.clarification) || !text(v.notice) || !text(v.token) || !source(v.source_mode) || !Array.isArray(v.competencies) || !v.competencies.every(competency)) throw new Error('Questionário inválido recebido da API.')
  const count = v.competencies.length
  if (v.clarification ? count !== 0 : count < 5 || count > 8 || !v.token) throw new Error('Questionário incompleto recebido da API.')
  if (new Set(v.competencies.map(c => c.id)).size !== count) throw new Error('Questionário contém competências repetidas.')
  return v as Questionnaire
}

const assessmentFields = ['gaps', 'summary', 'strengths', 'priorities', 'weeks', 'limitations', 'source_mode', 'notice']
const v3AssessmentFields = [...assessmentFields, 'plan_version', 'source_assessment_id']
const weekFields = ['week', 'title', 'objective', 'actions', 'deliverable']
const v3WeekFields = [...weekFields, 'competency_ids', 'estimated_minutes', 'review', 'prerequisite_weeks']
const exactFields = (value: Record<string, unknown>, fields: string[]) =>
  Object.keys(value).length === fields.length && fields.every(field => Object.hasOwn(value, field))
const planText = (v: unknown, limit: number) => typeof v === 'string' && v.trim().length > 0 && Array.from(v).length <= limit

function validWeek(value: unknown, weekNumber: number, competencyIds: ReadonlySet<string> | null) {
  if (!object(value) || value.week !== weekNumber || !text(value.title) || !text(value.objective) ||
    !texts(value.actions) || value.actions.length === 0 || value.actions.length > 4 || !text(value.deliverable)) return false
  if (!competencyIds) return exactFields(value, weekFields)

  const { competency_ids, estimated_minutes, review, prerequisite_weeks } = value
  return exactFields(value, v3WeekFields) &&
    planText(value.title, 120) && planText(value.objective, 280) &&
    value.actions.length <= 3 && value.actions.every(action => planText(action, 280)) && planText(value.deliverable, 280) &&
    texts(competency_ids) && competency_ids.length > 0 && new Set(competency_ids).size === competency_ids.length &&
    competency_ids.every(id => competencyIds.has(id)) &&
    typeof estimated_minutes === 'number' && Number.isInteger(estimated_minutes) && estimated_minutes >= 1 && estimated_minutes <= 240 &&
    planText(review, 280) && Array.isArray(prerequisite_weeks) && prerequisite_weeks.length < weekNumber &&
    new Set(prerequisite_weeks).size === prerequisite_weeks.length &&
    prerequisite_weeks.every(previous => Number.isInteger(previous) && previous >= 1 && previous < weekNumber)
}

export function validateAssessment(v: unknown): Assessment {
  if (!object(v) || !text(v.summary) || !texts(v.strengths) || !texts(v.priorities) || !texts(v.limitations) ||
    !text(v.notice) || !source(v.source_mode) || !Array.isArray(v.gaps) || !Array.isArray(v.weeks)) {
    throw new Error('Diagnóstico inválido recebido da API.')
  }
  const versioned = Object.hasOwn(v, 'plan_version') || Object.hasOwn(v, 'source_assessment_id')
  if (!exactFields(v, versioned ? v3AssessmentFields : assessmentFields) ||
    (versioned && (v.plan_version !== 3 || !text(v.source_assessment_id) || !/^[0-9a-f]{32}$/.test(v.source_assessment_id)))) {
    throw new Error('Diagnóstico inválido recebido da API.')
  }
  if (v.gaps.length < 5 || v.gaps.length > 8 || !v.gaps.every(g => object(g) && text(g.competency_id) && text(g.name) &&
    level(g.expected_level) && level(g.self_level) && level(g.gap) && g.gap === Math.max(0, g.expected_level - g.self_level))) {
    throw new Error('Lacunas inválidas recebidas da API.')
  }
  const competencyIds = versioned ? new Set<string>(v.gaps.map(gap => gap.competency_id)) : null
  if (v.weeks.length !== (versioned ? 12 : 4) || !v.weeks.every((week, i) => validWeek(week, i + 1, competencyIds))) {
    throw new Error('Trilha inválida recebida da API.')
  }
  return v as Assessment
}

export class ApiError extends Error {
  constructor(readonly status: number, message: string) { super(message) }
}

export async function apiFetch(path: string, init: RequestInit, signal?: AbortSignal): Promise<Response> {
  const timeout = AbortSignal.timeout(120000)
  try {
    return await fetch(path, { ...init, credentials: 'same-origin', signal: signal ? AbortSignal.any([signal, timeout]) : timeout })
  } catch {
    if (signal?.aborted) throw new Error('Solicitação cancelada.')
    throw new Error(timeout.aborted ? 'O servidor demorou para responder. Suas respostas foram mantidas; tente novamente.' : 'Não foi possível conectar ao serviço. Confira sua conexão e tente novamente. Suas respostas foram mantidas.')
  }
}

async function post(path: string, data: unknown, signal: AbortSignal): Promise<unknown> {
  const response = await apiFetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }, signal)
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: 'Entre na sua conta para ver o diagnóstico.',
      409: 'Avaliação expirada. Volte ao perfil para gerar um novo questionário.',
      413: 'A solicitação excede o tamanho permitido. Tente iniciar uma nova avaliação.',
      422: 'Dados inválidos. Revise as opções escolhidas e o consentimento.',
      429: 'Limite de solicitações atingido. Aguarde um minuto e tente novamente. Suas respostas foram mantidas.',
      502: 'A IA retornou uma resposta inválida. Suas respostas foram mantidas; tente novamente.',
      503: 'A IA está indisponível no momento. Suas respostas foram mantidas; tente novamente mais tarde.',
      504: 'A IA demorou para responder. Suas respostas foram mantidas; tente novamente.',
    }
    const body = response.status === 409 ? await response.json().catch(() => null) : null
    throw new ApiError(response.status, typeof body?.detail === 'string' ? body.detail :
      messages[response.status] ?? 'O servidor não conseguiu concluir a solicitação. Suas respostas foram mantidas; tente novamente.')
  }
  try { return await response.json() } catch { throw new Error('Resposta inválida da API. Suas respostas foram mantidas; tente novamente.') }
}

export async function requestQuestionnaire(profile: Profile, signal: AbortSignal) {
  return validateQuestionnaire(await post('/api/questionnaire', profile, signal))
}
export async function requestAssessment(data: { token: string; answers: Answer[]; context?: Record<string, string>; consent: boolean }, signal: AbortSignal) {
  return validateAssessment(await post('/api/assessment', data, signal))
}
