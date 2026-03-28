import type { RenderOptions } from '@testing-library/react'
import { render as rtlRender } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '@/App'
import { AuthProvider } from '@/context/AuthContext'

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[]
}

/**
 * Ensures the Clerk test mock key exists on window so AuthProvider uses
 * MockAuthProvider (unauthenticated) instead of ClerkAuthProvider which
 * requires a real ClerkProvider in the component tree.
 *
 * Uses `in` operator semantics: key existence triggers mock mode, value
 * of undefined means unauthenticated.
 */
function ensureClerkTestMock() {
  if (!('__CLERK_TEST_MOCK__' in window)) {
    Object.defineProperty(window, '__CLERK_TEST_MOCK__', {
      value: undefined,
      writable: true,
      configurable: true,
    })
  }
}

export function render(ui: React.ReactElement, options?: CustomRenderOptions) {
  const { initialEntries, ...renderOptions } = options || {}

  if (initialEntries) {
    ensureClerkTestMock()
    return rtlRender(
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>,
      renderOptions
    )
  }

  return rtlRender(ui, renderOptions)
}

export {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
