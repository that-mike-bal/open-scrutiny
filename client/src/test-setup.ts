import '@testing-library/jest-dom'
import { vi, afterEach } from 'vitest'

// Mock environment variables
Object.defineProperty(window, 'import.meta', {
  value: {
    env: {
      VITE_SUPABASE_URL: 'test-supabase-url',
      VITE_SUPABASE_ANON_KEY: 'test-supabase-key',
    }
  }
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock fetch for local data files
global.fetch = vi.fn()

// Setup cleanup after each test
afterEach(() => {
  vi.clearAllMocks()
})