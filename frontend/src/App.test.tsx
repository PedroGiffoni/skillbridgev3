import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { mockAssessment, mockQuestionnaire } from './test-fixtures'
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
test('fluxo API simulado em teste com validação, revisão, diagnóstico, trilha e reset', async () => {
 const q = mockQuestionnaire('Design de Produto Digital (UX/UI)')
 const result = mockAssessment(q, [1, 4, 4, 4, 4, 4, 4, 4])
 vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: true, json: async () => q })
   .mockResolvedValueOnce({ ok: true, json: async () => ({ email: 'ana@example.com' }) })
   .mockResolvedValueOnce({ ok: true, json: async () => result }))
 const user = userEvent.setup()
 render(<App />)
 expect(screen.getByText(/AUTOAVALIAÇÃO ORIENTATIVA/)).toBeVisible()
 await user.click(screen.getByRole('button', {name:'Escolher minha carreira'}))
 await user.click(screen.getByRole('button', {name:'Escolha uma carreira'}))
 await user.click(screen.getByRole('button', {name:'Design e experiência digital'}))
 await user.click(screen.getByRole('button', {name:q.profession}))
 await user.click(screen.getByRole('checkbox'))
 expect(screen.queryByRole('button', {name:/demonstração/i})).not.toBeInTheDocument()
 await user.click(screen.getByRole('button', {name:/Começar autoavaliação/}))
 await screen.findByRole('heading', {name:q.competencies[0].name})
 await user.click(screen.getByRole('button', {name:/Próxima pergunta/}))
 expect(screen.getByRole('alert')).toHaveTextContent('Selecione um nível')
 await user.click(screen.getByRole('radio', { name: /^1 ·/ }))
 await user.click(screen.getByRole('button', {name:/Próxima pergunta/}))
 await user.click(screen.getByRole('button', {name:'Voltar'}))
 expect(screen.getByRole('radio', { name: /^1 ·/ })).toBeChecked()
 await user.click(screen.getByRole('button', {name:/Próxima pergunta/}))
 for(let i=1;i<8;i++) {
 await user.click(screen.getByRole('radio', { name: /^4 ·/ }))
 await user.click(screen.getByRole('button', {name:i===7?/Continuar para contexto$/:/Próxima pergunta/}))
 }
  expect(screen.getByText('Pergunta 9 de 20')).toBeVisible()
  await user.click(screen.getByRole('radio', { name: 'Aprender a parte técnica' }))
  await user.click(screen.getByRole('button', { name: 'Próxima pergunta' }))
  await user.click(screen.getByRole('button', { name: 'Voltar' }))
  expect(screen.getByRole('radio', { name: 'Aprender a parte técnica' })).toBeChecked()
  await user.click(screen.getByRole('button', { name: 'Próxima pergunta' }))
  for (let i = 1; i < 12; i++) {
    await user.click(screen.getByRole('button', { name: i === 11 ? /^Ver diagnóstico$/ : 'Pular pergunta' }))
  }
 expect(await screen.findByText('Seu nível: 1/4 · Referência: 3/4 · Lacuna: 2')).toBeVisible()
 await user.click(screen.getByRole('button', {name:/Explorar trilha/}))
 expect(screen.getAllByText(/SEMANA 0/)).toHaveLength(4)
 await user.click(screen.getByRole('button', {name:/Concluir exploração/}))
 expect(screen.getByText(/Escolha uma ação da primeira semana/)).toBeVisible()
 await user.click(screen.getByRole('button', {name:/Reiniciar e apagar/}))
 await user.click(screen.getByRole('button', {name:'Escolher minha carreira'}))
 expect(screen.getByRole('button', {name:'Escolha uma carreira'})).toBeVisible()
 expect(screen.getByRole('checkbox')).not.toBeChecked()
})
