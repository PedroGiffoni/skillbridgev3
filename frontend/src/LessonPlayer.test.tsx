import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { LessonPlayer } from './LessonPlayer'
import type { Lesson } from './course-api'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const overview = {
  id: 'lesson', title: 'Investigar', week: 1, objective: 'Comparar hipóteses.',
  explanation: 'Registre os passos.', example: 'Compare dois registros.', summary: 'Revise os resultados.',
  practice: { attempts: 0, completed: false, latest_attempt: null },
}
const correct = { id: 'attempt', correct: true, hint_used: true, feedback: ['A resposta atende ao objetivo.'],
  created_at: '2026-11-20T12:00:00Z' }
const progress = { attempts: 1, completed: true, latest_attempt: correct }
const ok = (data: unknown) => ({ ok: true, status: 200, json: async () => data })

test('usa teclado para pedir dica, escolher resposta e revisar a correção do servidor', async () => {
  const lesson: Lesson = { ...overview, format: 'multiple_choice', exercise: {
    prompt: 'O que registrar?', options: [{ id: 'a', label: 'A hipótese' }, { id: 'b', label: 'O resultado' }],
  } }
  const requests: unknown[] = []
  const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
    requests.push(JSON.parse(String(init.body)))
    if (url.endsWith('/hint')) return ok({ text: 'Releia o exemplo.', receipt: 'receipt' })
    return ok({ attempt: correct, practice: progress })
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  const store = vi.fn()
  render(<LessonPlayer lesson={lesson} onExpired={vi.fn()} onProgress={store}/>)
  await user.tab()
  expect(screen.getByRole('radio', { name: 'A hipótese' })).toHaveFocus()
  expect(screen.getByRole('button', { name: 'Corrigir resposta' })).toBeDisabled()
  await user.tab()
  expect(screen.getByRole('button', { name: 'Ver dica' })).toHaveFocus()
  await user.keyboard('{Enter}')
  expect(await screen.findByText('Releia o exemplo.')).toHaveFocus()
  screen.getByRole('radio', { name: 'A hipótese' }).focus()
  await user.keyboard('{ArrowRight}')
  expect(screen.getByRole('radio', { name: 'O resultado' })).toBeChecked()
  await user.tab()
  await user.keyboard('{Enter}')
  expect(await screen.findByRole('heading', { name: 'Resposta correta' })).toHaveFocus()
  expect(screen.getByText(correct.feedback[0])).toBeVisible()
  expect(screen.getByText(overview.summary)).toBeVisible()
  expect(screen.getByText(/1 tentativa registrada/)).toBeVisible()
  expect(store).toHaveBeenCalledWith(progress)
  const { attempt_id } = requests[0] as { attempt_id: string }
  expect(attempt_id).toMatch(/^[0-9a-f]{32}$/)
  expect(requests[1]).toEqual({ attempt_id, hint_receipt: 'receipt', answer: { kind: 'multiple_choice', option_id: 'b' } })
})

test('reordena os passos por teclado sem perder o foco e envia os IDs nessa ordem', async () => {
  const lesson: Lesson = { ...overview, format: 'order_steps', exercise: {
    prompt: 'Ordene a investigação.',
    steps: [{ id: 'b', label: 'Testar' }, { id: 'a', label: 'Definir' }, { id: 'c', label: 'Rever' }],
  } }
  const wrong = { ...correct, correct: false, hint_used: false, feedback: ['Revise a sequência.'] }
  const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
    expect(JSON.parse(String(init.body)).answer).toEqual({ kind: 'order_steps', step_ids: ['a', 'b', 'c'] })
    return ok({ attempt: wrong, practice: { attempts: 1, completed: false, latest_attempt: wrong } })
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<LessonPlayer lesson={lesson} onExpired={vi.fn()} onProgress={vi.fn()}/>)
  const up = screen.getByRole('button', { name: 'Mover Definir para cima' })
  up.focus()
  await user.keyboard('{Enter}')
  expect(up).toHaveFocus()
  expect(up).toHaveAttribute('aria-disabled', 'true')
  expect(screen.getByText('Definir na posição 1 de 3.')).toBeInTheDocument()
  expect(within(screen.getByRole('list')).getAllByRole('listitem')[0]).toHaveTextContent('Definir')
  await user.click(screen.getByRole('button', { name: 'Corrigir resposta' }))
  expect(await screen.findByText(wrong.feedback[0])).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Nova tentativa' }))
  expect(screen.getByText(lesson.exercise.prompt)).toHaveFocus()
  expect(within(screen.getByRole('list')).getAllByRole('listitem')[0]).toHaveTextContent('Testar')
})

test('reenvia a mesma lacuna após erro de rede e recupera o progresso salvo ao reabrir', async () => {
  const lesson: Lesson = { ...overview, format: 'fill_blank', exercise: { prompt: 'Guarde o [lacuna].' } }
  const fetchMock = vi.fn<(url: string, init: RequestInit) => Promise<ReturnType<typeof ok>>>()
    .mockRejectedValueOnce(new Error('connection lost'))
    .mockResolvedValueOnce(ok({ attempt: correct, practice: progress }))
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  const view = render(<LessonPlayer lesson={lesson} onExpired={vi.fn()} onProgress={vi.fn()}/>)
  const field = screen.getByRole('textbox', { name: 'Resposta da lacuna' })
  await user.type(field, 'registro')
  await user.click(screen.getByRole('button', { name: 'Corrigir resposta' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Tente novamente')
  expect(field).toBeDisabled()
  await user.click(screen.getByRole('button', { name: 'Reenviar resposta' }))
  expect(await screen.findByRole('heading', { name: 'Resposta correta' })).toBeVisible()
  const sent = fetchMock.mock.calls.map(([, request]) => JSON.parse(String(request.body)))
  expect(sent[0].answer).toEqual({ kind: 'fill_blank', text: 'registro' })
  expect(sent[0]).toEqual(sent[1])
  view.unmount()
  render(<LessonPlayer lesson={{ ...lesson, practice: progress }} onExpired={vi.fn()} onProgress={vi.fn()}/>)
  expect(screen.getByText(/Prática concluída/)).toBeVisible()
  expect(screen.getByText('Dica usada nesta tentativa.')).toBeVisible()
  expect(fetchMock).toHaveBeenCalledTimes(2)
})
