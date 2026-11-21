import { LazyMotion, domAnimation, MotionConfig, useReducedMotion } from 'motion/react'
import * as m from 'motion/react-m'
import { ThemeToggle } from './ThemeToggle'
import { JourneyScene } from './JourneyScene'
import { StudyPlan } from './StudyPlan'
import { CourseLibrary } from './CourseLibrary'
import type { CourseResume } from './CourseLibrary'
import { LearningDashboard } from './LearningDashboard'
import { QualityDashboard } from './QualityDashboard'
import { getAdminAccess } from './quality-api'
import { useEffect, useRef, useState } from 'react'
import { ArrowRight, BookOpen, Check, Compass, GraduationCap, Layers, RotateCcw, ShieldCheck } from 'lucide-react'
import { contextQuestions, practiceOptions } from './context'
import { CareerPicker } from './CareerPicker'
import careerCatalog from './careers.json'
import { ApiError, requestAssessment, requestQuestionnaire } from './api'
import { AccessPanel, HistoryPanel, ProfilePanel } from './AccountPanels'
import { logout } from './account-api'
import type { AccountProfile, SavedAssessment } from './account-api'
import { clearDraft, readDraft, saveDraft } from './assessment-draft'
import type { Assessment, Questionnaire } from './api'

type PrivateScreen = 'history' | 'account' | 'library' | 'dashboard' | 'quality'
type Screen = 'home' | 'profile' | 'questions' | 'context' | 'results' | 'plan' | 'feedback' | 'login' | PrivateScreen
type Destination = 'assessment' | PrivateScreen
const privateScreens = new Set<Screen>(['history', 'account', 'library', 'dashboard', 'quality'])
const steps = ['Sua carreira', 'Autoavaliação', 'Diagnóstico', 'Sua trilha']
const careerLabels = new Set(careerCatalog.groups.flatMap(group => group.careers.map(career => career.label)))
export default function App() {
  const reducedMotion = useReducedMotion()
  const [draft] = useState(readDraft)
  const [screen, setScreen] = useState<Screen>(draft?.needsReview ? 'questions' : draft ? 'login' : 'home')
  const [needsDraftReview, setNeedsDraftReview] = useState(draft?.needsReview ?? false)
  const [destination, setDestination] = useState<Destination>(draft ? 'assessment' : 'history')
  const [account, setAccount] = useState<AccountProfile | null>(null)
  const [libraryPlan, setLibraryPlan] = useState<string | null>(null)
  const [libraryResume, setLibraryResume] = useState<CourseResume | null>(null)
  const [admin, setAdmin] = useState(false)
  useEffect(() => {
    if (screen !== 'dashboard' || !account) return
    const access = new AbortController()
    void getAdminAccess(access.signal).then(result => {
      if (!access.signal.aborted) setAdmin(result.allowed)
    }).catch(() => {
      if (!access.signal.aborted) setAdmin(false)
    })
    return () => access.abort()
  }, [account, screen])
  const [profession, setProfession] = useState(draft?.profession ?? '')
  const [career, setCareer] = useState(draft && careerLabels.has(draft.profession) ? draft.profession : '')
  const [course, setCourse] = useState(draft?.course ?? '')
  const [semester, setSemester] = useState(draft?.semester ?? '')
  const [consent, setConsent] = useState(draft?.consent ?? false)
  const [index, setIndex] = useState(draft && !draft.needsReview ? contextQuestions.length - 1 : 0)
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(draft?.questionnaire ?? null)
  const questionnaireExpiry = useRef(draft?.expiresAt ?? 0)
  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [loading, setLoading] = useState('')
  const [signingOut, setSigningOut] = useState(false)
  const controller = useRef<AbortController | null>(null)
  const competencies = (questionnaire?.competencies ?? []).map(c => ({ ...c, expected: c.expected_level }))
  const [answers, setAnswers] = useState<(number | null)[]>(draft?.answers ?? [])
  const [context, setContext] = useState<Record<string, string>>(draft?.context ?? {})
  const [examples, setExamples] = useState<string[]>(draft?.examples ?? [])
  const [error, setError] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { heading.current?.focus() }, [screen, index])
  const go = (next: Screen) => { setError(''); setScreen(next) }
  useEffect(() => () => controller.current?.abort(), [])
  const cancel = () => { controller.current?.abort(); controller.current = null; setLoading('') }
  const reset = () => {
    clearDraft(); cancel(); setNeedsDraftReview(false); setProfession(''); setCareer(''); setCourse(''); setSemester(''); setConsent(false);
    setIndex(0); setContext({}); setAnswers([]); setExamples([]); setQuestionnaire(null); setAssessment(null); go('home')
  }
  const acceptQuestionnaire = (next: Questionnaire) => {
    if (next.clarification) { setError('Não foi possível preparar perguntas para esta carreira. Tente novamente.'); return }
    clearDraft(); setNeedsDraftReview(false); questionnaireExpiry.current = Date.now() + 60 * 60 * 1000
    setProfession(next.profession); setQuestionnaire(next); setAssessment(null); setContext({}); setIndex(0);
    setAnswers(next.competencies.map(() => null)); setExamples(next.competencies.map(() => ''));
    go('questions')
  }
  const start = async () => {
    if (!careerLabels.has(career)) { setError('Selecione uma carreira da lista para continuar.'); return }
    if (!consent) { setError('Confirme o consentimento para continuar.'); return }
    if (semester && (!Number.isInteger(Number(semester)) || Number(semester) < 1 || Number(semester) > 20)) { setError('Informe um semestre inteiro entre 1 e 20.'); return }
    setError('')
    cancel(); const current = new AbortController(); controller.current = current; setLoading('Preparando suas perguntas…')
    try {
      const next = await requestQuestionnaire({ profession: career, course: course.trim(), semester: semester ? Number(semester) : null, consent }, current.signal)
      if (controller.current === current) acceptQuestionnaire(next)
    } catch (err) { if (controller.current === current) setError(err instanceof Error ? err.message : 'Não foi possível preparar o questionário.') }
    finally { if (controller.current === current) { setLoading(''); controller.current = null } }
  }
  const generateAssessment = async () => {
    if (!questionnaire) return
    setError('')
    cancel()
    const current = new AbortController()
    controller.current = current
    setLoading('Preparando seu diagnóstico e sua trilha…')
    try {
      const next = await requestAssessment({ token: questionnaire.token, context, consent,
        answers: questionnaire.competencies.map((c, i) => ({ competency_id: c.id, self_level: answers[i]!, example: examples[i] })) }, current.signal)
      if (controller.current === current) { clearDraft(); setAssessment(next); go('results') }
    } catch (err) {
      if (controller.current !== current) return
      if (err instanceof ApiError && err.status === 401) {
        setAccount(null); setDestination('assessment'); go('login')
      } else setError(err instanceof Error ? err.message : 'Não foi possível preparar o diagnóstico.')
    } finally {
      if (controller.current === current) { setLoading(''); controller.current = null }
    }
  }
  const finish = () => {
    if (!questionnaire || loading) return
    if (answers.some(answer => answer === null)) { setError('Selecione um nível antes de continuar.'); return }
    saveDraft({ expiresAt: questionnaireExpiry.current, questionnaire, profession, course, semester, consent, answers, examples, context })
    if (account) void generateAssessment()
    else { setDestination('assessment'); go('login') }
  }
  const openPrivate = (page: PrivateScreen) => {
    cancel(); setDestination(page)
    go(account ? page : 'login')
  }
  const acceptAccount = (profile: AccountProfile) => {
    setAccount(profile)
    setAdmin(false)
    if (destination === 'assessment') {
      setIndex(contextQuestions.length - 1); go('context'); void generateAssessment()
    } else go(destination)
  }
  const sessionExpired = () => {
    setAccount(null); setAdmin(false); setLibraryResume(null)
    setDestination(screen === 'account' || screen === 'library' || screen === 'dashboard' ? screen : 'history')
    go('login')
  }
  const viewSaved = (entry: SavedAssessment) => {
    setProfession(entry.profession); setQuestionnaire(null); setAssessment(entry.assessment); go('results')
  }
  const signOut = async () => {
    if (signingOut) return
    setSigningOut(true)
    try { await logout(); setAccount(null); setAdmin(false); setLibraryResume(null); reset() }
    catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível sair. Tente novamente.') }
    finally { setSigningOut(false) }
  }
  const ranked = (assessment?.gaps ?? []).map(g => ({ name: g.name, self: g.self_level, expected: g.expected_level, gap: g.gap })).sort((a, b) => b.gap - a.gap)
  const sourceMode = assessment?.source_mode ?? questionnaire?.source_mode
  const notice = assessment?.notice ?? questionnaire?.notice ?? 'Conheça seu ponto de partida e transforme sua autoavaliação em um plano de desenvolvimento.'
  const journeyScreen = screen !== 'login' && !privateScreens.has(screen)
  const questionCount = competencies.length + contextQuestions.length
  const contextQuestion = contextQuestions[index]
  const step = screen === 'profile' ? 0 : (screen === 'questions' || screen === 'context') ? 1 : screen === 'results' ? 2 : 3
  return <LazyMotion features={domAnimation}><MotionConfig reducedMotion="user"><div className="app-shell">
    <a className="skip" href="#main">Pular para o conteúdo</a>
    <header className="header"><button className="brand" onClick={() => { cancel(); go('home') }} aria-label="SkillBridge, início"><span className="brand-icon"><Layers size={22}/></span>Skill<span>Bridge</span></button><span className="header-note">da universidade ao primeiro emprego</span>{(screen === 'home' || screen === 'results' || screen === 'plan' || screen === 'feedback') && <button className="secondary account-link" onClick={() => openPrivate('history')}>Minhas avaliações</button>}<ThemeToggle/></header>
    <div className="demo-banner" role="status"><ShieldCheck size={16}/><span><strong>{sourceMode === 'gemini' ? 'CONTEÚDO GERADO POR GEMINI · ' : 'AUTOAVALIAÇÃO ORIENTATIVA · '}</strong>{notice}</span></div>
    <main id="main" aria-busy={Boolean(loading)}>{loading && <div className="loading-status" role="status">{loading}<button className="secondary" onClick={cancel}>Cancelar</button></div>}
    {screen === 'home' ? <>
      <section className="hero grid lg:grid-cols-2 gap-12">
        <m.div className="hero-copy" initial={reducedMotion ? false : { opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .55 }}>
          <h1 ref={heading} tabIndex={-1}>Seus primeiros passos <span>em tecnologia</span></h1>
          <p className="intro">Escolha uma carreira de tecnologia, avalie suas competências e receba uma trilha de estudos personalizada para se preparar para seu primeiro estágio ou emprego.</p>
          <button className="primary" onClick={() => go('profile')}>Escolher minha carreira <ArrowRight size={18}/></button>
          <p className="micro"><Check size={15}/> Questionário aberto <span>·</span> 20 perguntas por alternativas</p>
          <div className="audience"><GraduationCap size={23}/><p><strong>Para universitários de qualquer curso</strong> que querem explorar uma carreira em tecnologia.</p></div>
        </m.div>
        <m.div initial={reducedMotion ? false : { opacity: 0, y: 24, rotate: -1 }} animate={{ opacity: 1, y: 0, rotate: -1 }} transition={{ duration: .65, delay: .12 }} className="preview" aria-label="Prévia ilustrativa da jornada">
          <JourneyScene/>
          <div className="preview-top"><span className="small-icon"><Compass size={22}/></span><h2>Exemplo de autoavaliação</h2></div>
          <div className="preview-career"><span>CARREIRA DE INTERESSE</span><strong>Análise de Dados</strong></div>
          <div className="preview-chart" aria-hidden="true"><div><strong>Mapa de competências</strong></div>
            {[['Consultas SQL', 75], ['Visualização', 50], ['Comunicação', 90]].map(([name, value]) => <div className="preview-bar" key={name}><span>{name}</span><div><i style={{ width: `${value}%` }}/></div></div>)}
          </div>
          <div className="preview-bottom"><span className="small-icon"><BookOpen size={22}/></span><div><strong>Trilha de estudos</strong><p>Prática organizada por semana</p></div></div>
        </m.div>
      </section>
      <section className="how">
        <div className="section-heading"><h2>Como funciona</h2></div>
        <div className="grid md:grid-cols-3 gap-5">
          {[
            ['Escolha uma carreira', 'Explore áreas como desenvolvimento, dados, design e cibersegurança.'],
            ['Responda à autoavaliação', 'Marque as opções que mais combinam com sua experiência.'],
            ['Receba seu diagnóstico e sua trilha', 'Veja quais competências priorizar e como praticá-las ao longo da sua trilha.'],
          ].map(([title, description]) => <m.article className="how-card" key={title} initial={reducedMotion ? false : { opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .2 }} transition={{ duration: .3 }}>
            <h3>{title}</h3><p>{description}</p>
          </m.article>)}
        </div>
      </section>
    </> : <m.section key={screen} className="workspace" initial={reducedMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: .25 }}>{journeyScreen && <nav className="steps" aria-label="Etapas da avaliação">{steps.map((s, i) => <span key={s} aria-current={i === step ? 'step' : undefined} className={i <= step ? 'active' : ''}><b>{i < step ? <Check size={14}/> : i + 1}</b>{s}</span>)}</nav>}
      {privateScreens.has(screen) && <nav className="account-navigation" aria-label="Minha conta">
        <button className="secondary" aria-current={screen === 'history' ? 'page' : undefined} onClick={() => openPrivate('history')}>Meu histórico</button>
        <button className="secondary" aria-current={screen === 'account' ? 'page' : undefined} onClick={() => openPrivate('account')}>Meu perfil</button>
        <button className="secondary" aria-current={screen === 'library' ? 'page' : undefined} onClick={() => {
          setLibraryPlan(null); setLibraryResume(null); openPrivate('library')
        }}>Meus cursos</button>
        <button className="secondary" aria-current={screen === 'dashboard' ? 'page' : undefined}
          onClick={() => openPrivate('dashboard')}>Meu desenvolvimento</button>
        {admin && <button className="secondary" aria-current={screen === 'quality' ? 'page' : undefined}
          onClick={() => openPrivate('quality')}>Qualidade e operações</button>}
        <button className="secondary" disabled={signingOut} onClick={() => void signOut()}>{signingOut ? 'Saindo…' : 'Sair da conta'}</button>
      </nav>}
      {!journeyScreen && screen !== 'login' && error && <p className="error" role="alert">{error}</p>}
      {screen === 'login' && <AccessPanel assessment={destination === 'assessment'} heading={heading}
        onLogin={acceptAccount} onBack={() => go(destination === 'assessment' ? 'context' : 'home')} />}
      {screen === 'history' && account && <HistoryPanel heading={heading} onOpen={viewSaved} onExpired={sessionExpired} />}
      {screen === 'library' && account && <CourseLibrary planId={libraryPlan} heading={heading} onExpired={sessionExpired} resume={libraryResume}/>}
      {screen === 'dashboard' && account && <LearningDashboard heading={heading} onExpired={sessionExpired}
        onContinue={(courseItem, outlineId) => {
          setLibraryPlan(null); setLibraryResume({ course: courseItem, outlineId }); openPrivate('library')
        }}/>}
      {screen === 'quality' && account && <QualityDashboard heading={heading} onExpired={sessionExpired}/>}
      {screen === 'account' && account && <ProfilePanel profile={account} heading={heading} onChange={setAccount} onExpired={sessionExpired} />}
      {screen === 'profile' && <div className="form-card">
        <h1 ref={heading} tabIndex={-1}>Qual carreira de tecnologia você quer explorar?</h1>
        <p>Navegue pelas áreas ou digite para encontrar uma carreira.</p>
        {questionnaire && !assessment && <div className="notice">
          <p>Você tem uma autoavaliação em andamento em <strong>{questionnaire.profession}</strong>.</p>
          <button className="secondary" disabled={Boolean(loading)} onClick={() => {
            if (Date.now() >= questionnaireExpiry.current) {
              setError('O questionário anterior expirou. Escolha uma carreira para recomeçar.')
              return
            }
            setIndex(0)
            go('questions')
          }}>Retomar questionário</button>
        </div>}
        <form onSubmit={e => { e.preventDefault(); void start() }}>
          <CareerPicker value={career} disabled={Boolean(loading)} onChange={value => { setCareer(value); setError('') }}/>
          <div className="grid md:grid-cols-2 gap-5">
            <div>
              <label htmlFor="course">Curso <span>(opcional)</span></label>
              <input disabled={Boolean(loading)} id="course" maxLength={100} value={course} onChange={e => setCourse(e.target.value)} placeholder="Seu curso universitário"/>
            </div>
            <div>
              <label htmlFor="semester">Semestre <span>(opcional)</span></label>
              <input disabled={Boolean(loading)} id="semester" type="number" min={1} max={20} value={semester} onChange={e => setSemester(e.target.value)} placeholder="Ex.: 4"/>
            </div>
          </div>
          <div className="notice">O Gemini prepara 8 perguntas de competências para a carreira escolhida. As 12 perguntas de contexto são opcionais. Os níveis sugeridos são estimativas educacionais.</div>
          <label className="checkbox">
            <input disabled={Boolean(loading)} type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} required/>
            <span>Autorizo o processamento da profissão, contexto opcional e respostas para esta avaliação. Esses dados serão enviados ao Google Gemini para gerar o questionário, o diagnóstico e a trilha. No uso gratuito, o Google pode usar entradas e respostas para melhorar seus produtos e permitir revisão humana. Não informarei dados pessoais ou sensíveis nas respostas.</span>
          </label>
          <p className="privacy-note">Uso com IA destinado a maiores de 18 anos. Consulte os <a href="https://ai.google.dev/gemini-api/terms" target="_blank" rel="noreferrer">termos do Gemini</a>. A exclusão local não apaga eventuais dados já processados pelo provedor.</p>
          {error && <p role="alert" className="error">{error}</p>}
          <div className="actions">
            <button type="button" className="secondary" disabled={Boolean(loading)} onClick={() => go('home')}>Voltar</button>
            <button className="primary" disabled={Boolean(loading)}>{error && career ? 'Tentar novamente' : 'Começar autoavaliação'} <ArrowRight size={18}/></button>
          </div>
        </form>
      </div>}
      {screen === 'questions' && <div className="form-card">
        <span className="eyebrow">02 / AUTOAVALIAÇÃO · {profession}</span>
        <div className="progress-label">
          <span>Pergunta {index + 1} de {questionCount}</span>
          <span>{Math.round((index + 1) / questionCount * 100)}%</span>
        </div>
        <progress value={index + 1} max={questionCount} aria-label="Progresso das perguntas"/>
        <h1 ref={heading} tabIndex={-1}>{competencies[index].name}</h1>
        {needsDraftReview && index === 0 &&
          <p className="notice">As perguntas foram atualizadas. Seus níveis estão preservados. Revise as alternativas para continuar.</p>}
        <p>{competencies[index].question}</p>
        <fieldset aria-describedby="answer-help">
          <legend>Qual alternativa mais se aproxima do que você faz hoje?</legend>
          <p id="answer-help" className="answer-help">Considere o que já praticou, inclusive em estudos e projetos. Escolha a descrição mais próxima da sua experiência.</p>
          {competencies[index].options.map(option => <label className={'level' + (answers[index] === option.value ? ' selected' : '')} key={option.value}>
            <input disabled={Boolean(loading)} type="radio" name={'level-' + index} value={option.value} checked={answers[index] === option.value}
              onChange={() => { setAnswers(answers.map((answer, i) => i === index ? option.value : answer)); setError('') }}/>
            <span className="answer-label">{option.value} · {option.label}</span>
          </label>)}
        </fieldset>
        <label htmlFor="practice-context">Onde você já praticou esta competência? <span>(opcional)</span></label>
        <select className="practice-select" id="practice-context" disabled={Boolean(loading)} value={examples[index]}
          onChange={event => setExamples(examples.map((choice, i) => i === index ? event.target.value : choice))}>
          <option value="">Prefiro não responder</option>
          {practiceOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
        {error && <p role="alert" className="error">{error}</p>}
        <div className="actions">
          <button className="secondary" disabled={Boolean(loading)} onClick={() => {
            setError('')
            if (index) setIndex(index - 1)
            else go('profile')
          }}>Voltar</button>
          <button className="primary" disabled={Boolean(loading)} onClick={() => {
            if (answers[index] === null) { setError('Selecione um nível antes de continuar.'); return }
            if (index < competencies.length - 1) { setError(''); setIndex(index + 1) }
            else { setIndex(0); go('context') }
          }}>{index === competencies.length - 1 ? 'Continuar para contexto' : 'Próxima pergunta'}<ArrowRight size={18}/></button>
        </div>
      </div>}
      {screen === 'context' && <div className="form-card">
        <span className="eyebrow">02 / SEU CONTEXTO · {profession}</span>
        <div className="progress-label">
          <span>Pergunta {competencies.length + index + 1} de {questionCount}</span>
          <span>{Math.round((competencies.length + index + 1) / questionCount * 100)}%</span>
        </div>
        <progress value={competencies.length + index + 1} max={questionCount} aria-label="Progresso das perguntas"/>
        <h1 ref={heading} tabIndex={-1}>{contextQuestion.question}</h1>
        <p>Use a alternativa que mais combina com a sua situação. Estas escolhas ajudam a adaptar sua trilha de estudo.</p>
        <fieldset>
          <legend>Escolha uma opção <span>(opcional)</span></legend>
          {[...contextQuestion.options, { value: '', label: 'Prefiro não responder' }].map(option =>
            <label className={'level' + (context[contextQuestion.id] === option.value ? ' selected' : '')} key={option.value}>
              <input type="radio" name={'context-' + contextQuestion.id} value={option.value} disabled={Boolean(loading)}
                checked={context[contextQuestion.id] === option.value}
                onChange={() => { setContext(current => ({ ...current, [contextQuestion.id]: option.value })); setError('') }}/>
              <span className="answer-label">{option.label}</span>
            </label>)}
        </fieldset>
        {error && <p role="alert" className="error">{error}</p>}
        <div className="actions">
          <button className="secondary" disabled={Boolean(loading)} onClick={() => {
            setError('')
            if (index) setIndex(index - 1)
            else { setIndex(competencies.length - 1); go('questions') }
          }}>Voltar</button>
          <button className="primary" disabled={Boolean(loading)} onClick={() => {
            setError('')
            if (index < contextQuestions.length - 1) setIndex(index + 1)
            else finish()
          }}>{index === contextQuestions.length - 1
            ? (error ? 'Tentar diagnóstico novamente' : 'Ver diagnóstico')
            : context[contextQuestion.id] ? 'Próxima pergunta' : 'Pular pergunta'}<ArrowRight size={18}/></button>
        </div>
      </div>}
      {screen === 'results' && assessment && <><span className="eyebrow">03 / DIAGNÓSTICO ORIENTATIVO</span><h1 ref={heading} tabIndex={-1}>Seu ponto de partida, com clareza.</h1><p>Objetivo informado: <strong>{profession}</strong>. Este mapa reflete apenas sua autoavaliação.</p><div className="notice">Referências sugeridas pelo Gemini, por competência. Não é um padrão verificado da profissão. Lacuna = máximo entre 0 e (referência − nível autodeclarado). Não mede aptidão nem certifica habilidades.</div><div className="grid lg:grid-cols-3 gap-6"><div className="result-card lg:col-span-2"><h2>Seu mapa de competências</h2><p>Escala de 0 a 4 · referência estimativa por competência</p>{ranked.map(c => <div className="result-row" key={c.name}><div><strong>{c.name}</strong><span>Seu nível: {c.self}/4 · Referência: {c.expected}/4 · Lacuna: {c.gap}</span></div><meter min={0} max={4} value={c.self} aria-label={`${c.name}: nível ${c.self} de 4`}/></div>)}</div><aside className="result-card priority"><span className="small-icon"><Compass/></span><h2>{ranked[0].gap > 0 ? 'Uma prioridade para explorar' : 'Continue praticando'}</h2><strong>{ranked[0].gap > 0 ? ranked[0].name : 'Aprofunde suas experiências'}</strong><p>{ranked[0].gap > 0 ? 'Esta é a maior diferença em relação à referência didática. Em caso de empate, usamos a ordem do questionário.' : 'Suas respostas atingem a referência didática. Isso não comprova domínio: experimente aplicar e buscar feedback.'}</p><p className="micro">Prioridade baseada na diferença entre seu nível autodeclarado e a referência estimativa, sem julgamento de aptidão.</p></aside></div><div className="result-card guidance"><h2>Um olhar sobre sua autoavaliação</h2><p>{assessment.summary}</p><h3>Pontos fortes autodeclarados</h3>{assessment.strengths.length ? <ul>{assessment.strengths.map(s => <li key={s}>{s}</li>)}</ul> : <p>Continue explorando e praticando suas competências.</p>}<h3>Prioridades para desenvolver</h3>{assessment.priorities.length ? <ul>{assessment.priorities.map(s => <li key={s}>{s}</li>)}</ul> : <p>Experimente aprofundar suas práticas atuais.</p>}<h3>Limites desta orientação</h3><ul>{assessment.limitations.map(s => <li key={s}>{s}</li>)}</ul></div><div className="actions">{questionnaire && <button className="secondary" onClick={() => { setAssessment(null); setIndex(0); go('questions') }}>Revisar respostas</button>}<button className="primary" onClick={() => go('plan')}>Explorar trilha de {assessment.weeks.length} semanas <ArrowRight size={18}/></button></div></>}
      {screen === 'plan' && assessment && <><span className="eyebrow">04 / SUA TRILHA ORIENTATIVA</span><h1 ref={heading} tabIndex={-1}>Pequenas ações. Um caminho possível.</h1><p>Um roteiro gerado pelo Gemini de {assessment.weeks.length} semanas para explorar {ranked[0].gap > 0 ? ranked[0].name.toLocaleLowerCase('pt-BR') : 'uma competência de sua escolha'}. Adapte ao seu tempo e contexto.</p>{assessment.plan_version === 3 && <div className="actions library-entry">
        <button className="primary" onClick={() => { setLibraryPlan(assessment.source_assessment_id); setLibraryResume(null); openPrivate('library') }}>Abrir curso da trilha</button>
      </div>}<StudyPlan assessment={assessment}/><p className="notice">Plano orientativo para explorar {profession}; adapte as ações ao seu contexto e verifique os materiais escolhidos. Não garante certificação ou emprego.</p><div className="actions"><button className="secondary" onClick={() => go('results')}>Voltar ao diagnóstico</button><button className="primary" onClick={() => go('feedback')}>Concluir exploração <Check size={18}/></button></div></>}
      {screen === 'feedback' && <div className="form-card finish"><span className="small-icon"><Check/></span><h1 ref={heading} tabIndex={-1}>Seu próximo passo começa agora.</h1><p>Escolha uma ação da primeira semana, reserve um momento na sua rotina e comece no seu ritmo.</p><div className="notice">Seu diagnóstico e sua trilha estão no histórico da sua conta. Volte quando quiser para rever o resultado.</div><button className="secondary" onClick={() => go('plan')}>Rever trilha</button></div>}
      {(journeyScreen || destination === 'assessment' && screen === 'login') && <button className="reset" onClick={reset}><RotateCcw size={15}/> Reiniciar e apagar respostas da sessão</button>}
    </m.section>}
    </main><footer><span className="brand footer-brand">SkillBridge<span> / </span><small>Conhecer. Desenvolver. Avançar.</small></span><p>Seu desenvolvimento, no seu ritmo.<span>Orientação por autoavaliação, não certificação.</span></p></footer>
  </div></MotionConfig></LazyMotion>
}
