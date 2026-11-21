import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, expect, test, vi } from 'vitest'
import { CareerPicker } from './CareerPicker'

vi.mock('./careers.json', () => ({
  default: { version: 1, groups: [
    {
      id: 'development',
      label: 'Desenvolvimento',
      careers: [
        { id: 'front', label: 'Desenvolvimento Front-end', description: 'Constrói interfaces.', aliases: ['front end'] },
      ],
    },
    {
      id: 'operations',
      label: 'Infraestrutura',
      careers: [
        { id: 'sre', label: 'Engenharia de Confiabilidade', description: 'Mantém serviços confiáveis.', aliases: ['SRE', 'observação'] },
      ],
    },
  ] },
}))

afterEach(cleanup)

function Field({ onChange = vi.fn() }: { onChange?: (label: string) => void }) {
  const [value, setValue] = useState('')
  return <CareerPicker value={value} onChange={label => { setValue(label); onChange(label) }} />
}

test('escolhe uma carreira pela família sem digitar', async () => {
  const user = userEvent.setup()
  render(<Field />)

  await user.click(screen.getByRole('button', { name: 'Escolha uma carreira' }))
  await user.click(screen.getByRole('button', { name: 'Infraestrutura' }))
  await user.click(screen.getByRole('button', { name: 'Engenharia de Confiabilidade' }))

  expect(screen.getByRole('button', { name: 'Engenharia de Confiabilidade' })).toHaveAttribute('aria-expanded', 'false')
})

test('busca um alias parcial sem acentos em todas as famílias e seleciona por teclado', async () => {
  const user = userEvent.setup()
  const onChange = vi.fn()
  render(<Field onChange={onChange} />)

  await user.tab()
  await user.keyboard('{Enter}')
  await user.click(screen.getByRole('button', { name: 'Desenvolvimento' }))
  const search = screen.getByRole('searchbox', { name: 'Buscar carreira' })
  await user.type(search, 'observa')
  expect(onChange).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Engenharia de Confiabilidade' })).toBeVisible()

  await user.keyboard('{ArrowDown}')
  expect(screen.getByRole('button', { name: 'Engenharia de Confiabilidade' })).toHaveFocus()
  await user.keyboard('{Enter}')
  expect(onChange).toHaveBeenCalledWith('Engenharia de Confiabilidade')
  expect(screen.getByRole('button', { name: 'Engenharia de Confiabilidade' })).toHaveFocus()
})

test('informa busca sem resultados e permite fechar sem escolher', async () => {
  const user = userEvent.setup()
  const onChange = vi.fn()
  render(<Field onChange={onChange} />)

  const trigger = screen.getByRole('button', { name: 'Escolha uma carreira' })
  await user.click(trigger)
  await user.type(screen.getByRole('searchbox', { name: 'Buscar carreira' }), 'profissão inexistente')
  expect(screen.getByRole('status')).toHaveTextContent('Nenhuma carreira encontrada')

  await user.keyboard('{Enter}')
  expect(onChange).not.toHaveBeenCalled()
  await user.keyboard('{Escape}')
  expect(trigger).toHaveAttribute('aria-expanded', 'false')
  expect(trigger).toHaveFocus()
})

test('mostra a carreira selecionada enquanto o formulário está ocupado', () => {
  render(<CareerPicker value="Engenharia de Confiabilidade" onChange={vi.fn()} disabled />)
  expect(screen.getByRole('button', { name: 'Engenharia de Confiabilidade' })).toBeDisabled()
})