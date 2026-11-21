import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { afterEach, expect, test, vi } from 'vitest'
import { CourseLibrary } from './CourseLibrary'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const course = { id: 'course', title: 'Laboratório de design', revision: 2, plan_id: 'plan', created_at: '2026-11-20T12:00:00Z' }
const slot = { outline_id: 'lesson-1', module_title: 'Fundamentos', title: 'Teste sua hipótese',
  objective: 'Comparar duas tentativas.', week: 1, job_id: null, lesson_id: null, practice_completed: false }
const lesson = { id: 'saved-lesson', title: slot.title, week: 1, objective: slot.objective,
  explanation: 'Registre o resultado antes de comparar.', example: 'Teste duas alternativas.', summary: 'Confira as diferenças.',
  format: 'multiple_choice', practice: { attempts: 0, completed: false, latest_attempt: null },
  exercise: { prompt: 'O que registrar?', options: [{ id: 'a', label: 'O resultado observado' }] } }
const json = (data: unknown, status = 200) => ({ ok: true, status, json: async () => data })
const job = { id: 'job', status: 'ready', attempts: 1, error: null, retry_after_seconds: 0, draft: null, lesson: null }

test('reabre um curso e uma lição salva apenas por leitura', async () => {
  const fetchMock = vi.fn(async (url: string) => {
    if (url === '/api/courses?offset=0') return json({ items: [course], next_offset: null })
    if (url === '/api/courses/course/lessons?course_revision=2') return json({ items: [{ ...slot, lesson_id: lesson.id }] })
    if (url === '/api/lessons/' + lesson.id) return json(lesson)
    throw new Error('Chamada inesperada: ' + url)
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<CourseLibrary planId={null} heading={createRef()} onExpired={vi.fn()}/>)
  await user.click(await screen.findByRole('button', { name: 'Abrir curso Laboratório de design' }))
  const open = await screen.findByRole('button', { name: slot.title })
  open.focus()
  await user.keyboard('{Enter}')
  expect(await screen.findByText(lesson.explanation)).toBeVisible()
  expect(screen.getByRole('heading', { name: slot.title })).toHaveFocus()
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
    '/api/courses?offset=0', '/api/courses/course/lessons?course_revision=2', '/api/lessons/saved-lesson',
  ])
})

test('salva o rascunho validado e prepara uma lição apenas após consentimento', async () => {
  const draft = { ...course, revision: 1, content: { title: course.title } }
  const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
    if (url === '/api/courses?offset=0') return json({ items: [], next_offset: null })
    if (url === '/api/study-plans/plan/course-job') return json({ job: { ...job, draft } })
    if (url === '/api/courses/course/publish') {
      expect(JSON.parse(String(init.body))).toEqual({ draft_revision: 1 })
      return json({ ...draft, revision: 2 })
    }
    if (url === '/api/courses/course/lessons?course_revision=2') return json({ items: [slot] })
    if (url === '/api/courses/course/lessons/lesson-1/generate') {
      expect(JSON.parse(String(init.body))).toEqual({ course_revision: 2, consent: true })
      return json({ ...job, lesson }, 202)
    }
    throw new Error('Chamada inesperada: ' + url)
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<CourseLibrary planId="plan" heading={createRef()} onExpired={vi.fn()}/>)
  await user.click(await screen.findByRole('button', { name: 'Salvar na biblioteca' }))
  await user.click(await screen.findByRole('button', { name: slot.title }))
  const prepare = await screen.findByRole('button', { name: 'Preparar esta lição' })
  expect(prepare).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /Autorizo o Gemini/ }))
  await user.click(prepare)
  expect(await screen.findByText(lesson.explanation)).toBeVisible()
  await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init.method === 'POST')).toHaveLength(2))
})


test('mantém a resposta da lição aberta e navega para a próxima pelo player', async () => {
  const next = { ...slot, outline_id: 'lesson-2', title: 'Compare duas hipóteses', week: 2 }
  const fetchMock = vi.fn(async (url: string) => {
    if (url === '/api/courses?offset=0') return json({ items: [course], next_offset: null })
    if (url === '/api/courses/course/lessons?course_revision=2') return json({
      items: [{ ...slot, lesson_id: lesson.id, practice_completed: true }, next],
    })
    if (url === '/api/lessons/' + lesson.id) return json(lesson)
    throw new Error('Chamada inesperada: ' + url)
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<CourseLibrary planId={null} heading={createRef()} onExpired={vi.fn()}/>)
  await user.click(await screen.findByRole('button', { name: 'Abrir curso Laboratório de design' }))
  const open = await screen.findByRole('button', { name: slot.title })
  expect(screen.getByText('1 de 2 práticas concluídas')).toBeVisible()
  await user.click(open)
  const answer = await screen.findByRole('radio', { name: 'O resultado observado' })
  await user.click(answer)
  await user.click(open)
  expect(answer).toBeChecked()
  expect(fetchMock).toHaveBeenCalledTimes(3)
  await user.click(screen.getByRole('button', { name: 'Próxima lição' }))
  expect(await screen.findByRole('heading', { name: next.title })).toHaveFocus()
  await user.click(screen.getByRole('button', { name: 'Lição anterior' }))
  expect(await screen.findByRole('radio')).toBeVisible()
})
