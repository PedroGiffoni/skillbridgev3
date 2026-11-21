import { useEffect, useRef, useState } from 'react'
import type { Ref } from 'react'
import { ArrowRight, Camera, Clock3, LockKeyhole, UserRound } from 'lucide-react'
import { ApiError } from './api'
import {
  deleteHistory, getAccount, getGoogleNonce, getHistory, getLoginConfig, openHistory,
  requestCode, signInWithGoogle, updateProfile, verifyCode,
} from './account-api'
import type { AccountDetails, AccountProfile, GoogleLogin, HistoryItem, LoginConfig, SavedAssessment } from './account-api'
import './account.css'

const errorMessage = (err: unknown) => err instanceof Error ? err.message : 'Não foi possível concluir. Tente novamente.'

type GoogleIdentity = {
  accounts: { id: {
    initialize: (options: { client_id: string; nonce: string; callback: (response: { credential: string }) => void }) => void
    renderButton: (element: HTMLElement, options: { theme: string; size: string; text: string; locale: string; width: number }) => void
  } }
}

let googleScript: Promise<GoogleIdentity> | undefined

function googleIdentity() {
  const googleWindow = window as Window & { google?: GoogleIdentity }
  if (googleWindow.google) return Promise.resolve(googleWindow.google)
  googleScript ??= new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    const failed = () => {
      script.remove()
      googleScript = undefined
      reject(new Error('Não foi possível carregar o acesso com Google.'))
    }
    script.addEventListener('load', () => googleWindow.google ? resolve(googleWindow.google) : failed(), { once: true })
    script.addEventListener('error', failed, { once: true })
    document.head.append(script)
  })
  return googleScript
}

function GoogleAccess({ clientId, onLogin }: { clientId: string; onLogin: (result: GoogleLogin) => void }) {
  const holder = useRef<HTMLDivElement>(null)
  const callback = useRef(onLogin)
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { callback.current = onLogin }, [onLogin])
  useEffect(() => {
    const controller = new AbortController()
    const node = holder.current
    if (!node) return () => controller.abort()
    async function prepare() {
      try {
        const google = await googleIdentity()
        if (controller.signal.aborted || !node) return
        const { nonce } = await getGoogleNonce(controller.signal)
        if (controller.signal.aborted) return
        google.accounts.id.initialize({
          client_id: clientId,
          nonce,
          callback: async ({ credential }) => {
            setBusy(true)
            try { callback.current(await signInWithGoogle(credential, controller.signal)) }
            catch (err) { if (!controller.signal.aborted) setError(errorMessage(err)) }
            finally { if (!controller.signal.aborted) setBusy(false) }
          },
        })
        google.accounts.id.renderButton(node, {
          theme: 'outline', size: 'large', text: 'signin_with', locale: 'pt-BR',
          width: Math.min(320, Math.max(190, node.clientWidth)),
        })
      } catch (err) {
        if (!controller.signal.aborted) setError(errorMessage(err))
      }
    }
    void prepare()
    return () => { controller.abort(); node.replaceChildren() }
  }, [clientId, attempt])

  return <div className="google-entry" aria-busy={busy}>
    <div ref={holder} hidden={Boolean(error) || busy} />
    {busy && <p role="status">Confirmando conta Google…</p>}
    {error && <><p className="error" role="alert">{error}</p><button className="secondary" onClick={() => { setError(''); setAttempt(attempt + 1) }}>Tentar Google novamente</button></>}
  </div>
}

type EmailAccessProps = {
  lockedEmail?: string
  linkToken?: string
  linkAccount?: boolean
  onLogin: (account: AccountProfile) => void
}

function EmailAccess({ lockedEmail, linkToken, linkAccount = false, onLogin }: EmailAccessProps) {
  const [email, setEmail] = useState(lockedEmail ?? '')
  const [code, setCode] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function submit(reissue = false) {
    if (controller.current) return
    const current = new AbortController()
    controller.current = current
    setError(''); setBusy(true)
    try {
      if (sent && !reissue) {
        onLogin(await verifyCode(email, code, linkToken, linkAccount, current.signal))
      } else {
        await requestCode(email, linkAccount, current.signal)
        setCode(''); setSent(true)
      }
    } catch (err) { if (!current.signal.aborted) setError(errorMessage(err)) }
    finally {
      if (!current.signal.aborted) setBusy(false)
      controller.current = null
    }
  }

  return <form className="email-access" onSubmit={event => { event.preventDefault(); void submit() }}>
    <label htmlFor="access-email">E-mail</label>
    <input id="access-email" type="email" autoComplete="email" maxLength={254} required
      readOnly={Boolean(lockedEmail) || sent} value={email} onChange={event => setEmail(event.target.value)} />
    {sent && <>
      <p className="privacy-note" role="status">Enviamos um código de 6 dígitos para este e-mail.</p>
      <label htmlFor="access-code">Código de acesso</label>
      <input id="access-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required
        value={code} onChange={event => setCode(event.target.value.replace(/[^0-9]/g, ''))} />
    </>}
    {error && <p className="error" role="alert">{error}</p>}
    <div className="actions">
      <button className="primary" disabled={busy}>
        {busy ? 'Aguarde…' : sent ? 'Confirmar código' : 'Receber código por e-mail'}<ArrowRight size={16} aria-hidden="true" />
      </button>
      {sent && <button className="secondary" type="button" disabled={busy}
        onClick={() => void submit(true)}>Pedir outro código</button>}
      {sent && !lockedEmail && <button className="secondary" type="button" disabled={busy}
        onClick={() => { setSent(false); setCode(''); setError('') }}>Trocar e-mail</button>}
    </div>
  </form>
}

type AccessProps = {
  assessment: boolean
  heading: Ref<HTMLHeadingElement>
  onLogin: (account: AccountProfile) => void
  onBack: () => void
}

export function AccessPanel({ assessment, heading, onLogin, onBack }: AccessProps) {
  const [config, setConfig] = useState<LoginConfig | null>(null)
  const [link, setLink] = useState<{ email: string; link_token: string } | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const callback = useRef(onLogin)
  useEffect(() => { callback.current = onLogin }, [onLogin])
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const account = await getAccount(controller.signal)
        if (controller.signal.aborted) return
        if (account) { callback.current(account); return }
        const next = await getLoginConfig(controller.signal)
        if (!controller.signal.aborted) setConfig(next)
      } catch (err) { if (!controller.signal.aborted) setError(errorMessage(err)) }
    }
    void load()
    return () => controller.abort()
  }, [attempt])

  return <div className="form-card access-card">
    <span className="small-icon"><LockKeyhole size={20} aria-hidden="true" /></span>
    <h1 ref={heading} tabIndex={-1}>{!config && !error ? 'Verificando acesso' : assessment ? 'Entre grátis para ver seu diagnóstico' : 'Acesse suas avaliações'}</h1>
    {config && <p>{assessment
      ? 'Suas respostas estão prontas. Entre para receber seu diagnóstico e sua trilha de estudo. Sua conta é gratuita e guarda os resultados no histórico para você consultar quando quiser.'
      : 'Entre na sua conta gratuita para consultar seu histórico e editar seu perfil.'}</p>}
    {error && <><p role="alert" className="error">{error}</p>
      <button className="secondary" onClick={() => { setError(''); setAttempt(attempt + 1) }}>Tentar novamente</button></>}
    {!config && !error && <p role="status">Verificando seu acesso…</p>}
    {config?.google_client_id && !link && <GoogleAccess clientId={config.google_client_id} onLogin={result => {
      if ('profile' in result) onLogin(result.profile)
      else setLink(result)
    }} />}
    {config?.google_client_id && config.email_enabled && !link && <div className="access-divider">ou</div>}
    {config?.email_enabled && <>
      {link && <p className="notice">Confirme seu e-mail para vincular o Google à conta que já guarda seu histórico.</p>}
      <EmailAccess key={link?.link_token ?? 'entry'} lockedEmail={link?.email} linkToken={link?.link_token} onLogin={onLogin} />
      {link && <button className="secondary access-back" onClick={() => setLink(null)}>Escolher outra forma de entrada</button>}
    </>}
    {config && !config.email_enabled && !config.google_client_id &&
      <p className="notice" role="status">O acesso está indisponível no momento. Tente novamente mais tarde.</p>}
    <button className="secondary access-back" onClick={onBack}>{assessment ? 'Revisar respostas' : 'Voltar ao início'}</button>
  </div>
}

export function HistoryPanel({ heading, onOpen, onExpired }: {
  heading: Ref<HTMLHeadingElement>; onOpen: (entry: SavedAssessment) => void; onExpired: () => void
}) {
  const [items, setItems] = useState<HistoryItem[] | null>(null)
  const [pending, setPending] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const expired = useRef(onExpired)
  useEffect(() => { expired.current = onExpired }, [onExpired])
  useEffect(() => {
    const controller = new AbortController()
    void getHistory(controller.signal).then(result => setItems(result.items)).catch(err => {
      if (controller.signal.aborted) return
      if (err instanceof ApiError && err.status === 401) expired.current()
      else setError(errorMessage(err))
    })
    return () => controller.abort()
  }, [attempt])

  async function open(id: string) {
    setBusy(true); setError('')
    try { onOpen(await openHistory(id)) }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) expired.current()
      else setError(errorMessage(err))
    }
    finally { setBusy(false) }
  }

  async function remove(id: string) {
    setBusy(true); setError('')
    try { await deleteHistory(id); setItems(current => current?.filter(item => item.id !== id) ?? []); setPending('') }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) expired.current()
      else setError(errorMessage(err))
    }
    finally { setBusy(false) }
  }

  return <div className="form-card">
    <span className="small-icon"><Clock3 size={20} aria-hidden="true" /></span>
    <h1 ref={heading} tabIndex={-1}>Meu histórico</h1>
    <p>Retome o diagnóstico e a trilha de uma avaliação salva.</p>
    {error && <><p className="error" role="alert">{error}</p>
      <button className="secondary" onClick={() => { setError(''); setAttempt(attempt + 1) }}>Recarregar histórico</button></>}
    {!items && !error && <p role="status">Carregando avaliações…</p>}
    {items?.length === 0 && <p className="notice">Seu primeiro diagnóstico aparecerá aqui quando você concluir uma avaliação.</p>}
    {items && items.length > 0 && <ul className="history-list">{items.map(item => <li key={item.id}>
      <div><strong>{item.profession}</strong><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleDateString('pt-BR')}</time></div>
      {pending === item.id ? <div className="history-actions">
        <span>Excluir esta avaliação?</span>
        <button className="secondary" disabled={busy} onClick={() => setPending('')}>Cancelar</button>
        <button className="primary" disabled={busy} onClick={() => void remove(item.id)}>Confirmar exclusão</button>
      </div> : <div className="history-actions">
        <button className="secondary" disabled={busy} onClick={() => setPending(item.id)}>Excluir</button>
        <button className="primary" disabled={busy} onClick={() => void open(item.id)}>Abrir diagnóstico</button>
      </div>}
    </li>)}</ul>}
  </div>
}

async function makePhoto(file: File): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
    throw new Error('Selecione uma imagem JPG, PNG ou WebP de até 8 MB.')
  }
  const image = await createImageBitmap(file)
  try {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 192
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Não foi possível preparar a foto.')
    const edge = Math.min(image.width, image.height)
    context.fillStyle = '#f0f1f7'
    context.fillRect(0, 0, 192, 192)
    context.drawImage(image, (image.width - edge) / 2, (image.height - edge) / 2, edge, edge, 0, 0, 192, 192)
    return canvas.toDataURL('image/jpeg', 0.8)
  } finally { image.close() }
}

export function ProfilePanel({ profile, heading, onChange, onExpired }: {
  profile: AccountProfile; heading: Ref<HTMLHeadingElement>; onChange: (profile: AccountProfile) => void; onExpired: () => void
}) {
  const [details, setDetails] = useState<AccountDetails>({
    display_name: profile.display_name, photo: profile.photo, course: profile.course,
    semester: profile.semester, goal: profile.goal,
  })
  const [busy, setBusy] = useState(false)
  const [imageBusy, setImageBusy] = useState(false)
  const [link, setLink] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  async function choosePhoto(file?: File) {
    if (!file) return
    setError(''); setImageBusy(true)
    try { const photo = await makePhoto(file); setDetails(current => ({ ...current, photo })) }
    catch (err) { setError(errorMessage(err)) }
    finally { setImageBusy(false) }
  }

  async function save() {
    setBusy(true); setStatus(''); setError('')
    try { onChange(await updateProfile(details)); setStatus('Perfil salvo.') }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) onExpired()
      else setError(errorMessage(err))
    } finally { setBusy(false) }
  }

  return <div className="form-card">
    <h1 ref={heading} tabIndex={-1}>Meu perfil</h1>
    <p>Adicione uma foto e as informações que quiser guardar na sua conta.</p>
    {profile.email && <p className="privacy-note">E-mail de acesso: {profile.email}</p>}
    {!profile.email && <button className="secondary" onClick={() => setLink(!link)}>{link ? 'Cancelar vinculação' : 'Vincular e-mail para entrar com código'}</button>}
    {!profile.email && link && <EmailAccess linkAccount onLogin={account => { onChange(account); setLink(false); setStatus('E-mail vinculado.') }} />}
    <form onSubmit={event => { event.preventDefault(); void save() }}>
      <div className="profile-photo">
        {details.photo ? <img className="profile-avatar" src={details.photo} alt="Sua foto de perfil" width="72" height="72" /> :
          <span className="profile-avatar" aria-hidden="true"><UserRound size={30} /></span>}
        <div>
          <label htmlFor="profile-photo"><Camera size={15} aria-hidden="true" /> Foto de perfil</label>
          <input id="profile-photo" type="file" accept="image/jpeg,image/png,image/webp" disabled={imageBusy || busy}
            onChange={event => { void choosePhoto(event.target.files?.[0]); event.target.value = '' }} />
        </div>
        {details.photo && <button type="button" className="secondary" disabled={imageBusy || busy}
          onClick={() => setDetails({ ...details, photo: null })}>Remover foto</button>}
      </div>
      <label htmlFor="display-name">Nome de exibição</label>
      <input id="display-name" autoComplete="nickname" maxLength={80} value={details.display_name}
        onChange={event => setDetails({ ...details, display_name: event.target.value })} />
      <div className="grid md:grid-cols-2 gap-5">
        <div><label htmlFor="profile-course">Curso universitário</label><input id="profile-course" maxLength={100}
          value={details.course} onChange={event => setDetails({ ...details, course: event.target.value })} /></div>
        <div><label htmlFor="profile-semester">Semestre</label><input id="profile-semester" type="number" min={1} max={20}
          value={details.semester ?? ''} onChange={event => setDetails({ ...details, semester: event.target.value ? Number(event.target.value) : null })} /></div>
      </div>
      <label htmlFor="profile-goal">Objetivo profissional</label>
      <textarea id="profile-goal" maxLength={240} value={details.goal}
        onChange={event => setDetails({ ...details, goal: event.target.value })} />
      {error && <p className="error" role="alert">{error}</p>}
      {status && <p className="notice" role="status">{status}</p>}
      <button className="primary profile-save" disabled={busy || imageBusy}>{busy ? 'Salvando…' : 'Salvar perfil'}</button>
    </form>
  </div>
}
