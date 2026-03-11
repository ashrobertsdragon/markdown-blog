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
