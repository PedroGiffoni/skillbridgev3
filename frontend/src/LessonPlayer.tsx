import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from './api'
import { requestPracticeHint, submitPractice } from './course-api'
import type { Lesson, PracticeAnswer, PracticeProgress } from './course-api'

function initialAnswer(lesson: Lesson): PracticeAnswer {
  switch (lesson.format) {
    case 'multiple_choice': return { kind: lesson.format, option_id: '' }
    case 'order_steps': return { kind: lesson.format, step_ids: lesson.exercise.steps.map(step => step.id) }
    case 'fill_blank': return { kind: lesson.format, text: '' }
  }
}

type PlayerProps = {
  lesson: Lesson
  onExpired: () => void
  onProgress: (progress: PracticeProgress) => void
}

export function LessonPlayer({ lesson, onExpired, onProgress }: PlayerProps) {
  const promptId = useId()
  const controller = useRef<AbortController | null>(null)
  const attemptId = useRef<string>(null)
  const feedbackTitle = useRef<HTMLHeadingElement>(null)
  const prompt = useRef<HTMLLegendElement>(null)
  const hintText = useRef<HTMLParagraphElement>(null)
  const focusAfterRetry = useRef(false)
  const [answer, setAnswer] = useState(() => initialAnswer(lesson))
  const [progress, setProgress] = useState(lesson.practice)
  const [latest, setLatest] = useState(lesson.practice.latest_attempt)
  const [submitted, setSubmitted] = useState(false)
  const [busy, setBusy] = useState<'hint' | 'answer' | null>(null)
  const [hint, setHint] = useState<{ text: string; receipt: string } | null>(null)
  const [error, setError] = useState('')
  const [position, setPosition] = useState('')
  const hasAnswer = answer.kind === 'multiple_choice' ? Boolean(answer.option_id)
    : answer.kind === 'fill_blank' ? Boolean(answer.text.trim()) : true

  useEffect(() => () => controller.current?.abort(), [])

  async function perform(kind: 'hint' | 'answer', action: (id: string, signal: AbortSignal) => Promise<void>) {
    if (controller.current) return
    const current = new AbortController()
    controller.current = current
    setBusy(kind)
    setError('')
    try {
      attemptId.current ??= crypto.randomUUID().replaceAll('-', '')
      await action(attemptId.current, current.signal)
    } catch (err) {
      if (current.signal.aborted) return
      if (err instanceof ApiError && err.status === 401) onExpired()
      else {
        // Validation errors are rejected before the attempt is recorded. Retry ambiguous failures with the same answer.
        if (kind === 'answer' && err instanceof ApiError && err.status === 422) setSubmitted(false)
        setError(err instanceof ApiError ? err.message : 'Não foi possível se conectar. Tente novamente.')
      }
    } finally {
      if (!current.signal.aborted) {
        controller.current = null
        setBusy(null)
      }
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!hasAnswer || controller.current) return
    setSubmitted(true)
    void perform('answer', async (id, signal) => {
      const result = await submitPractice(lesson.id, id, answer, hint?.receipt, signal)
      if (signal.aborted) return
      setProgress(result.practice)
      setLatest(result.attempt)
      onProgress(result.practice)
    })
  }

  function retry() {
    attemptId.current = null
    setAnswer(initialAnswer(lesson))
    setLatest(null)
    setSubmitted(false)
    focusAfterRetry.current = true
    setHint(null)
    setError('')
    setPosition('')
  }

  useEffect(() => {
    if (latest && submitted) feedbackTitle.current?.focus()
  }, [latest, submitted])

  useEffect(() => {
    if (!focusAfterRetry.current) return
    focusAfterRetry.current = false
    prompt.current?.focus()
  }, [answer])

  useEffect(() => {
    if (hint) hintText.current?.focus()
  }, [hint])

  function move(index: number, change: number) {
    if (answer.kind !== 'order_steps' || lesson.format !== 'order_steps' || busy || submitted) return
    const target = index + change
    if (target < 0 || target >= answer.step_ids.length) return
    const stepIds = [...answer.step_ids]
    const [id] = stepIds.splice(index, 1)
    stepIds.splice(target, 0, id)
    setAnswer({ kind: answer.kind, step_ids: stepIds })
    const label = lesson.exercise.steps.find(step => step.id === id)?.label
    setPosition(label + ' na posição ' + (target + 1) + ' de ' + stepIds.length + '.')
  }

  return <article className="library-lesson">
    <h4>Objetivo</h4><p>{lesson.objective}</p>
    <h4>Explicação</h4><p>{lesson.explanation}</p>
    <h4>Exemplo</h4><p>{lesson.example}</p>
    <h4>Prática</h4>
    <p role="status">{progress.completed ? 'Prática concluída. ' : ''}
      {progress.attempts === 1 ? '1 tentativa registrada.' : progress.attempts + ' tentativas registradas.'}
    </p>
    {latest ? <div className="practice-feedback">
      <h4 ref={feedbackTitle} tabIndex={-1}>{latest.correct ? 'Resposta correta' : 'Revise e tente novamente'}</h4>
      {latest.hint_used && <p>Dica usada nesta tentativa.</p>}
      {latest.feedback.map(message => <p key={message}>{message}</p>)}
    </div> : <form className="practice-form" onSubmit={submit} aria-busy={Boolean(busy)}>
      <fieldset disabled={submitted}>
        <legend ref={prompt} tabIndex={-1}>
          {lesson.format === 'fill_blank' ? lesson.exercise.prompt.replace('[lacuna]', '_____') : lesson.exercise.prompt}
        </legend>
        {lesson.format === 'multiple_choice' && answer.kind === 'multiple_choice' &&
          <div className="practice-options">{lesson.exercise.options.map(option =>
            <label key={option.id} className="practice-option">
              <input type="radio" name={promptId} value={option.id} checked={answer.option_id === option.id}
                onChange={() => setAnswer({ kind: answer.kind, option_id: option.id })}/>
              <span>{option.label}</span>
            </label>
          )}</div>}
        {lesson.format === 'order_steps' && answer.kind === 'order_steps' &&
          <>
            <p>Use os botões para ajustar a sequência dos passos.</p>
            <ol className="practice-order">{answer.step_ids.map((id, index) => {
              const item = lesson.exercise.steps.find(step => step.id === id)!
              return <li key={id}>
                <span>{item.label}</span>
                <div className="practice-actions">
                  <button className="secondary" type="button" aria-disabled={index === 0}
                    aria-label={'Mover ' + item.label + ' para cima'} onClick={() => move(index, -1)}>Subir</button>
                  <button className="secondary" type="button" aria-disabled={index === answer.step_ids.length - 1}
                    aria-label={'Mover ' + item.label + ' para baixo'} onClick={() => move(index, 1)}>Descer</button>
                </div>
              </li>
            })}</ol>
            <p className="practice-announcement" role="status">{position}</p>
          </>}
        {lesson.format === 'fill_blank' && answer.kind === 'fill_blank' &&
          <label className="practice-blank">Resposta da lacuna
            <input type="text" value={answer.text} maxLength={80} autoComplete="off"
              onChange={event => setAnswer({ kind: answer.kind, text: event.currentTarget.value })}/>
          </label>}
      </fieldset>
      {hint && <p className="practice-hint" ref={hintText} tabIndex={-1}>{hint.text}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="practice-actions">
        <button className="primary" disabled={!hasAnswer} aria-disabled={Boolean(busy)} type="submit">
          {busy === 'answer' ? 'Corrigindo…' : submitted ? 'Reenviar resposta' : 'Corrigir resposta'}
        </button>
        {!submitted && !hint && <button className="secondary" aria-disabled={Boolean(busy)} type="button"
          onClick={() => void perform('hint', async (id, signal) => {
            const result = await requestPracticeHint(lesson.id, id, signal)
            if (!signal.aborted) setHint(result)
          })}>{busy === 'hint' ? 'Carregando dica…' : 'Ver dica'}</button>}
        {error && <button className="secondary" type="button" onClick={retry}>Nova tentativa</button>}
      </div>
    </form>}
    {latest && <>
      <h4>Resumo</h4><p>{lesson.summary}</p>
      <button className="secondary" type="button" onClick={retry}>{latest.correct ? 'Praticar novamente' : 'Nova tentativa'}</button>
    </>}
  </article>
}
