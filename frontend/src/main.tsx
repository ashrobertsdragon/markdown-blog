import { ClerkProvider } from '@clerk/clerk-react'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/App'
import '@/index.css'

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
const isTestMockPresent =
  import.meta.env.MODE === 'test' &&
  typeof window !== 'undefined' &&
  '__CLERK_TEST_MOCK__' in (window as { __CLERK_TEST_MOCK__?: unknown })

if (!publishableKey && !isTestMockPresent) {
  throw new Error(
    'Missing Clerk configuration: VITE_CLERK_PUBLISHABLE_KEY environment variable is not set.\n' +
      'Please add it to your .env file or environment configuration.\n' +
      'See .env.example for setup instructions.'
  )
}

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Root element with id="root" not found in HTML')
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    {isTestMockPresent ? (
      <App />
    ) : (
      <ClerkProvider publishableKey={publishableKey ?? ''}>
        <App />
      </ClerkProvider>
    )}
  </React.StrictMode>
)
