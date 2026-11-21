import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { request } from './account-api'
import type { CourseItem } from './course-api'
import { useLearningRequest } from './useLearningRequest'
import './learning-progress.css'

type Question = { id: string; prompt: string; options: { id: string; label: string }[] }
type Exam = { id: string; questions: Question[] }
type Result = {
  form_id: string
  submitted_at: string
  score: number
  correct: number
  total: number
  passed: boolean
  competencies: { id: string; name: string; correct: number; total: number }[]
  reinforcement: { outline_id: string; title: string }[]
}
type ExamStatus = { available: boolean; pending: boolean; form: Exam | null; result: Result | null }

function ExamForm({ form, disabled, submit }: {
  form: Exam
  disabled: boolean
  submit: (answers: Record<string, string>) => void
}) {
  const group = useId()
  const legend = useRef<HTMLLegendElement>(null)
  const [page, setPage] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const question = form.questions[page]
  const unanswered = form.questions.findIndex(item => !answers[item.id])
  const answered = form.questions.filter(item => Boolean(answers[item.id])).length
  const last = page === form.questions.length - 1

  function move(next: number) {
    setPage(next)
  }

  useEffect(() => {
    legend.current?.focus()
  }, [page])

  function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (answered === form.questions.length && !disabled) submit(answers)
  }

  return <form className="practice-form mastery-form" onSubmit={send} aria-busy={disabled}>
    <p className="mastery-question-count" role="status">Questão {page + 1} de {form.questions.length} · {answered} respondidas</p>
    <fieldset disabled={disabled}>
      <legend ref={legend} tabIndex={-1}>{question.prompt}</legend>
      <div className="practice-options">
        {question.options.map(option => <label key={option.id} className="practice-option">
          <input type="radio" name={group + '-' + question.id} value={option.id} checked={answers[question.id] === option.id}
            onChange={() => setAnswers(previous => ({ ...previous, [question.id]: option.id }))}/>
          <span>{option.label}</span>
        </label>)}
      </div>
    </fieldset>
    <div className="practice-actions">
      {page > 0 && <button type="button" className="secondary" disabled={disabled}
        onClick={() => move(page - 1)}>Questão anterior</button>}
      {!last && <button type="button" className="primary" disabled={disabled}
        onClick={() => move(page + 1)}>Próxima questão</button>}
      {last && unanswered >= 0 && unanswered !== page &&
        <button type="button" className="secondary" disabled={disabled} onClick={() => move(unanswered)}>Ir à primeira questão em branco</button>}
      {last && <button type="submit" className="primary" disabled={disabled || unanswered >= 0}>
        {disabled ? 'Corrigindo avaliação…' : 'Enviar avaliação'}
      </button>}
    </div>
  </form>
}

export function ModuleAssessment({ course, moduleId, onExpired, onUnlock, onReview }: {
  course: CourseItem
  moduleId: string
  onExpired: () => void
  onUnlock: () => void
  onReview: (outlineId: string) => void
}) {
  const titleId = useId()
  const resultHeading = useRef<HTMLHeadingElement>(null)
  const focusResult = useRef(false)
  const [state, setState] = useState<ExamStatus | null>(null)
  const [consent, setConsent] = useState(false)
  const { busy, error, run } = useLearningRequest(onExpired)
  const path = '/api/courses/' + encodeURIComponent(course.id) + '/modules/' + encodeURIComponent(moduleId) + '/assessment'
  const revision = course.revision

  const refresh = useCallback(() => run(async signal => {
    const result = await request<ExamStatus>(path + '?course_revision=' + revision, 'GET', undefined, signal)
    if (!signal.aborted) setState(result)
  }), [path, revision, run])
  useEffect(() => { void refresh() }, [refresh])
  useEffect(() => {
    if (!state?.pending || busy || error) return
    const timer = window.setTimeout(() => void refresh(), 1000)
    return () => window.clearTimeout(timer)
  }, [state, busy, error, refresh])
  useEffect(() => {
    if (focusResult.current && state?.result && resultHeading.current) {
      focusResult.current = false
      resultHeading.current.focus()
    }
  }, [state])

  const form = state?.form
  const result = state?.result

  function prepare() {
    if (!consent || busy) return
    void run(async signal => {
      const updated = await request<ExamStatus>(path, 'POST', {
        course_revision: revision, consent: true, previous_form_id: result?.form_id,
      }, signal)
      if (!signal.aborted) {
        setConsent(false)
        setState(updated)
      }
    })
  }

  function submit(answers: Record<string, string>) {
    if (!state || !form || busy) return
    void run(async signal => {
      const outcome = await request<Result>(path + '/submit', 'POST', {
        course_revision: revision, form_id: form.id, answers,
      }, signal)
      if (signal.aborted) return
      focusResult.current = true
      setState({ ...state, form: null, pending: false, result: outcome })
      if (outcome.passed) onUnlock()
    })
  }

  return <section className="mastery-panel" aria-labelledby={titleId}>
    <h4 id={titleId}>Avaliação de domínio</h4>
    <p>Para aprovar, acerte pelo menos 80% da prova e uma questão de cada competência crítica do módulo.</p>
    {!state && !error && <p role="status">Carregando avaliação…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {error && (!state || state.pending) &&
      <button type="button" className="secondary" disabled={busy} onClick={() => void refresh()}>Consultar avaliação</button>}
    {state?.pending && <p role="status">Preparando as questões…</p>}

    {form && <ExamForm key={form.id} form={form} disabled={busy} submit={submit}/>}

    {!form && result && <div className="mastery-result">
      <h5 ref={resultHeading} tabIndex={-1}>{result.passed ? 'Módulo aprovado' : 'Reforce o conteúdo e tente novamente'}</h5>
      <p><strong>{result.score}% de aproveitamento</strong> · {result.correct} de {result.total} acertos.</p>
      <ul className="mastery-competencies">
        {result.competencies.map(item => <li key={item.id}>
          <strong>{item.name}</strong>
          <span>{item.correct} de {item.total} acertos{item.correct === 0 ? ' · Requer revisão' : ''}</span>
        </li>)}
      </ul>
      {result.reinforcement.length > 0 && <>
        <h6>Lições para revisar</h6>
        <ul className="mastery-review-list">
          {result.reinforcement.map(lesson => <li key={lesson.outline_id}>
            <button className="secondary" type="button" onClick={() => onReview(lesson.outline_id)}>{lesson.title}</button>
          </li>)}
        </ul>
      </>}
    </div>}

    {state && !form && !state.pending && !result?.passed && (state.available ? <div className="mastery-generate">
      <label className="checkbox">
        <input type="checkbox" checked={consent} onChange={event => setConsent(event.currentTarget.checked)}/>
        <span>Autorizo o envio dos objetivos e tópicos do módulo ao Gemini para gerar a avaliação.</span>
      </label>
      <button type="button" className="primary" disabled={busy || !consent} onClick={prepare}>
        {busy ? 'Preparando avaliação…' : result ? 'Preparar nova prova' : 'Preparar avaliação'}
      </button>
    </div> : <p className="notice">A geração de uma nova avaliação está indisponível no momento.</p>)}
  </section>
}