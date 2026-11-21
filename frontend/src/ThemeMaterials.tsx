import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from './api'
import { generateTheme, generateThemeAudio, gradeTheme, readTheme, themeAudioSource } from './theme-api'
import type { ThemeAssessmentKind, ThemeAudioFormat, ThemeGrade, ThemeJob, ThemePack, ThemeQuestion, ThemeState } from './theme-api'
import './theme.css'

type Expiry = { onExpired: () => void }
type ThemeMode = ThemeAudioFormat | ThemeAssessmentKind | 'map'

const formats: { mode: ThemeMode; label: string }[] = [
  { mode: 'video', label: 'Videoaula' },
  { mode: 'audiobook', label: 'Audiolivro' },
  { mode: 'podcast', label: 'Podcast' },
  { mode: 'map', label: 'Mapa mental' },
  { mode: 'quiz', label: 'Quiz' },
  { mode: 'simulation', label: 'Simulado' },
]

function useThemeRequest(onExpired: () => void) {
  const controller = useRef<AbortController | null>(null)
  const expire = useRef(onExpired)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { expire.current = onExpired }, [onExpired])
  useEffect(() => () => {
    controller.current?.abort()
    controller.current = null
  }, [])

  const run = useCallback(async (task: (signal: AbortSignal) => Promise<void>) => {
    if (controller.current) return
    const current = new AbortController()
    controller.current = current
    setBusy(true)
    setError('')
    try {
      await task(current.signal)
    } catch (error) {
      if (current.signal.aborted) return
      if (error instanceof ApiError && error.status === 401) expire.current()
      else setError(error instanceof Error ? error.message : 'Não foi possível carregar os materiais.')
    } finally {
      if (!current.signal.aborted) {
        controller.current = null
        setBusy(false)
      }
    }
  }, [])
  return { busy, error, run }
}

const pending = (job: ThemeJob) => job.status === 'queued' || job.status === 'running'
const canGenerate = (job: ThemeJob) => job.status === 'idle' || Boolean(job.error?.retryable)

function JobNotice({ job }: { job: ThemeJob }) {
  if (pending(job)) return <p role="status">{job.status === 'queued'
    ? 'Material na fila de preparação.'
    : 'Gemini está preparando o material.'}</p>
  if (!job.error) return null
  return <p role="status" className="error">{job.error.detail}
    {job.retry_after_seconds > 0 && ' Aguarde antes de tentar novamente.'}</p>
}

function GenerateMaterial({ job, available, busy, consentText, label, unavailable, onGenerate }: {
  job: ThemeJob
  available: boolean
  busy: boolean
  consentText: string
  label: string
  unavailable: string
  onGenerate: (onSaved: () => void) => void
}) {
  const [consent, setConsent] = useState(false)
  if (job.status === 'ready') return null
  return <div className="theme-generate">
    <JobNotice job={job}/>
    {!available && !pending(job) && <p>{unavailable}</p>}
    {available && canGenerate(job) && <>
      <label className="checkbox">
        <input type="checkbox" checked={consent} onChange={event => setConsent(event.currentTarget.checked)}/>
        <span>{consentText}</span>
      </label>
      <button className="primary" type="button" disabled={!consent || busy || job.retry_after_seconds > 0}
        onClick={() => onGenerate(() => setConsent(false))}>
        {job.status === 'idle' ? label : 'Tentar novamente'}
      </button>
    </>}
  </div>
}

function ThemeMap({ map }: { map: ThemePack['map'] }) {
  return <section aria-label="Mapa mental">
    <h5 className="theme-map-topic">{map.topic}</h5>
    <ul className="theme-map">
      {map.branches.map(branch => <li key={branch.label}>
        <details>
          <summary>{branch.label}</summary>
          <ul className="theme-bullets">{branch.details.map(detail => <li key={detail}>{detail}</li>)}</ul>
        </details>
      </li>)}
    </ul>
  </section>
}

const speakers = { host: 'Apresentador', expert: 'Especialista' }

function ThemeSegmentPlayer({ lessonId, mode, pack, recordings, onAudioError }: {
  lessonId: string
  mode: ThemeAudioFormat
  pack: ThemePack
  recordings: number
  onAudioError: () => void
}) {
  const [index, setIndex] = useState(0)
  const [audioError, setAudioError] = useState(false)
  const player = useRef<HTMLAudioElement>(null)
  const resume = useRef(false)
  const scenes = pack.slides
  const chapter = pack.chapter
  const podcast = pack.podcast
  const segments = mode === 'video' ? scenes.length : mode === 'audiobook' ? chapter.sections.length : 1
  const label = mode === 'video' ? 'Cena' : 'Seção'
  const hasRecording = recordings === segments
  const source = hasRecording ? themeAudioSource(lessonId, mode, index) : undefined

  useEffect(() => {
    if (!source || !resume.current || !player.current) return
    resume.current = false
    // Reuse the same audio element across segments. Native controls remain available if autoplay is restricted.
    void player.current.play().catch(() => {})
  }, [source])

  function go(target: number, autoplay = false) {
    if (target < 0 || target >= segments) return
    resume.current = autoplay
    setAudioError(false)
    setIndex(target)
  }

  return <>
    {mode === 'video' && <figure className="theme-slide">
      <div className="theme-slide-content">
        <h5>{scenes[index].title}</h5>
        <ul className="theme-bullets">{scenes[index].points.map(point => <li key={point}>{point}</li>)}</ul>
        {scenes[index].diagram && <ol className="theme-diagram" aria-label="Sequência ilustrada">
          {scenes[index].diagram?.map((step, position) => <li key={step}>
            {position > 0 && <span aria-hidden="true">→</span>}
            <span>{step}</span>
          </li>)}
        </ol>}
      </div>
      <figcaption><strong>Narração desta cena</strong> {scenes[index].narration}</figcaption>
    </figure>}
    {mode === 'audiobook' && <section aria-label="Capítulo do audiolivro">
      <h5>{chapter.title}</h5>
      <h6>{chapter.sections[index].title}</h6>
      <p>{chapter.sections[index].text}</p>
    </section>}
    {mode === 'podcast' && <h5>{podcast.title}</h5>}
    {source && <audio ref={player} className="theme-audio" controls preload="metadata" src={source}
      aria-label={mode === 'video' ? 'Narração da cena' : mode === 'podcast' ? 'Áudio do podcast' : 'Narração da seção'}
      onEnded={() => go(index + 1, true)} onLoadedMetadata={() => setAudioError(false)}
      onError={() => { setAudioError(true); onAudioError() }}/>}
    {audioError && <p role="alert" className="error">Não foi possível reproduzir a gravação. Tente reabrir o material.</p>}
    {segments > 1 && <div className="practice-actions theme-segments">
      <button className="secondary" type="button" disabled={index === 0} onClick={() => go(index - 1)}>Anterior</button>
      <p role="status">{label} {index + 1} de {segments}</p>
      <button className="secondary" type="button" disabled={index === segments - 1}
        onClick={() => go(index + 1)}>Próxima</button>
    </div>}
    {mode === 'podcast' && <details className="theme-transcript">
      <summary>Transcrição do podcast</summary>
      <ol>{podcast.turns.map((turn, index) => <li key={index}>
        <strong>{speakers[turn.speaker]}</strong>
        <p>{turn.text}</p>
      </li>)}</ol>
    </details>}
  </>
}

function ThemeAssessment({ lessonId, kind, questions, onExpired }: Expiry & {
  lessonId: string
  kind: ThemeAssessmentKind
  questions: ThemeQuestion[]
}) {
  const formId = useId()
  const gradeHeading = useRef<HTMLHeadingElement>(null)
  const firstLegend = useRef<HTMLLegendElement>(null)
  const focusQuestion = useRef(false)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [index, setIndex] = useState(0)
  const [grades, setGrades] = useState<ThemeGrade['items']>([])
  const [showSummary, setShowSummary] = useState(false)
  const { busy, error, run } = useThemeRequest(onExpired)
  const isQuiz = kind === 'quiz'
  const visible = isQuiz ? [questions[index]] : questions
  const currentGrade = isQuiz ? grades.find(grade => grade.question_id === visible[0].id) : undefined
  const answered = visible.every(question => Boolean(answers[question.id]))
  const completed = grades.length === questions.length

  useEffect(() => {
    if (grades.length || showSummary) gradeHeading.current?.focus()
  }, [grades, showSummary])

  useEffect(() => {
    if (focusQuestion.current) {
      firstLegend.current?.focus()
      focusQuestion.current = false
    }
  }, [index, grades.length, showSummary])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!answered || currentGrade || completed) return
    const submission = Object.fromEntries(visible.map(question => [question.id, answers[question.id]]))
    void run(async signal => {
      const result = await gradeTheme(lessonId, kind, submission, signal)
      if (!signal.aborted) setGrades(previous => [...previous, ...result.items])
    })
  }

  function reset() {
    focusQuestion.current = true
    setAnswers({})
    setIndex(0)
    setGrades([])
    setShowSummary(false)
  }

  if ((!isQuiz && completed) || showSummary) return <section aria-labelledby={formId + '-result'} className="practice-feedback">
    <h5 id={formId + '-result'} ref={gradeHeading} tabIndex={-1}>Resultado do {isQuiz ? 'quiz' : 'simulado'}</h5>
    <p>{grades.filter(grade => grade.correct).length} de {questions.length} respostas corretas.</p>
    {!isQuiz && <ol className="theme-bullets">{questions.map(question => {
      const grade = grades.find(item => item.question_id === question.id)
      return <li key={question.id}>
        <strong>{question.prompt}</strong>
        <p>{grade?.correct ? 'Resposta correta. ' : 'Revise esta questão. '}{grade?.feedback}</p>
      </li>
    })}</ol>}
    <button className="secondary" type="button" onClick={reset}>{isQuiz ? 'Refazer quiz' : 'Refazer simulado'}</button>
  </section>

  return <form className="practice-form theme-assessment" onSubmit={submit}>
    {isQuiz && <p role="status">Questão {index + 1} de {questions.length}</p>}
    {visible.map((question, position) => <fieldset key={question.id} disabled={Boolean(currentGrade) || busy}>
      <legend ref={position === 0 ? firstLegend : undefined} tabIndex={-1}>{question.prompt}</legend>
      <div className="practice-options">{question.options.map(option => <label key={option.id} className="practice-option">
        <input type="radio" name={formId + '-' + question.id} value={option.id}
          checked={answers[question.id] === option.id}
          onChange={() => setAnswers(previous => ({ ...previous, [question.id]: option.id }))}/>
        <span>{option.label}</span>
      </label>)}</div>
    </fieldset>)}
    {error && <p role="alert" className="error">{error}</p>}
    {currentGrade ? <section className="practice-feedback" aria-labelledby={formId + '-feedback'}>
      <h5 id={formId + '-feedback'} ref={gradeHeading} tabIndex={-1}>
        {currentGrade.correct ? 'Resposta correta' : 'Revise esta questão'}
      </h5>
      <p>{currentGrade.feedback}</p>
      <button className="secondary" type="button" onClick={() => {
        if (completed) setShowSummary(true)
        else {
          focusQuestion.current = true
          setIndex(index + 1)
        }
      }}>{completed ? 'Ver resultado do quiz' : 'Próxima questão'}</button>
    </section> : <button className="primary" type="submit" disabled={!answered} aria-disabled={busy}>
      {busy ? 'Corrigindo…' : isQuiz ? 'Corrigir questão' : 'Enviar simulado'}
    </button>}
  </form>
}

export function ThemeMaterials({ lessonId, onExpired }: Expiry & { lessonId: string }) {
  const headingId = useId()
  const panelId = useId()
  const [state, setState] = useState<ThemeState | null>(null)
  const [mode, setMode] = useState<ThemeMode>('video')
  const { busy, error, run } = useThemeRequest(onExpired)
  const update = useCallback((load: (signal: AbortSignal) => Promise<ThemeState>, onSaved?: () => void) =>
    run(async signal => {
      const next = await load(signal)
      if (signal.aborted) return
      setState(next)
      onSaved?.()
    }), [run])
  const refresh = useCallback(() => update(signal => readTheme(lessonId, signal)), [lessonId, update])
  useEffect(() => { void refresh() }, [refresh])

  useEffect(() => {
    if (!state || busy || error) return
    const jobs = [state.study, ...Object.values(state.audio)]
    const cooldowns = jobs.map(job => job.retry_after_seconds).filter(seconds => seconds > 0)
    const delay = jobs.some(pending) ? 950 : cooldowns.length ? 200 + Math.min(...cooldowns) * 1000 : null
    if (delay === null) return
    const timer = window.setTimeout(() => { void refresh() }, delay)
    return () => window.clearTimeout(timer)
  }, [state, busy, error, refresh])

  const pack = state?.content
  const audioFormat = mode === 'video' || mode === 'audiobook' || mode === 'podcast' ? mode : null

  return <section className="theme-materials" aria-labelledby={headingId}>
    <h4 id={headingId}>Materiais do tema</h4>
    {!state && !error && <p role="status">Carregando materiais…</p>}
    {error && <div>
      <p role="alert" className="error">{error}</p>
      <button className="secondary" type="button" disabled={busy} onClick={() => void refresh()}>Consultar situação</button>
    </div>}
    {state && !pack && <GenerateMaterial job={state.study} busy={busy} available={state.text_available}
      consentText="Autorizo o Gemini a usar o conteúdo desta lição para preparar materiais de estudo."
      label="Preparar materiais" unavailable="A geração de materiais está indisponível."
      onGenerate={onSaved => void update(signal => generateTheme(lessonId, state.study.status === 'idle' ? undefined : state.study.attempts, signal), onSaved)}/>}
    {pack && state && <>
      <nav className="theme-format-nav" aria-label="Escolher formato de estudo">
        {formats.map(format => <button key={format.mode} className="secondary" type="button"
          aria-controls={panelId} aria-pressed={mode === format.mode} onClick={() => setMode(format.mode)}>
          {format.label}
        </button>)}
      </nav>
      <div id={panelId} className="theme-panel">
        {audioFormat && <div key={audioFormat} className="theme-media">
          <GenerateMaterial job={state.audio[audioFormat]} busy={busy} available={state.audio_available}
            consentText="Autorizo o envio do roteiro deste material ao Gemini para gerar a narração."
            label={audioFormat === 'podcast' ? 'Gerar podcast com duas vozes' : 'Gerar narração'}
            unavailable="A geração de áudio está indisponível."
            onGenerate={onSaved => void update(signal => generateThemeAudio(
              lessonId, audioFormat, state.audio[audioFormat].status === 'idle' ? undefined : state.audio[audioFormat].attempts, signal,
            ), onSaved)}/>
          <ThemeSegmentPlayer lessonId={lessonId} mode={audioFormat} pack={pack} onAudioError={() => void refresh()}
            recordings={state.audio[audioFormat].status === 'ready' ? state.audio[audioFormat].segments : 0}/>
        </div>}
        {mode === 'map' && <ThemeMap map={pack.map}/>}
        <div hidden={mode !== 'quiz'}>
          <ThemeAssessment lessonId={lessonId} kind="quiz" questions={pack.quiz} onExpired={onExpired}/>
        </div>
        <div hidden={mode !== 'simulation'}>
          <ThemeAssessment lessonId={lessonId} kind="simulation" questions={pack.simulation} onExpired={onExpired}/>
        </div>
      </div>
    </>}
  </section>
}
