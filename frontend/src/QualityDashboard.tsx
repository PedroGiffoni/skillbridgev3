import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, RefObject } from 'react'
import { ApiError } from './api'
import { readQuality, reportLabels, submitContentReport } from './quality-api'
import type { QualityFilters, QualitySnapshot, ReportCategory } from './quality-api'
import './quality.css'

const initialFilters: QualityFilters = { windowDays: 30, model: '', promptVersion: '', career: '' }
const statusLabels = {
  queued: 'Na fila',
  running: 'Em execução',
  ready: 'Prontos',
  failed: 'Falharam',
  needs_review: 'Em revisão',
}
const failureLabels = {
  quota: 'Cota ou limite de solicitações',
  provider_503: 'Gemini indisponível (503)',
  unavailable: 'Outras indisponibilidades',
  timeout: 'Tempo limite excedido',
  invalid_response: 'Resposta rejeitada',
  other: 'Outras falhas',
}
const number = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 })
const percent = new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 })
const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD' })

function SummaryValue({ title, value, detail }: { title: string; value: string; detail?: string }) {
  return <div className="quality-value">
    <dt>{title}</dt>
    <dd><strong>{value}</strong>{detail && <small>{detail}</small>}</dd>
  </div>
}

function Counts<K extends string>({ labels, values, hidden }: {
  labels: Record<K, string>
  values: Record<K, number | null>
  hidden?: string
}) {
  return <dl className="quality-counts">
    {(Object.keys(labels) as K[]).map(key => {
      const count = values[key]
      return <div key={key}>
        <dt>{labels[key]}</dt>
        <dd>{count === null ? hidden : number.format(count)}</dd>
      </div>
    })}
  </dl>
}

function GenerationSummary({ generation }: { generation: QualitySnapshot['generation'] }) {
  const { total, by_status, failures, rejection_rate, latency_ms, input_tokens, output_tokens, cost_usd } = generation
  if (generation.restricted) return <p>Os dados desta carreira ainda são insuficientes para exibição.</p>
  if (!total || !by_status || !failures) return <p>Nenhuma geração registrada para estes filtros.</p>
  return <>
    <dl className="quality-kpis">
      <SummaryValue title="Gerações registradas" value={number.format(total)}/>
      <SummaryValue title="Taxa de rejeição" value={rejection_rate === null ? 'Sem dados' : percent.format(rejection_rate)}
        detail="Entre gerações encerradas"/>
      <SummaryValue title="Tempo médio" value={latency_ms ? number.format(latency_ms.average / 1000) + ' s' : 'Sem dados'}
        detail={latency_ms ? number.format(latency_ms.samples) + ' medições' : undefined}/>
      <SummaryValue title="Custo informado" value={cost_usd === null ? 'Sem dados' : currency.format(cost_usd)}/>
    </dl>
    <div className="quality-details">
      <section>
        <h3>Por estado atual</h3>
        <Counts labels={statusLabels} values={by_status}/>
      </section>
      <section>
        <h3>Motivos de falha</h3>
        <Counts labels={failureLabels} values={failures}/>
      </section>
      <section>
        <h3>Tokens informados</h3>
        <dl className="quality-kpis">
          <SummaryValue title="Entrada" value={input_tokens ? number.format(input_tokens.total) : 'Sem dados'}
            detail={input_tokens ? number.format(input_tokens.samples) + ' medições' : undefined}/>
          <SummaryValue title="Saída" value={output_tokens ? number.format(output_tokens.total) : 'Sem dados'}
            detail={output_tokens ? number.format(output_tokens.samples) + ' medições' : undefined}/>
        </dl>
      </section>
    </div>
    <p className="quality-note">A contagem usa o estado atual de cada geração registrada no período.</p>
  </>
}

type DashboardProps = {
  heading: RefObject<HTMLHeadingElement | null>
  onExpired: () => void
}

export function QualityDashboard({ heading, onExpired }: DashboardProps) {
  const [draft, setDraft] = useState(initialFilters)
  const [filters, setFilters] = useState(initialFilters)
  const [data, setData] = useState<QualitySnapshot | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const onExpiredRef = useRef(onExpired)

  useEffect(() => { onExpiredRef.current = onExpired }, [onExpired])
  const load = useCallback(async (signal: AbortSignal) => {
    setBusy(true)
    setError('')
    try {
      const snapshot = await readQuality(filters, signal)
      if (!signal.aborted) setData(snapshot)
    } catch (err) {
      if (signal.aborted) return
      if (err instanceof ApiError && err.status === 401) onExpiredRef.current()
      else setError(err instanceof Error ? err.message : 'Não foi possível carregar o painel.')
    } finally {
      if (!signal.aborted) setBusy(false)
    }
  }, [filters])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFilters({ ...draft })
  }
  const progressLabels = { learners: 'Pessoas com progresso', lessons_completed: 'Lições concluídas', modules_mastered: 'Módulos dominados' }
  return <div className="quality-dashboard">
    <h1 ref={heading} tabIndex={-1}>Qualidade e operações</h1>
    {data && <form className="result-card quality-filters" onSubmit={submit}>
      <label>Período
        <select value={draft.windowDays} onChange={event => setDraft({ ...draft, windowDays: Number(event.currentTarget.value) })}>
          <option value={7}>Últimos 7 dias</option><option value={30}>Últimos 30 dias</option><option value={90}>Últimos 90 dias</option>
        </select>
      </label>
      <label>Carreira
        <select value={draft.career} onChange={event => setDraft({ ...draft, career: event.currentTarget.value })}>
          <option value="">Todas</option>
          {data.careers.map(career => <option key={career} value={career}>{career}</option>)}
        </select>
      </label>
      <label>Modelo de geração
        <select value={draft.model} onChange={event => setDraft({ ...draft, model: event.currentTarget.value })}>
          <option value="">Todos</option>
          {draft.model && !data.models.includes(draft.model) && <option value={draft.model}>{draft.model}</option>}
          {data.models.map(model => <option key={model} value={model}>{model}</option>)}
        </select>
      </label>
      <label>Versão do prompt de geração
        <select value={draft.promptVersion} onChange={event => setDraft({ ...draft, promptVersion: event.currentTarget.value })}>
          <option value="">Todas</option>
          {draft.promptVersion && !data.prompt_versions.includes(Number(draft.promptVersion)) &&
            <option value={draft.promptVersion}>{draft.promptVersion}</option>}
          {data.prompt_versions.map(version => <option key={version} value={version}>{version}</option>)}
        </select>
      </label>
      <button type="submit" className="primary" disabled={busy}>Aplicar filtros</button>
    </form>}
    {busy && <p role="status">Carregando métricas de qualidade…</p>}
    {error && <>
      <p className="error" role="alert">{error}</p>
      <button className="secondary" onClick={() => setFilters({ ...filters })}>Tentar novamente</button>
    </>}
    {data && !busy && !error && <div className="quality-results" aria-live="polite">
      <section className="result-card">
        <h2>Gerações do Gemini</h2>
        <GenerationSummary generation={data.generation}/>
      </section>
      <section className="result-card">
        <h2>Relatos de conteúdo</h2>
        <Counts labels={reportLabels} values={data.reports} hidden="Dados insuficientes"/>
      </section>
      <section className="result-card">
        <h2>Progresso agregado</h2>
        <Counts labels={progressLabels} values={data.progress} hidden="Dados insuficientes"/>
        <p className="quality-note">Os indicadores de progresso e relatos aparecem a partir de {data.privacy_minimum} contas distintas por grupo.</p>
      </section>
    </div>}
  </div>
}

type ReportProps = { lessonId: string; onExpired: () => void }

function ReportForm({ lessonId, onExpired }: ReportProps) {
  const [expanded, setExpanded] = useState(false)
  const [category, setCategory] = useState<ReportCategory>('accuracy')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const id = useId()
  const request = useRef<AbortController | null>(null)
  const confirmation = useRef<HTMLParagraphElement | null>(null)
  useEffect(() => () => request.current?.abort(), [])
  useEffect(() => { if (saved) confirmation.current?.focus() }, [saved])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (request.current) return
    const controller = new AbortController()
    request.current = controller
    setBusy(true)
    setError('')
    try {
      await submitContentReport(lessonId, category, controller.signal)
      if (!controller.signal.aborted) setSaved(true)
    } catch (err) {
      if (controller.signal.aborted) return
      if (err instanceof ApiError && err.status === 401) onExpired()
      else setError(err instanceof Error ? err.message : 'Não foi possível registrar o relato.')
    } finally {
      if (!controller.signal.aborted) {
        request.current = null
        setBusy(false)
      }
    }
  }

  return <div className="quality-report">
    <button type="button" className="secondary" aria-controls={id} aria-expanded={expanded}
      onClick={() => setExpanded(!expanded)} disabled={busy}>Relatar problema nesta lição</button>
    <div id={id} hidden={!expanded}>
      {saved ? <p ref={confirmation} tabIndex={-1} role="status">Relato registrado. Obrigado por ajudar a melhorar a lição.</p>
        : <form onSubmit={event => { void submit(event) }}>
          <label>Tipo de problema
            <select value={category} onChange={event => setCategory(event.currentTarget.value as ReportCategory)} disabled={busy}>
              {(Object.keys(reportLabels) as ReportCategory[]).map(key => <option key={key} value={key}>{reportLabels[key]}</option>)}
            </select>
          </label>
          {error && <p className="error" role="alert">{error}</p>}
          <button className="primary" type="submit" disabled={busy}>{busy ? 'Registrando…' : 'Registrar relato'}</button>
        </form>}
    </div>
  </div>
}

export function ContentReport(props: ReportProps) {
  return <ReportForm key={props.lessonId} {...props}/>
}
