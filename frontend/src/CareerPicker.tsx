import { Check, ChevronDown, Search } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import careerCatalog from './careers.json'
import './CareerPicker.css'

type CareerPickerProps = {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

function searchWords(value: string) {
  return value.normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLocaleLowerCase('pt-BR')
    .split(/[^\p{L}\p{N}]+/u)
    .filter(Boolean)
}

const families = careerCatalog.groups

const careerIndex = families.flatMap(family => family.careers.map(career => ({
  ...career,
  familyId: family.id,
  familyLabel: family.label,
  words: searchWords([career.label, ...career.aliases, family.label].join(' ')),
})))

export function CareerPicker({ value, onChange, disabled = false }: CareerPickerProps) {
  const [open, setOpen] = useState(false)
  const [familyId, setFamilyId] = useState('')
  const [query, setQuery] = useState('')
  const trigger = useRef<HTMLButtonElement>(null)
  const results = useRef<HTMLUListElement>(null)
  const labelId = useId()
  const searchId = useId()
  const panelId = useId()
  const selected = careerIndex.find(career => career.label === value)
  const expanded = open && !disabled
  const terms = searchWords(query)
  const searching = terms.length > 0
  const visibleCareers = careerIndex.filter(career => searching
    ? terms.every(term => career.words.some(word => word.startsWith(term)))
    : career.familyId === familyId)

  function close() {
    setOpen(false)
    trigger.current?.focus()
  }

  function toggle() {
    if (expanded) {
      close()
      return
    }

    setQuery('')
    setFamilyId(selected?.familyId ?? '')
    setOpen(true)
  }

  function handleSearchKeys(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' && !event.nativeEvent.isComposing) event.preventDefault()
    if (event.key === 'ArrowDown') {
      const first = results.current?.querySelector('button')
      if (first) {
        event.preventDefault()
        first.focus()
      }
    }
  }

  return <div className="career-picker" onKeyDown={event => {
    if (expanded && event.key === 'Escape') {
      event.preventDefault()
      close()
    }
  }}>
    <p id={labelId} className="career-picker__label">Carreira em tecnologia <span>(obrigatória)</span></p>
    <button
      ref={trigger}
      type="button"
      className="career-picker__trigger"
      disabled={disabled}
      aria-expanded={expanded}
      aria-controls={expanded ? panelId : undefined}
      aria-describedby={labelId}
      onClick={toggle}
    >
      <span>{selected?.label ?? 'Escolha uma carreira'}</span>
      {selected ? <Check size={18} aria-hidden="true" /> : <ChevronDown size={18} aria-hidden="true" />}
    </button>

    {expanded && <div id={panelId} className="career-picker__panel">
      <label htmlFor={searchId}>Buscar carreira</label>
      <div className="career-picker__search">
        <Search size={17} aria-hidden="true" />
        <input
          id={searchId}
          type="search"
          placeholder="Ex.: dados, DevOps, UX"
          value={query}
          onChange={event => setQuery(event.target.value)}
          onKeyDown={handleSearchKeys}
        />
      </div>

      {!searching && <div className="career-picker__families" role="group" aria-label="Áreas de tecnologia">
        {families.map(family => <button
          key={family.id}
          type="button"
          aria-pressed={family.id === familyId}
          onClick={() => setFamilyId(family.id)}
        >{family.label}</button>)}
      </div>}

      {searching && <p className="career-picker__status" role="status">
        {visibleCareers.length ? `${visibleCareers.length} ${visibleCareers.length === 1 ? 'carreira encontrada' : 'carreiras encontradas'}` : 'Nenhuma carreira encontrada'}
      </p>}

      {visibleCareers.length > 0 && <ul ref={results} className="career-picker__results" aria-label="Carreiras disponíveis">
        {visibleCareers.map(career => <li key={career.id}>
          <button
            type="button"
            aria-label={career.label}
            aria-describedby={`${panelId}-${career.id}`}
            aria-pressed={career.label === value}
            onClick={() => { onChange(career.label); close() }}
          >
            <strong>{career.label}</strong>
            <span id={`${panelId}-${career.id}`}>{career.description}</span>
            {searching && <span className="career-picker__family-label">{career.familyLabel}</span>}
          </button>
        </li>)}
      </ul>}
    </div>}
  </div>
}