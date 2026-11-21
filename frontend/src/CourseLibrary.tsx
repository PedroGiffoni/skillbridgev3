import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { ApiError } from './api'
import { LessonPlayer } from './LessonPlayer'
import { ModuleAssessment } from './ModuleAssessment'
import { ContentReport } from './QualityDashboard'
import { ThemeMaterials } from './ThemeMaterials'
import {
  createCourse, getCourseJob, getJob, getLesson, listCourses, listLessons, prepareLesson, publishCourse,
} from './course-api'
import type { CourseDraft, CourseItem, CourseJob, Lesson, LessonSlot, LibraryModule } from './course-api'

type Expiry = { onExpired: () => void }
export type CourseResume = { course: CourseItem; outlineId?: string }

function useAction(onExpired: () => void) {
  const current = useRef<AbortController | null>(null)
  const expired = useRef(onExpired)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { expired.current = onExpired }, [onExpired])
  useEffect(() => () => current.current?.abort(), [])
  const run = useCallback(async (task: (signal: AbortSignal) => Promise<void>) => {
    current.current?.abort()
    const controller = new AbortController()
    current.current = controller
    setBusy(true)
    setError('')
    try { await task(controller.signal) }
    catch (err) {
      if (controller.signal.aborted) return
      if (err instanceof ApiError && err.status === 401) expired.current()
      else setError(err instanceof Error ? err.message : 'Não foi possível carregar o conteúdo.')
    } finally {
      if (!controller.signal.aborted) setBusy(false)
    }
  }, [])
  return { run, busy, error }
}

function pending(job: CourseJob | null) {
  return job?.status === 'queued' || job?.status === 'running'
}

function statusText(job: CourseJob) {
  if (job.status === 'queued') return 'Na fila de preparação.'
  if (job.status === 'running') return 'Gemini está preparando o conteúdo.'
  return job.error?.detail ?? 'Conteúdo pronto.'
}

function JobStatus({ job, onChange, onExpired }: Expiry & {
  job: CourseJob; onChange: (job: CourseJob) => void
}) {
  const { run, busy, error } = useAction(onExpired)
  const refresh = useCallback(() => run(async signal => {
    const updated = await getJob(job.id, signal)
    if (!signal.aborted) onChange(updated)
  }), [job.id, onChange, run])
  useEffect(() => {
    if (!pending(job) && !job.retry_after_seconds) return
    const timer = window.setTimeout(() => { void refresh() }, pending(job) ? 900 : job.retry_after_seconds * 1000 + 150)
    return () => window.clearTimeout(timer)
  }, [job, refresh])
  return <div className="library-job">
    <p role="status">{statusText(job)}
      {job.retry_after_seconds > 0 && ' Aguarde ' + job.retry_after_seconds + ' s para tentar de novo.'}
    </p>
    {error && <p className="error" role="alert">{error}</p>}
    {job.status !== 'ready' && <button className="secondary" disabled={busy} onClick={() => void refresh()}>Consultar situação</button>}
  </div>
}

function Consent({ checked, onChange, kind }: {
  checked: boolean; onChange: (checked: boolean) => void; kind: 'course' | 'lesson'
}) {
  return <label className="checkbox">
    <input type="checkbox" checked={checked} onChange={event => onChange(event.currentTarget.checked)} />
    <span>{kind === 'course'
      ? 'Autorizo o Gemini a usar a carreira e os dados pedagógicos da trilha para preparar o curso.'
      : 'Autorizo o Gemini a usar a carreira, o objetivo e as competências desta lição para preparar o conteúdo.'}</span>
  </label>
}

function CourseCreation({ planId, onSaved, onExpired }: Expiry & { planId: string; onSaved: (draft: CourseDraft) => void }) {
  const { run, busy, error } = useAction(onExpired)
  const [job, setJob] = useState<CourseJob | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [consent, setConsent] = useState(false)
  const load = useCallback(() => run(async signal => {
    const result = await getCourseJob(planId, signal)
    if (!signal.aborted) { setJob(result.job); setLoaded(true) }
  }), [planId, run])
  useEffect(() => { void load() }, [load])
  const draft = job?.draft
  const canRequest = loaded && (!job || Boolean(job.error?.retryable))
  const generate = () => run(async signal => {
    const next = await createCourse(planId, job?.attempts, signal)
    if (!signal.aborted) { setJob(next); setConsent(false) }
  })
  return <section className="result-card library-section" aria-labelledby="prepare-course">
    <h2 id="prepare-course">Curso da sua trilha</h2>
    {!loaded && busy && <p role="status">Verificando seu plano de curso…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!loaded && error && <button className="secondary" onClick={() => void load()}>Tentar carregar</button>}
    {job && <JobStatus job={job} onChange={setJob} onExpired={onExpired}/>}
    {draft && <div className="library-row"><strong>{draft.content.title}</strong>
      <button className="primary" disabled={busy} onClick={() => void run(async signal => {
        const saved = await publishCourse(draft, signal)
        if (!signal.aborted) onSaved(saved)
      })}>Salvar na biblioteca</button></div>}
    {canRequest && <>
      <Consent checked={consent} onChange={setConsent} kind="course"/>
      <button className="primary" disabled={!consent || busy || Boolean(job?.retry_after_seconds)}
        onClick={() => void generate()}>{job ? 'Tentar preparar o curso novamente' : 'Preparar plano do curso'}</button>
    </>}
  </section>
}


function LessonMaterialsButton({ lessonId, onExpired }: Expiry & { lessonId: string }) {
  const [open, setOpen] = useState(false)
  const controls = useId()
  return <div className="library-materials">
    <button className="secondary" type="button" aria-expanded={open} aria-controls={controls}
      onClick={() => setOpen(value => !value)}>
      {open ? 'Fechar materiais do tema' : 'Materiais do tema'}
    </button>
    <div id={controls} hidden={!open}>
      {open && <ThemeMaterials lessonId={lessonId} onExpired={onExpired}/>}
    </div>
  </div>
}

function CourseReader({ course, initialOutlineId, onBack, onExpired }: Expiry & {
  course: CourseItem; initialOutlineId?: string; onBack: () => void
}) {
  const { run, busy, error } = useAction(onExpired)
  const [slots, setSlots] = useState<LessonSlot[] | null>(null)
  const [modules, setModules] = useState<LibraryModule[]>([])
  const [examModule, setExamModule] = useState<string | null>(null)
  const examTitle = useRef<HTMLHeadingElement>(null)
  const resume = useRef(initialOutlineId)
  const [selected, setSelected] = useState<string | null>(null)
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [job, setJob] = useState<CourseJob | null>(null)
  const [consent, setConsent] = useState(false)
  const [opened, setOpened] = useState(false)
  const title = useRef<HTMLHeadingElement>(null)
  const selectedTitle = useRef<HTMLHeadingElement>(null)
  const activeSlot = useRef<string | null>(null)
  const load = useCallback(() => run(async signal => {
    const data = await listLessons(course, signal)
    if (!signal.aborted) {
      setSlots(data.items)
      setModules(data.modules ?? [])
    }
  }), [course, run])
  useEffect(() => { title.current?.focus(); void load() }, [load])
  useEffect(() => {
    if (examModule) examTitle.current?.focus()
    else if (selected) selectedTitle.current?.focus()
  }, [examModule, selected])
  const exam = modules.find(module => module.id === examModule && module.status !== 'locked')
  const index = slots?.findIndex(item => item.outline_id === selected) ?? -1
  const active = slots?.[index]
  const previous = slots?.[index - 1]
  const following = slots?.[index + 1]
  const completed = slots?.filter(slot => slot.practice_completed).length ?? 0
  const markCompleted = useCallback((outlineId: string) => {
    setSlots(current => current?.map(slot => slot.outline_id === outlineId
      ? { ...slot, practice_completed: true } : slot) ?? null)
  }, [])
  const updateJob = useCallback((next: CourseJob) => {
    if (activeSlot.current !== selected) return
    setJob(next)
    setSlots(current => current?.map(slot => slot.outline_id === selected
      ? { ...slot, job_id: next.id, lesson_id: next.lesson?.id ?? slot.lesson_id } : slot) ?? null)
  }, [selected])
  const open = useCallback((slot: LessonSlot) => {
    if (slot.locked) return
    setExamModule(null)
    activeSlot.current = slot.outline_id
    setSelected(slot.outline_id)
    setLesson(null)
    setJob(null)
    setConsent(false)
    setOpened(false)
    void run(async signal => {
      const content = slot.lesson_id ? await getLesson(slot.lesson_id, signal) : null
      const currentJob = !slot.lesson_id && slot.job_id ? await getJob(slot.job_id, signal) : null
      if (!signal.aborted) {
        if (content?.practice.completed || currentJob?.lesson?.practice.completed) markCompleted(slot.outline_id)
        setLesson(content)
        setJob(currentJob)
        setOpened(true)
      }
    })
  }, [markCompleted, run])
  useEffect(() => {
    if (!resume.current || !slots) return
    const target = slots.find(slot => slot.outline_id === resume.current)
    resume.current = undefined
    if (target) open(target)
  }, [open, slots])
  const content = lesson ?? job?.lesson
  return <>
    <button className="secondary" onClick={onBack}>Voltar à biblioteca</button>
    <h2 ref={title} tabIndex={-1}>{course.title}</h2>
    {!slots && busy && <p role="status">Carregando lições…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!slots && error && <button className="secondary" onClick={() => void load()}>Tentar carregar</button>}
    {!!slots?.length && <p role="status">{completed} de {slots.length} práticas concluídas</p>}
    {!!modules.length && <details className="course-exams">
      <summary>Avaliações de módulo</summary>
      <ul>
        {modules.map(module => <li key={module.id}>
          <strong>{module.title}</strong>
          {module.status === 'locked' ? <p>Bloqueado. Conclua {module.blocked_by.join(', ')}.</p> :
            <button className="secondary" type="button" aria-pressed={examModule === module.id}
              aria-label={'Avaliação de ' + module.title} onClick={() => setExamModule(module.id)}>
              {module.status === 'mastered' ? 'Ver resultado' : 'Abrir avaliação'}
            </button>}
        </li>)}
      </ul>
    </details>}
    <div className="library-grid">
      <ul className="library-slots" aria-label="Lições do curso">
        {slots?.map(slot => <li key={slot.outline_id}>
          <span>{slot.module_title} · Semana {slot.week}</span>
          <button className="secondary" disabled={slot.locked} aria-pressed={!exam && selected === slot.outline_id}
            onClick={() => !exam && slot.outline_id === selected && opened ? selectedTitle.current?.focus() : open(slot)}>
            {slot.title}
          </button>
          {slot.locked && <span>Bloqueada por pré-requisito</span>}
          {slot.practice_completed && <span>Prática concluída</span>}
        </li>)}
      </ul>
      {exam ? <section className="result-card library-section" aria-labelledby="selected-exam">
        <h3 id="selected-exam" ref={examTitle} tabIndex={-1}>{exam.title}</h3>
        <ModuleAssessment key={exam.id} course={course} moduleId={exam.id} onExpired={onExpired}
          onUnlock={() => void load()} onReview={outlineId => {
            const target = slots?.find(slot => slot.outline_id === outlineId)
            if (target) open(target)
          }}/>
      </section> : active && <section className="result-card library-section" aria-labelledby="selected-lesson">
        <h3 id="selected-lesson" ref={selectedTitle} tabIndex={-1}>{active.title}</h3>
        {!opened && busy && <p role="status">Verificando a lição…</p>}
        {!opened && error && <button className="secondary" onClick={() => open(active)}>Tentar abrir</button>}
        {job && <JobStatus job={job} onChange={updateJob} onExpired={onExpired}/>}
        {content ? <>
          <LessonMaterialsButton key={'materials-' + content.id} lessonId={content.id} onExpired={onExpired}/>
          <ContentReport key={'report-' + content.id} lessonId={content.id} onExpired={onExpired}/>
          <LessonPlayer key={content.id} lesson={content} onExpired={onExpired} onProgress={progress => {
            if (progress.completed && activeSlot.current === active.outline_id) markCompleted(active.outline_id)
          }}/>
        </> : opened && (!job || job.error?.retryable) && <>
          <p>{active.objective}</p>
          <Consent checked={consent} onChange={setConsent} kind="lesson"/>
          <button className="primary" disabled={!consent || busy || Boolean(job?.retry_after_seconds)}
            onClick={() => void run(async signal => {
              const next = await prepareLesson(course, active.outline_id, job?.attempts, signal)
              if (!signal.aborted) { updateJob(next); setConsent(false) }
            })}>{job ? 'Tentar preparar a lição novamente' : 'Preparar esta lição'}</button>
        </>}
        {(previous || following) && <nav className="practice-actions lesson-navigation" aria-label="Navegação entre lições">
          {previous && <button className="secondary" disabled={previous.locked} onClick={() => open(previous)}>Lição anterior</button>}
          {following && <button className="secondary" disabled={following.locked} onClick={() => open(following)}>Próxima lição</button>}
        </nav>}
      </section>}
    </div>
  </>
}

export function CourseLibrary({ planId, heading, onExpired, resume }: Expiry & {
  planId: string | null; heading: RefObject<HTMLHeadingElement | null>; resume?: CourseResume | null
}) {
  const { run, busy, error } = useAction(onExpired)
  const [items, setItems] = useState<CourseItem[] | null>(null)
  const [nextOffset, setNextOffset] = useState<number | null>(null)
  const [selected, setSelected] = useState<CourseItem | null>(() => resume?.course ?? null)
  const load = useCallback((offset: number) => run(async signal => {
    const page = await listCourses(offset, signal)
    if (!signal.aborted) {
      setItems(current => offset ? [...(current ?? []), ...page.items] : page.items)
      setNextOffset(page.next_offset)
    }
  }), [run])
  useEffect(() => { void load(0) }, [load])
  useEffect(() => { if (!selected) heading.current?.focus() }, [heading, selected])
  function saved(draft: CourseDraft) {
    const course = { ...draft, title: draft.content.title }
    setItems(current => [course, ...(current ?? []).filter(item => item.id !== course.id)])
    setSelected(course)
  }
  return <div className="course-library">
    <h1 ref={heading} tabIndex={-1}>Meus cursos</h1>
    {selected ? <CourseReader key={selected.id} course={selected} initialOutlineId={resume?.course.id === selected.id ? resume.outlineId : undefined} onExpired={onExpired} onBack={() => setSelected(null)}/> : <>
      {busy && <p role="status">Carregando a biblioteca…</p>}
      {error && <><p className="error" role="alert">{error}</p><button className="secondary" onClick={() => void load(0)}>Tentar carregar</button></>}
      {planId && items && !items.some(item => item.plan_id === planId) &&
        <CourseCreation key={planId} planId={planId} onSaved={saved} onExpired={onExpired}/>}
      {items?.length === 0 && !planId && <p>Abra uma avaliação de 12 semanas no histórico para preparar seu primeiro curso.</p>}
      {!!items?.length && <ul className="library-courses">
        {items.map(course => <li className="result-card library-row" key={course.id}>
          <div><h2>{course.title}</h2><p>Revisão {course.revision}</p></div>
          <button className="primary" aria-label={'Abrir curso ' + course.title} onClick={() => setSelected(course)}>Abrir curso</button>
        </li>)}
      </ul>}
      {nextOffset !== null && <button className="secondary" disabled={busy} onClick={() => void load(nextOffset)}>Carregar mais cursos</button>}
    </>}
  </div>
}
