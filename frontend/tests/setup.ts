import '@testing-library/jest-dom'
import { vi } from 'vitest'

/**
 * Test environment setup for Vitest
 *
 * Configures the jsdom test environment with necessary DOM elements
 * required by the React application entry point.
 *
 * Exposes `vi` as `jest` on globalThis so that @testing-library/dom's
 * jestFakeTimersAreEnabled() check succeeds when vi.useFakeTimers() is
 * active. Without this, waitFor() uses setInterval for retries which
 * never fires under fake timers, causing test timeouts.
 */

Object.defineProperty(globalThis, 'jest', {
  value: vi,
  writable: true,
  configurable: true,
})

const rootElement = document.createElement('div')
rootElement.id = 'root'
document.body.appendChild(rootElement)

/**
 * jsdom does not implement window.matchMedia, but react-hot-toast uses it
 * to detect the user's color-scheme preference. This stub satisfies the call
 * so Toaster renders without throwing in the test environment.
 */
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn((query: string) => ({
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
