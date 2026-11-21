import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// jsdom não implementa os observadores usados pelo Motion no navegador.
vi.stubGlobal('IntersectionObserver', class {
  observe() {}
  unobserve() {}
  disconnect() {}
})
Object.defineProperty(window, 'matchMedia', { writable: true, value: vi.fn().mockImplementation(() => ({ matches: true, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} })) })
