import '@testing-library/jest-dom'

/**
 * Test environment setup for Vitest
 *
 * Configures the jsdom test environment with necessary DOM elements
 * required by the React application entry point.
 */

const rootElement = document.createElement('div')
rootElement.id = 'root'
document.body.appendChild(rootElement)
