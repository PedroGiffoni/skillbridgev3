import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { ThemeMaterials } from './ThemeMaterials'
import type { ThemeJob, ThemePack, ThemeState } from './theme-api'

const root = '/api/lessons/licao/materials'
const idle: ThemeJob = { status: 'idle', attempts: 0, retry_after_seconds: 0, error: null }
const ready: ThemeJob = { ...idle, status: 'ready', attempts: 1 }
const silent = { ...idle, segments: 0 }
const pending: ThemeState = {
  study: idle, content: null, text_available: true, audio_available: true,
  audio: { video: silent, audiobook: silent, podcast: silent },
}
const pack: ThemePack = {
  slides: [
    { title: 'O que é JOIN?', points: ['Combina tabelas'], narration: 'Veja como duas tabelas se relacionam.' },
    { title: 'INNER JOIN', points: ['Traz as correspondências'], narration: 'Cada linha precisa de uma correspondência.' },
  ],
  chapter: { title: 'Ligando tabelas', sections: [{ title: 'Introdução ao SQL', text: 'Relacione duas tabelas pela chave.' }] },
  podcast: { title: 'Conversas de SQL', turns: [
    { speaker: 'host', text: 'Quando uso INNER JOIN?' },
    { speaker: 'expert', text: 'Quando preciso apenas das correspondências.' },
  ] },
  map: { topic: 'JOINs em SQL', branches: [{ label: 'INNER JOIN', details: ['Intersecção de registros'] }] },
  quiz: [{ id: 'quiz-a', prompt: 'Qual operação combina tabelas?', options: [{ id: 'j', label: 'JOIN' }, { id: 'd', label: 'DROP' }] }],
  simulation: [
    { id: 's-a', prompt: 'Qual cláusula define a relação?', options: [{ id: 'o', label: 'ON' }, { id: 'f', label: 'FROM' }] },
    { id: 's-b', prompt: 'Qual tipo preserva a tabela da esquerda?', options: [{ id: 'l', label: 'LEFT' }, { id: 'i', label: 'INNER' }] },
  ],
}
const material: ThemeState = { ...pending, study: ready, content: pack }
const ok = (data: unknown) => ({ ok: true, status: 200, json: async () => data })

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

test('solicita material somente com consentimento e mantém a síntese separada', async () => {
  const mock = vi.fn(async (url: string, init: RequestInit) => {
    if (url === root && init.method === 'GET') return ok(pending)
    expect(JSON.parse(String(init.body))).toEqual({ consent: true })
    if (url === root) return ok(material)
    expect(url).toBe(root + '/audio/podcast')
    return ok({ ...material, audio: { ...material.audio, podcast: { ...ready, segments: 1 } } })
  })
  vi.stubGlobal('fetch', mock)
  const user = userEvent.setup()
  const { container } = render(<ThemeMaterials lessonId="licao" onExpired={vi.fn()}/>)
  const prepare = await screen.findByRole('button', { name: 'Preparar materiais' })
  expect(prepare).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /conteúdo desta lição/ }))
  await user.click(prepare)
  await user.click(await screen.findByRole('button', { name: 'Mapa mental' }))
  const branch = screen.getByText('INNER JOIN', { selector: 'summary' })
  await user.tab()
  await user.tab()
  await user.tab()
  expect(branch).toHaveFocus()
  await user.click(branch)
  expect(screen.getByText('Intersecção de registros')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Podcast' }))
  const preparePodcast = screen.getByRole('button', { name: 'Gerar podcast com duas vozes' })
  expect(preparePodcast).toBeDisabled()
  expect(mock).toHaveBeenCalledTimes(2)
  await user.click(screen.getByRole('checkbox', { name: /gerar a narração/ }))
  await user.click(preparePodcast)
  await screen.findByLabelText('Áudio do podcast')
  expect(container.querySelector('audio')).toHaveAttribute('src', root + '/audio/podcast/0')
  await user.click(screen.getByText('Transcrição do podcast', { selector: 'summary' }))
  expect(screen.getByText('Apresentador')).toBeVisible()
  expect(screen.getByText('Especialista')).toBeVisible()
})

test('recupera gravações e acompanha a mudança de cena quando a narração termina', async () => {
  const mock = vi.fn(async () => ok({ ...material, audio: { ...material.audio, video: { ...ready, segments: 2 } } }))
  vi.stubGlobal('fetch', mock)
  const play = vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  render(<ThemeMaterials lessonId="licao" onExpired={vi.fn()}/>)
  const audio = await screen.findByLabelText('Narração da cena')
  expect(audio).toHaveAttribute('src', root + '/audio/video/0')
  expect(screen.getByText(pack.slides[0].narration)).toBeVisible()
  fireEvent.ended(audio)
  expect(audio).toHaveAttribute('src', root + '/audio/video/1')
  expect(screen.getByText(pack.slides[1].narration)).toBeVisible()
  expect(play).toHaveBeenCalledOnce()
  expect(mock).toHaveBeenCalledOnce()
})

test('corrige quiz em uma questão, preserva seleção e envia o simulado completo', async () => {
  const requests: { url: string; answers: unknown }[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
    if (init.method === 'GET') return ok(material)
    const { answers } = JSON.parse(String(init.body)) as { answers: Record<string, string> }
    requests.push({ url, answers })
    const items = Object.keys(answers).map(question_id => ({ question_id, correct: true, feedback: 'Correção do servidor' }))
    return ok({ items, correct: items.length, total: items.length })
  }))
  const user = userEvent.setup()
  render(<ThemeMaterials lessonId="licao" onExpired={vi.fn()}/>)
  await user.click(await screen.findByRole('button', { name: 'Quiz' }))
  await user.click(screen.getByRole('radio', { name: 'JOIN' }))
  await user.click(screen.getByRole('button', { name: 'Simulado' }))
  expect(screen.getByRole('button', { name: 'Enviar simulado' })).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Quiz' }))
  expect(screen.getByRole('radio', { name: 'JOIN' })).toBeChecked()
  await user.click(screen.getByRole('button', { name: 'Corrigir questão' }))
  expect(await screen.findByText('Correção do servidor')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Ver resultado do quiz' }))
  expect(screen.getByRole('heading', { name: 'Resultado do quiz' })).toHaveFocus()
  await user.click(screen.getByRole('button', { name: 'Simulado' }))
  const question = screen.getByRole('group', { name: pack.simulation[0].prompt })
  await user.click(within(question).getByRole('radio', { name: 'ON' }))
  expect(screen.getByRole('button', { name: 'Enviar simulado' })).toBeDisabled()
  await user.click(screen.getByRole('radio', { name: 'LEFT' }))
  await user.click(screen.getByRole('button', { name: 'Enviar simulado' }))
  expect(await screen.findByText('2 de 2 respostas corretas.')).toBeVisible()
  expect(requests).toEqual([
    { url: root + '/quiz/grade', answers: { 'quiz-a': 'j' } },
    { url: root + '/simulation/grade', answers: { 's-a': 'o', 's-b': 'l' } },
  ])
})

test('reenvia o número zero de um job interrompido antes da primeira tentativa', async () => {
  const stale: ThemeState = {
    ...pending, study: { ...idle, status: 'failed', error: { detail: 'A configuração mudou.', retryable: true } },
  }
  const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
    if (init.method === 'GET') return ok(stale)
    expect(JSON.parse(String(init.body))).toEqual({ consent: true, retry_attempt: 0 })
    return ok(material)
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<ThemeMaterials lessonId="licao" onExpired={vi.fn()}/>)
  const retry = await screen.findByRole('button', { name: 'Tentar novamente' })
  await user.click(screen.getByRole('checkbox', { name: /conteúdo desta lição/ }))
  await user.click(retry)
  expect(await screen.findByRole('button', { name: 'Videoaula' })).toBeVisible()
})
