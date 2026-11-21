import { useCallback, useEffect, useId, useState } from 'react'
import type { FormEvent, RefObject } from 'react'
import { request } from './account-api'
import type { CourseItem } from './course-api'
import { useLearningRequest } from './useLearningRequest'
import './learning-progress.css'

type Week = {
  week: number
  title: string
  planned_minutes: number
  recorded_minutes: number
  lessons_completed: number
  lessons_total: number
  complete: boolean
  mastered_count: number
}
type Competency = {
  id: string
  name: string
  status: 'not_started' | 'studying' | 'review' | 'mastered'
  correct: number
  total: number
}
type DashboardModule = {
  id: string
  title: string
  objective: string
  weeks: number[]
  competency_ids?: string[]
  prerequisites: { id: string; title: string; satisfied?: boolean }[]
  status: 'locked' | 'open' | 'mastered'
  lessons_completed: number
  lessons_total: number
  latest_score: number | null
  reinforcement: { outline_id: string; title: string }[]
}
type Dashboard = {
  courses: CourseItem[]
  course: CourseItem | null
  plan_revision: number | null
  xp: number
  achievements: string[]
  weeks: Week[]
  competencies: Competency[]
  modules: DashboardModule[]
  next_lesson: { outline_id: string; title: string } | null
}

const competencyStatus = {
  not_started: 'Não iniciada', studying: 'Em estudo', review: 'Em revisão', mastered: 'Dominada',
}
const moduleStatus = { locked: 'Bloqueado', open: 'Liberado', mastered: 'Aprovado' }
const dashboardPath = '/api/me/dashboard'
type ModuleFilter = 'all' | DashboardModule['status']

function duration(minutes: number) {
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  if (hours === 0) return remainder + ' min'
  if (remainder === 0) return hours + ' h'
  return hours + ' h ' + remainder + ' min'
}

function Summary({ dashboard }: { dashboard: Dashboard }) {
  const complete = dashboard.weeks.filter(week => week.complete).length
  const mastered = dashboard.competencies.filter(competency => competency.status === 'mastered').length
  const lessons = dashboard.weeks.reduce((count, week) => count + week.lessons_completed, 0)
  const totalLessons = dashboard.weeks.reduce((count, week) => count + week.lessons_total, 0)
  const planned = dashboard.weeks.reduce((minutes, week) => minutes + week.planned_minutes, 0)
  const recorded = dashboard.weeks.reduce((minutes, week) => minutes + week.recorded_minutes, 0)
  const stats = [
    { label: 'Semanas concluídas', value: complete + ' / ' + dashboard.weeks.length },
    { label: 'Lições concluídas', value: lessons + ' / ' + totalLessons },
    { label: 'Competências dominadas', value: mastered + ' / ' + dashboard.competencies.length },
    { label: 'XP acumulado', value: String(dashboard.xp) },
  ]
  return <section aria-label="Resumo do progresso">
    <dl className="learning-kpis">
      {stats.map(stat => <div className="result-card" key={stat.label}>
        <dt>{stat.label}</dt><dd>{stat.value}</dd>
      </div>)}
    </dl>
    <p className="learning-effort"><strong>Esforço</strong> · {duration(planned)} planejados e {duration(recorded)} registrados.</p>
    {dashboard.achievements.length > 0 && <div className="learning-achievements">
      <h2>Conquistas</h2>
      <ul>{dashboard.achievements.map(achievement => <li key={achievement}>{achievement}</li>)}</ul>
    </div>}
  </section>
}

function MasteryChart({ weeks, targets }: { weeks: Week[]; targets: number }) {
  const chartId = useId()
  if (!weeks.length || !targets) return null
  return <section className="result-card learning-chart" aria-labelledby={chartId}>
    <h2 id={chartId}>Evolução de domínio</h2>
    <p>Competências dominadas acumuladas por semana. A última semana inclui aprovações posteriores.</p>
    <ol className="learning-chart-bars" aria-hidden="true">
      {weeks.map(week => <li key={week.week}>
        <div className="learning-chart-track">
          <span style={{ height: Math.min(100, week.mastered_count / targets * 100) + '%' }}/>
        </div>
        <span>{week.week}</span>
      </li>)}
    </ol>
    <details className="learning-chart-text">
      <summary>Valores da evolução por semana</summary>
      <ol>{weeks.map(week => <li key={week.week}>
        Semana {week.week} · {week.mastered_count} de {targets} competências dominadas
      </li>)}</ol>
    </details>
  </section>
}

function CompetencyMatrix({ competencies }: { competencies: Competency[] }) {
  const title = useId()
  const missed = competencies.filter(competency => competency.total > competency.correct)
  return <section className="result-card" aria-labelledby={title}>
    <h2 id={title}>Competências</h2>
    {competencies.length === 0 && <p>Este curso ainda está sem dados de competências.</p>}
    <ul className="learning-matrix">
      {competencies.map(competency => <li key={competency.id}>
        <div><strong>{competency.name}</strong><span className="learning-state">{competencyStatus[competency.status]}</span></div>
        <span>{competency.total ? competency.correct + ' de ' + competency.total + ' acertos' : 'Sem avaliação registrada'}</span>
      </li>)}
    </ul>
    {missed.length > 0 && <details className="learning-review">
      <summary>Revisão de erros por competência</summary>
      <ul>{missed.map(competency => <li key={competency.id}>
        {competency.name} · {competency.total - competency.correct} de {competency.total} questões para revisar
      </li>)}</ul>
    </details>}
  </section>
}

function validatedMinutes(value: string, minimum: number, maximum: number) {
  const number = Number(value)
  return value.trim() !== '' && Number.isInteger(number) && number >= minimum && number <= maximum ? number : null
}

function MinutesInput({ week, busy, onSave }: { week: Week; busy: boolean; onSave: (week: number, minutes: number) => void }) {
  const field = useId()
  const [minutes, setMinutes] = useState(String(week.recorded_minutes))
  const numeric = validatedMinutes(minutes, 0, 1440)

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (numeric !== null && !busy) onSave(week.week, numeric)
  }

  return <form className="learning-time-form" onSubmit={save}>
    <label htmlFor={field}>Minutos estudados na semana</label>
    <input id={field} type="number" inputMode="numeric" min={0} max={1440} step={1} required value={minutes}
      disabled={busy} onChange={event => setMinutes(event.target.value)}/>
    <button className="primary" type="submit" disabled={numeric === null || busy}>{busy ? 'Salvando…' : 'Salvar tempo'}</button>
  </form>
}

function TimeEditor({ weeks, busy, onSave }: {
  weeks: Week[]
  busy: boolean
  onSave: (week: number, minutes: number) => void
}) {
  const title = useId()
  const field = useId()
  const [selected, setSelected] = useState<number | null>(null)
  const week = weeks.find(item => item.week === selected) ?? weeks.find(item => !item.complete) ?? weeks[0]
  if (!week) return null
  return <section className="result-card learning-time" aria-labelledby={title}>
    <h2 id={title}>Registrar tempo de estudo</h2>
    <p>Informe o total que você estudou na semana escolhida. Você pode atualizar esse valor depois.</p>
    <div className="learning-time-controls">
      <label htmlFor={field}>Semana para registrar</label>
      <select id={field} value={week.week} disabled={busy} onChange={event => setSelected(Number(event.target.value))}>
        {weeks.map(item => <option key={item.week} value={item.week}>Semana {item.week}</option>)}
      </select>
      <MinutesInput key={week.week + '-' + week.recorded_minutes} week={week} busy={busy} onSave={onSave}/>
    </div>
  </section>
}

function ReplanEditor({ plannedMinutes, busy, onReplan }: {
  plannedMinutes: number
  busy: boolean
  onReplan: (minutes: number) => void
}) {
  const field = useId()
  const [minutes, setMinutes] = useState(String(plannedMinutes))
  const numeric = validatedMinutes(minutes, 1, 240)

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (numeric !== null && !busy) onReplan(numeric)
  }

  return <details className="result-card learning-replan">
    <summary>Replanejar semanas em aberto</summary>
    <p>Informe o novo tempo estimado por semana. As semanas concluídas mantêm o planejamento salvo.</p>
    <form className="learning-time-form" onSubmit={save}>
      <label htmlFor={field}>Minutos planejados por semana</label>
      <input id={field} type="number" inputMode="numeric" min={1} max={240} step={1} required value={minutes}
        disabled={busy} onChange={event => setMinutes(event.target.value)}/>
      <button className="primary" type="submit" disabled={numeric === null || busy}>Salvar planejamento</button>
    </form>
  </details>
}

function WeekCards({ weeks }: { weeks: Week[] }) {
  const title = useId()
  return <section aria-labelledby={title}>
    <h2 id={title}>As semanas da trilha</h2>
    {!weeks.length && <p>O planejamento semanal ainda não está disponível.</p>}
    <ol className="learning-weeks">
      {weeks.map(week => <li className="result-card" key={week.week}>
        <div className="learning-week-top">
          <span>Semana {week.week}</span>
          <span className="learning-state">{week.complete ? 'Concluída' : week.lessons_completed ? 'Em andamento' : 'Em aberto'}</span>
        </div>
        <h3>{week.title}</h3>
        {week.lessons_total > 0 && <progress value={week.lessons_completed} max={week.lessons_total}
          aria-label={'Lições concluídas da semana ' + week.week}/>}
        <p>{week.lessons_completed} de {week.lessons_total} lições concluídas.</p>
        <p>{duration(week.planned_minutes)} planejados · {duration(week.recorded_minutes)} registrados.</p>
      </li>)}
    </ol>
  </section>
}

function ModuleMap({ modules, competencies, onReview }: {
  modules: DashboardModule[]; competencies: Competency[]; onReview: (outlineId: string) => void
}) {
  const title = useId()
  const filterId = useId()
  const weekId = useId()
  const competencyId = useId()
  const [competency, setCompetency] = useState('')
  const [filter, setFilter] = useState<ModuleFilter>('all')
  const [week, setWeek] = useState(0)
  const weeks = [...new Set(modules.flatMap(module => module.weeks))].sort((a, b) => a - b)
  const visible = modules.filter(module =>
    (filter === 'all' || module.status === filter) && (!week || module.weeks.includes(week)) &&
    (!competency || module.competency_ids?.includes(competency)))

  return <section aria-labelledby={title}>
    <h2 id={title}>Mapa do curso</h2>
    <div className="learning-filters">
      <label htmlFor={filterId}>Estado do módulo</label>
      <select id={filterId} value={filter} onChange={event => setFilter(event.target.value as ModuleFilter)}>
        <option value="all">Todos</option>
        <option value="open">Liberado</option>
        <option value="locked">Bloqueado</option>
        <option value="mastered">Aprovado</option>
      </select>
      <label htmlFor={weekId}>Semana do módulo</label>
      <select id={weekId} value={week} onChange={event => setWeek(Number(event.target.value))}>
        <option value={0}>Todas as semanas</option>
        {weeks.map(value => <option key={value} value={value}>Semana {value}</option>)}
      </select>
      <label htmlFor={competencyId}>Competência do módulo</label>
      <select id={competencyId} value={competency} onChange={event => setCompetency(event.target.value)}>
        <option value="">Todas as competências</option>
        {competencies.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select>
    </div>
    {!visible.length && <p role="status">Nenhum módulo para os filtros selecionados.</p>}
    <ol className="learning-modules">
      {visible.map(module => <li className="result-card" key={module.id}>
        <span className="learning-state">{moduleStatus[module.status]}</span>
        <h3>{module.title}</h3>
        <p>{module.objective}</p>
        <p>{module.weeks.length === 1 ? 'Semana ' : 'Semanas '}{module.weeks.join(', ')} · {module.lessons_completed} de {module.lessons_total} lições concluídas.</p>
        {module.prerequisites.length > 0 && <p>
          <strong>{module.status === 'locked' ? 'Avaliações necessárias ' : 'Pré-requisitos '}</strong>
          {module.prerequisites.filter(item => module.status !== 'locked' || !item.satisfied)
            .map(prerequisite => prerequisite.title).join(', ')}.
        </p>}
        {module.latest_score !== null && <p>Última avaliação · {module.latest_score}%</p>}
        {module.reinforcement.length > 0 && <ul className="mastery-review-list">
          {module.reinforcement.map(lesson => <li key={lesson.outline_id}>
            <button className="secondary" type="button" onClick={() => onReview(lesson.outline_id)}>Revisar {lesson.title}</button>
          </li>)}
        </ul>}
      </li>)}
    </ol>
  </section>
}

export function LearningDashboard({ heading, onExpired, onContinue }: {
  heading: RefObject<HTMLHeadingElement | null>
  onExpired: () => void
  onContinue: (course: CourseItem, outlineId?: string) => void
}) {
  const picker = useId()
  const [selected, setSelected] = useState('')
  const [view, setView] = useState<'progress' | 'modules'>('progress')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [notice, setNotice] = useState('')
  const { busy, error, run } = useLearningRequest(onExpired)

  const load = useCallback(() => run(async signal => {
    const path = selected ? dashboardPath + '?course_id=' + encodeURIComponent(selected) : dashboardPath
    const data = await request<Dashboard>(path, 'GET', undefined, signal)
    if (!signal.aborted) setDashboard(data)
  }), [selected, run])
  useEffect(() => { void load() }, [load])
  useEffect(() => { heading.current?.focus() }, [heading])

  const visible = dashboard && (!selected || dashboard.course?.id === selected) ? dashboard : null
  const course = visible?.course
  const planRevision = visible?.plan_revision ?? null
  const nextOpenWeek = visible?.weeks.find(item => !item.complete)

  function saveTime(week: number, minutes: number) {
    if (!course || busy) return
    setNotice('')
    void run(async signal => {
      const data = await request<Dashboard>(dashboardPath + '/time', 'POST', {
        course_id: course.id, course_revision: course.revision, week, minutes,
      }, signal)
      if (!signal.aborted) {
        setDashboard(data)
        setNotice('Tempo da semana ' + week + ' salvo.')
      }
    })
  }

  function replan(minutes: number) {
    if (!course || planRevision === null || busy) return
    setNotice('')
    void run(async signal => {
      const path = '/api/study-plans/' + encodeURIComponent(course.plan_id) + '/replan'
      const changed = await request<{ revision: number }>(path, 'POST', {
        expected_revision: planRevision, minutes_per_week: minutes,
      }, signal)
      if (signal.aborted) return
      setDashboard(previous => previous && { ...previous, plan_revision: changed.revision })
      setNotice('Planejamento das semanas em aberto salvo.')
      const data = await request<Dashboard>(dashboardPath + '?course_id=' + encodeURIComponent(course.id),
        'GET', undefined, signal)
      if (!signal.aborted) setDashboard(data)
    })
  }

  return <div className="learning-dashboard">
    <h1 ref={heading} tabIndex={-1}>Meu progresso</h1>
    {Boolean(dashboard?.courses.length) && <div className="learning-course-select">
      <label htmlFor={picker}>Curso em exibição</label>
      <select id={picker} value={selected || dashboard?.course?.id || ''} onChange={event => {
        setSelected(event.target.value)
        setNotice('')
      }}>
        {dashboard?.courses.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
      </select>
    </div>}
    {busy && !visible && <p role="status">Carregando progresso…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {error && <button className="secondary" type="button" disabled={busy} onClick={() => void load()}>Atualizar painel</button>}
    {visible && !course && <p>O progresso aparece quando você tem um curso publicado na sua biblioteca.</p>}
    {visible && course && <>
      <section className="result-card learning-resume">
        <div><h2>{course.title}</h2>{visible.next_lesson && <p>{visible.next_lesson.title}</p>}</div>
        <button className="primary" type="button" onClick={() => onContinue(course, visible.next_lesson?.outline_id)}>
          {visible.next_lesson ? 'Retomar lição' : 'Abrir curso'}
        </button>
      </section>
      <nav className="learning-views" aria-label="Visão de aprendizagem">
        <button className="secondary" type="button" aria-pressed={view === 'progress'} onClick={() => setView('progress')}>Visão geral</button>
        <button className="secondary" type="button" aria-pressed={view === 'modules'} onClick={() => setView('modules')}>Mapa do curso</button>
      </nav>
      {view === 'progress' ? <div className="learning-panels">
        <Summary dashboard={visible}/>
        <MasteryChart weeks={visible.weeks} targets={visible.competencies.length}/>
        <CompetencyMatrix competencies={visible.competencies}/>
        <TimeEditor key={course.id + ':' + course.revision} weeks={visible.weeks} busy={busy} onSave={saveTime}/>
        {nextOpenWeek && planRevision !== null && <ReplanEditor key={course.plan_id + ':' + planRevision + ':' + nextOpenWeek.planned_minutes}
          plannedMinutes={nextOpenWeek.planned_minutes} busy={busy} onReplan={replan}/>}
        {notice && <p role="status">{notice}</p>}
        <WeekCards weeks={visible.weeks}/>
      </div> : <ModuleMap key={course.id + ':' + course.revision} modules={visible.modules} competencies={visible.competencies}
        onReview={outlineId => onContinue(course, outlineId)}/>}
    </>}
  </div>
}