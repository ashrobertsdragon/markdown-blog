import type { RenderOptions } from '@testing-library/react'
import { render as rtlRender } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '@/App'
import { AuthProvider } from '@/context/AuthContext'

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[]
}

export function render(ui: React.ReactElement, options?: CustomRenderOptions) {
  const { initialEntries, ...renderOptions } = options || {}

  if (initialEntries) {
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
