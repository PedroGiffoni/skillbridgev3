import { validateQuestionnaire } from './api'
import { contextQuestions, practiceOptions } from './context'
import type { Questionnaire } from './api'

const storageKey = 'skillbridge-draft-v1'

export type Draft = {
  expiresAt: number
  questionnaire: Questionnaire
  profession: string
  course: string
  semester: string
  answers: (number | null)[]
  examples: string[]
  context: Record<string, string>
  consent: boolean
}

export function clearDraft() {
  try { sessionStorage.removeItem(storageKey) } catch { /* The current tab still keeps its React state. */ }
}

export function readDraft(): (Draft & { needsReview: boolean }) | null {
  try {
    const raw = sessionStorage.getItem(storageKey)
    if (!raw) return null
    const saved = JSON.parse(raw) as Draft
    const q = validateQuestionnaire(saved.questionnaire)
    if (!Number.isFinite(saved.expiresAt) || saved.expiresAt <= Date.now() || saved.consent !== true ||
        saved.profession !== q.profession || typeof saved.course !== 'string' || typeof saved.semester !== 'string' ||
        !Array.isArray(saved.answers) || saved.answers.length !== q.competencies.length ||
        !saved.answers.every(value => Number.isInteger(value) && value !== null && value >= 0 && value <= 4) ||
        !Array.isArray(saved.examples) || saved.examples.length !== q.competencies.length ||
        !saved.examples.every(value => typeof value === 'string' && value.length <= 300) ||
        !saved.context || typeof saved.context !== 'object' || Array.isArray(saved.context) ||
        !Object.values(saved.context).every(value => typeof value === 'string' && value.length <= 500)) {
      clearDraft()
      return null
    }
    const examples = saved.examples.map(value => practiceOptions.some(option => option.value === value) ? value : '')
    const context = Object.fromEntries(contextQuestions.flatMap(({ id, options }) => {
      const choice = saved.context[id]
      return options.some(option => option.value === choice) ? [[id, choice]] : []
    }))
    const needsReview = examples.some((choice, i) => choice !== saved.examples[i]) ||
      Object.entries(saved.context).some(([id, choice]) => Boolean(choice) && context[id] !== choice)
    return { ...saved, examples, context, needsReview }
  } catch {
    clearDraft()
    return null
  }
}

export function saveDraft(draft: Draft) {
  try { sessionStorage.setItem(storageKey, JSON.stringify(draft)) } catch { /* Use the active tab's state if unavailable. */ }
}
