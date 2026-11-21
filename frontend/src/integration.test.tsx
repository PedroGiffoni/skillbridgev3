import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { mockAssessment, mockAssessmentV3, mockQuestionnaire } from './test-fixtures'

afterEach(() => { cleanup(); sessionStorage.clear(); vi.unstubAllGlobals() })

const designCareer = 'Design de Produto Digital (UX/UI)'

async function fillProfile() {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Escolher minha carreira' }))
  await user.click(screen.getByRole('button', { name: 'Escolha uma carreira' }))
  await user.type(screen.getByRole('searchbox', { name: 'Buscar carreira' }), 'UX UI')
  await user.click(screen.getByRole('button', { name: designCareer }))
  await user.click(screen.getByRole('checkbox'))
  return user
}

test('envia apenas uma carreira confirmada no catálogo para iniciar a avaliação', async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, json: async () => mockQuestionnaire('Análise de Dados') }))
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Escolher minha carreira' }))
  await user.click(screen.getByRole('checkbox'))
  await user.click(screen.getByRole('button', { name: 'Escolha uma carreira' }))
  await user.type(screen.getByRole('searchbox', { name: 'Buscar carreira' }), 'analise de dados')
  await user.click(screen.getByRole('button', { name: 'Começar autoavaliação' }))
  expect(fetchMock).not.toHaveBeenCalled()
  expect(screen.getByRole('alert')).toHaveTextContent('Selecione uma carreira')
  await user.click(screen.getByRole('button', { name: 'Análise de Dados' }))
  await user.click(screen.getByRole('button', { name: 'Começar autoavaliação' }))
  await screen.findByRole('heading', { name: 'Comunicação' })
  expect(fetchMock).toHaveBeenCalledWith('/api/questionnaire', expect.objectContaining({
    body: expect.stringContaining('"profession":"Análise de Dados"'),
  }))
})

test('fluxo API preserva respostas após falha da IA e repete diagnóstico sem fallback', async () => {
  const q = { ...mockQuestionnaire(designCareer), source_mode: 'gemini' as const, token: 'signed-token', notice: 'Questionário de teste via API.' }
  q.competencies[0] = { ...q.competencies[0], name: 'Pesquisa de interfaces', expected_level: 2 }
  q.competencies[0].options[1].label = 'Sigo um exemplo de pesquisa e preciso de ajuda para interpretar o que observei.'
  const result = { ...mockAssessmentV3(q, Array(8).fill(1)), source_mode: 'gemini' as const, summary: 'Resumo de teste recebido do servidor.', notice: 'Orientação de teste via API.' }
  result.weeks[0].title = 'Investigar necessidades de usuários'
  const account = { email: 'ana@example.com', display_name: '', photo: null, course: '', semester: null, goal: '' }
  const assessments: string[] = []
  const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
    const json = (data: unknown) => ({ ok: true, json: async () => data })
    switch (url) {
      case '/api/questionnaire': return json(q)
      case '/api/account': return { ok: false, status: 401 }
      case '/api/auth/config': return json({ email_enabled: true, google_client_id: null })
      case '/api/auth/email/request': return { ok: true, status: 204 }
      case '/api/auth/email/verify': return json(account)
      case '/api/assessment':
        assessments.push(String(init.body))
        return assessments.length === 1 ? { ok: false, status: 503 } : json(result)
      default: throw new Error('Rota inesperada')
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  const initial = render(<App />)
  const user = await fillProfile()
  expect(fetchMock).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: /Começar autoavaliação/ }))
  expect(await screen.findByRole('heading', { name: 'Pesquisa de interfaces' })).toBeVisible()
  expect(screen.getByRole('radio', { name: '1 · ' + q.competencies[0].options[1].label })).toBeVisible()
  expect(screen.queryByText('Preciso de bastante apoio')).not.toBeInTheDocument()
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  await user.selectOptions(screen.getByLabelText(/Onde você já praticou/), 'projeto')
  for (let i = 0; i < 8; i++) {
    expect(screen.getByRole('radio', { name: '1 · ' + q.competencies[i].options[1].label })).toBeVisible()
    await user.click(screen.getByRole('radio', { name: /^1 ·/ }))
    await user.click(screen.getByRole('button', { name: i === 7 ? /^Continuar para contexto$/ : /Próxima pergunta/ }))
  }
  expect(screen.getByText('Pergunta 9 de 20')).toBeVisible()
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  await user.click(screen.getByRole('radio', { name: 'Aprender a parte técnica' }))
  await user.click(screen.getByRole('button', { name: 'Próxima pergunta' }))
  await user.click(screen.getByRole('button', { name: 'Voltar' }))
  expect(screen.getByRole('radio', { name: 'Aprender a parte técnica' })).toBeChecked()
  await user.click(screen.getByRole('button', { name: 'Próxima pergunta' }))
  for (let i = 1; i < 12; i++) {
    if (i === 9) await user.click(screen.getByRole('radio', { name: '2 horas por semana' }))
    if (i === 11) await user.click(screen.getByRole('radio', { name: 'Concluir uma atividade prática' }))
    await user.click(screen.getByRole('button', { name: i === 11 ? /^Ver diagnóstico$/ : i === 9 ? 'Próxima pergunta' : 'Pular pergunta' }))
  }
  expect(await screen.findByRole('heading', { name: 'Entre grátis para ver seu diagnóstico' })).toBeVisible()
  expect(assessments).toHaveLength(0)
  initial.unmount()
  render(<App />)
  await user.type(await screen.findByLabelText('E-mail'), account.email)
  await user.click(screen.getByRole('button', { name: 'Receber código por e-mail' }))
  await user.type(await screen.findByLabelText('Código de acesso'), '123456')
  await user.click(screen.getByRole('button', { name: 'Confirmar código' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('A IA está indisponível')
  expect(screen.getByRole('radio', { name: 'Concluir uma atividade prática' })).toBeChecked()
  expect(screen.getByText('Pergunta 20 de 20')).toBeVisible()
  expect(screen.queryByText(result.summary)).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /demonstração/i })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Tentar diagnóstico novamente' }))
  expect(await screen.findByText(result.summary)).toBeVisible()
  expect(screen.getByText('Seu nível: 1/4 · Referência: 2/4 · Lacuna: 1')).toBeVisible()
  expect(JSON.parse(assessments[0]).answers[0].example).toBe('projeto')
  expect(JSON.parse(assessments[0]).answers[0].self_level).toBe(1)
  expect(JSON.parse(assessments[0]).context).toEqual({
    motivation: 'tecnica', availability: 'duas-horas', goal: 'atividade-pratica',
  })
  expect(JSON.parse(String(fetchMock.mock.calls[0][1].body)).consent).toBe(true)
  expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).not.toHaveProperty('demo')
  expect(JSON.parse(assessments[0])).not.toHaveProperty('demo')
  expect(assessments[1]).toBe(assessments[0])
  screen.getByRole('button', { name: 'Explorar trilha de 12 semanas' }).focus()
  await user.keyboard('{Enter}')
  expect(screen.getByRole('heading', { level: 1 })).toHaveFocus()
  const groups = screen.getAllByRole('region', { name: /Semanas [0-9]+ a [0-9]+/ })
  expect(groups).toHaveLength(3)
  groups.forEach((group, index) => {
    expect(within(group).getAllByRole('heading', { level: 3 }).map(heading => heading.textContent))
      .toEqual(result.weeks.slice(index * 4, index * 4 + 4).map(week => week.title))
  })
  for (const number of [10, 11, 12]) expect(screen.getByText('SEMANA ' + number)).toBeVisible()
  const lastWeek = within(within(groups[2]).getAllByRole('article')[3])
  expect(lastWeek.getByText('60 min')).toBeVisible()
  expect(lastWeek.getByText(result.gaps[3].name)).toBeVisible()
  expect(lastWeek.getByText(result.weeks[11].review)).toBeVisible()
  expect(lastWeek.getByText('Semana 11')).toBeVisible()
})

test('falha de conexão mantém perfil e permite tentar com IA novamente', async () => {
  const fetchMock = vi.fn().mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce({ ok: true, json: async () => mockQuestionnaire(designCareer) })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  const user = await fillProfile()
  await user.click(screen.getByRole('button', { name: /Começar autoavaliação/ }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível conectar')
  expect(screen.getByRole('button', { name: designCareer })).toBeVisible()
  expect(screen.getByRole('checkbox')).toBeChecked()
  expect(screen.queryByText(/demonstração/i)).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByRole('heading', { name: 'Comunicação' })).toBeVisible()
  expect(fetchMock).toHaveBeenCalledTimes(2)
  expect(fetchMock.mock.calls[1][1].body).toBe(fetchMock.mock.calls[0][1].body)
})

test('resposta sem perguntas permite nova tentativa e cancelamento ignora resposta tardia', async () => {
  let resolve: (v: unknown) => void = () => {}
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ ...mockQuestionnaire(designCareer), clarification: 'Qual área do design?', competencies: [], token: '' }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  const user = await fillProfile()
  await user.click(screen.getByRole('button', { name: /Começar autoavaliação/ }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível preparar perguntas para esta carreira')
  fetchMock.mockImplementationOnce(() => new Promise(r => { resolve = r }))
  await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(screen.getByText('Preparando suas perguntas…')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Cancelar' }))
  resolve({ ok: true, json: async () => mockQuestionnaire(designCareer) })
  await waitFor(() => expect(screen.getByRole('heading', { name: /Qual carreira de tecnologia/ })).toBeVisible())
})

test('Google abre o histórico e permite editar o perfil sem gerar outro diagnóstico', async () => {
  const q = mockQuestionnaire('Designer')
  const assessment = mockAssessment(q, Array(8).fill(2))
  const item = { id: 'saved-assessment', profession: 'Designer', created_at: '2026-11-20T12:00:00Z' }
  let saved = true
  let account = { email: 'ana@example.com', display_name: '', photo: null, course: '', semester: null, goal: '' }
  let googleCallback: (response: { credential: string }) => void = () => {}
  vi.stubGlobal('google', { accounts: { id: {
    initialize: (options: { nonce: string; callback: typeof googleCallback }) => {
      expect(options.nonce).toBe('server-nonce')
      googleCallback = options.callback
    },
    renderButton: (element: HTMLElement) => {
      const button = document.createElement('button')
      button.textContent = 'Entrar com Google'
      button.addEventListener('click', () => googleCallback({ credential: 'offline-credential' }))
      element.append(button)
    },
  } } })
  const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
    const json = (data: unknown) => ({ ok: true, json: async () => data })
    switch (url) {
      case '/api/account': return { ok: false, status: 401 }
      case '/api/auth/config': return json({ email_enabled: false, google_client_id: 'offline.apps.googleusercontent.com' })
      case '/api/auth/google/nonce': return json({ nonce: 'server-nonce' })
      case '/api/auth/google': return json({ profile: account })
      case '/api/history': return json({ items: saved ? [item] : [] })
      case '/api/history/saved-assessment':
        if (init.method === 'DELETE') { saved = false; return { ok: true, status: 204 } }
        return json({ ...item, assessment })
      case '/api/account/profile':
        account = { ...account, ...JSON.parse(String(init.body)) }
        return json(account)
      default: throw new Error('Rota inesperada')
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Minhas avaliações' }))
  await user.click(await screen.findByRole('button', { name: 'Entrar com Google' }))
  await user.click(await screen.findByRole('button', { name: 'Abrir diagnóstico' }))
  expect(await screen.findByText(assessment.summary)).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Explorar trilha de 4 semanas' }))
  expect(screen.getAllByRole('heading', { level: 2 }).map(heading => heading.textContent))
    .toEqual(assessment.weeks.map(week => week.title))
  expect(screen.getAllByText(/SEMANA 0[1-4]/)).toHaveLength(4)
  await user.click(screen.getByRole('button', { name: 'Minhas avaliações' }))
  await user.click(screen.getByRole('button', { name: 'Meu perfil' }))
  await user.type(screen.getByLabelText('Nome de exibição'), 'Ana')
  await user.click(screen.getByRole('button', { name: 'Salvar perfil' }))
  expect(await screen.findByText('Perfil salvo.')).toBeVisible()
  expect(account.display_name).toBe('Ana')
  await user.click(screen.getByRole('button', { name: 'Meu histórico' }))
  await user.click(await screen.findByRole('button', { name: 'Excluir' }))
  await user.click(screen.getByRole('button', { name: 'Confirmar exclusão' }))
  expect(await screen.findByText(/Seu primeiro diagnóstico aparecerá aqui/)).toBeVisible()
  expect(fetchMock.mock.calls.some(([url]) => url === '/api/assessment')).toBe(false)
})

test('rascunho antigo pode ser retomado sem selecionar outra carreira', async () => {
  const q = mockQuestionnaire('Designer')
  sessionStorage.setItem('skillbridge-draft-v1', JSON.stringify({
    expiresAt: Date.now() + 60_000, questionnaire: q, profession: q.profession, course: '', semester: '',
    answers: Array(8).fill(2), examples: ['Texto livre antigo', ...Array(7).fill('')],
    context: { motivation: 'Uma resposta aberta antiga', availability: 'duas-horas' }, consent: true,
  }))
  render(<App />)
  expect(screen.getByRole('heading', { name: q.competencies[0].name })).toBeVisible()
  expect(screen.getByText(/As perguntas foram atualizadas/)).toBeVisible()
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Voltar' }))
  await user.click(screen.getByRole('button', { name: 'Retomar questionário' }))
  expect(screen.getByRole('radio', { name: /^2 ·/ })).toBeChecked()
  expect(screen.getByLabelText(/Onde você já praticou/)).toHaveValue('')
})
