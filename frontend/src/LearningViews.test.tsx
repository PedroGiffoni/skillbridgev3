import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { LearningDashboard } from './LearningDashboard'
import { ModuleAssessment } from './ModuleAssessment'

const course = { id: 'c1', title: 'Fundamentos de SQL', revision: 2, plan_id: 'p1', created_at: '2026-01-01' }
const route = '/api/courses/c1/modules/fundamentos/assessment'
const dashboardPath = '/api/me/dashboard'
const form = {
  id: 'f1',
  questions: Array.from({ length: 10 }, (_, i) => ({
    id: 'q' + i, prompt: 'Questão sobre SQL ' + (i + 1),
    options: [{ id: 'a', label: 'Escolher consulta' }, { id: 'b', label: 'Escolher filtro' }],
  })),
}
const failed = {
  form_id: form.id, submitted_at: '2026-03-01T12:00:00Z', score: 90, correct: 9, total: 10, passed: false,
  competencies: [
    { id: 'queries', name: 'Consultas', correct: 9, total: 9 },
    { id: 'filters', name: 'Filtros', correct: 0, total: 1 },
  ],
  reinforcement: [{ outline_id: 'where', title: 'Praticar WHERE' }],
}
const approved = {
  ...failed, score: 100, correct: 10, passed: true,
  competencies: [...failed.competencies.slice(0, 1), { id: 'filters', name: 'Filtros', correct: 1, total: 1 }],
  reinforcement: [],
}
const weeks = Array.from({ length: 12 }, (_, i) => ({
  week: i + 1, title: 'Plano semanal ' + (i + 1), planned_minutes: 30, recorded_minutes: 0,
  lessons_completed: i === 0 ? 1 : 0, lessons_total: 2, complete: false, mastered_count: i >= 1 ? 1 : 0,
}))
const dashboard = {
  courses: [course], course, plan_revision: 2, xp: 60, achievements: ['Primeira aprovação'], weeks,
  competencies: [{ id: 'queries', name: 'Consultas', status: 'mastered', correct: 8, total: 10 }],
  modules: [
    { id: 'fundamentos', title: 'Consulta simples', objective: 'Usar SELECT', weeks: [1], prerequisites: [],
      status: 'mastered', lessons_completed: 1, lessons_total: 2, latest_score: 80, reinforcement: [] },
    { id: 'joins', title: 'Cruzar tabelas', objective: 'Usar JOIN', weeks: [2],
      prerequisites: [{ id: 'fundamentos', title: 'Consulta simples' }], status: 'locked', lessons_completed: 0,
      lessons_total: 2, latest_score: null, reinforcement: [] },
  ],
  next_lesson: { outline_id: 'select', title: 'Sua primeira consulta' },
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('mantém respostas quando o envio falha e só libera com os requisitos de domínio', async () => {
  let attempts = 0
  const send = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === route + '/submit') {
      expect(JSON.parse(String(init?.body))).toEqual({
        course_revision: 2, form_id: 'f1', answers: Object.fromEntries(form.questions.map(item => [item.id, 'a'])),
      })
      if (++attempts === 1) return Response.json({ detail: 'Falha temporária.' }, { status: 503 })
      return Response.json(failed)
    }
    if (url === route) {
      expect(JSON.parse(String(init?.body))).toEqual({ course_revision: 2, consent: true, previous_form_id: 'f1' })
      return Response.json({ available: true, pending: false, form: { ...form, id: 'f2' }, result: failed })
    }
    expect(url).toBe(route + '?course_revision=2')
    return Response.json({ available: true, pending: false, form, result: null })
  })
  vi.stubGlobal('fetch', send)
  const unlock = vi.fn()
  const review = vi.fn()
  const user = userEvent.setup()
  render(<ModuleAssessment course={course} moduleId="fundamentos" onExpired={vi.fn()} onUnlock={unlock} onReview={review}/>)

  await screen.findByText('Questão sobre SQL 1')
  for (let page = 0; page < 10; page += 1) {
    await user.click(screen.getByRole('radio', { name: 'Escolher consulta' }))
    if (page < 9) await user.click(screen.getByRole('button', { name: 'Próxima questão' }))
  }
  await user.click(screen.getByRole('button', { name: 'Enviar avaliação' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Falha temporária')
  expect(screen.getByRole('radio', { name: 'Escolher consulta' })).toBeChecked()
  await user.click(screen.getByRole('button', { name: 'Enviar avaliação' }))
  expect(await screen.findByText('90% de aproveitamento')).toBeVisible()
  expect(unlock).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Praticar WHERE' }))
  expect(review).toHaveBeenCalledWith('where')

  const prepare = screen.getByRole('button', { name: 'Preparar nova prova' })
  expect(prepare).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  await user.click(prepare)
  expect(await screen.findByText('Questão 1 de 10 · 0 respondidas')).toBeVisible()
})

it('atualiza as lições liberadas quando a prova é aprovada', async () => {
  const send = vi.fn(async (url: string) => url === route + '/submit'
    ? Response.json(approved)
    : Response.json({ available: true, pending: false, form, result: null }))
  vi.stubGlobal('fetch', send)
  const unlock = vi.fn()
  const user = userEvent.setup()
  render(<ModuleAssessment course={course} moduleId="fundamentos" onExpired={vi.fn()} onUnlock={unlock} onReview={vi.fn()}/>)
  await screen.findByText('Questão sobre SQL 1')
  for (let page = 0; page < 10; page += 1) {
    await user.click(screen.getByRole('radio', { name: 'Escolher consulta' }))
    if (page < 9) await user.click(screen.getByRole('button', { name: 'Próxima questão' }))
  }
  await user.click(screen.getByRole('button', { name: 'Enviar avaliação' }))
  const result = await screen.findByRole('heading', { name: 'Módulo aprovado' })
  expect(result).toHaveFocus()
  expect(unlock).toHaveBeenCalledTimes(1)
})

it('usa o progresso persistido para retomar, registrar tempo, replanejar e filtrar módulos', async () => {
  let current = dashboard
  const send = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === dashboardPath + '/time') {
      expect(JSON.parse(String(init?.body))).toEqual({ course_id: 'c1', course_revision: 2, week: 2, minutes: 45 })
      current = { ...current, weeks: current.weeks.map(week => week.week === 2 ? { ...week, recorded_minutes: 45 } : week) }
      return Response.json(current)
    }
    if (url === '/api/study-plans/p1/replan') {
      expect(JSON.parse(String(init?.body))).toEqual({ expected_revision: 2, minutes_per_week: 60 })
      current = { ...current, plan_revision: 3, weeks: current.weeks.map(week => ({ ...week, planned_minutes: 60 })) }
      return Response.json({ revision: 3 })
    }
    expect([dashboardPath, dashboardPath + '?course_id=c1']).toContain(url)
    return Response.json(current)
  })
  vi.stubGlobal('fetch', send)
  const user = userEvent.setup()
  const resume = vi.fn()
  render(<LearningDashboard heading={createRef()} onExpired={vi.fn()} onContinue={resume}/>)

  expect(await screen.findByText('Primeira aprovação')).toBeVisible()
  expect(screen.getByText('1 / 24')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Retomar lição' }))
  expect(resume).toHaveBeenCalledWith(course, 'select')

  await user.selectOptions(screen.getByLabelText('Semana para registrar'), '2')
  const minutes = screen.getByLabelText('Minutos estudados na semana')
  await user.clear(minutes)
  await user.type(minutes, '45')
  await user.click(screen.getByRole('button', { name: 'Salvar tempo' }))
  expect(await screen.findByText('Tempo da semana 2 salvo.')).toBeVisible()
  expect(screen.getByText('30 min planejados · 45 min registrados.')).toBeVisible()

  await user.click(screen.getByText('Replanejar semanas em aberto'))
  const plan = screen.getByLabelText('Minutos planejados por semana')
  await user.clear(plan)
  await user.type(plan, '60')
  await user.click(screen.getByRole('button', { name: 'Salvar planejamento' }))
  expect(await screen.findByText('1 h planejados · 45 min registrados.')).toBeVisible()

  await user.click(screen.getByRole('button', { name: 'Mapa do curso' }))
  const maze = screen.getByRole('region', { name: 'Mapa do curso' })
  await user.selectOptions(within(maze).getByLabelText('Estado do módulo'), 'locked')
  expect(within(maze).getByRole('heading', { name: 'Cruzar tabelas' })).toBeVisible()
  expect(within(maze).queryByRole('heading', { name: 'Consulta simples' })).toBeNull()
  expect(within(maze).getByText('Consulta simples.', { exact: false })).toBeVisible()
})