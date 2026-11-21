import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'

export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === 'dark')
  function toggle() {
    const next = !dark
    setDark(next)
    document.documentElement.dataset.theme = next ? 'dark' : 'light'
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', next ? '#0c1221' : '#f8f9fc')
    try { localStorage.setItem('skillbridge-theme', next ? 'dark' : 'light') } catch { /* A preferência é opcional. */ }
  }
  return <button className="theme-toggle" onClick={toggle} aria-label={dark ? 'Ativar modo claro' : 'Ativar modo escuro'} title={dark ? 'Ativar modo claro' : 'Ativar modo escuro'}>{dark ? <Sun size={18}/> : <Moon size={18}/>}<span>{dark ? 'Modo claro' : 'Modo escuro'}</span></button>
}
