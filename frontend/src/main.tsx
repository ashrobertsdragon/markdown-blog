import { ClerkProvider } from '@clerk/clerk-react'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/App'
import '@/index.css'

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
const isTestMode =
  typeof window !== 'undefined' && (window as { __CLERK_TEST_MOCK__?: unknown }).__CLERK_TEST_MOCK__

if (!publishableKey && !isTestMode) {
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
    {isTestMode ? (
      <App />
    ) : (
      <ClerkProvider publishableKey={publishableKey ?? ''}>
        <App />
      </ClerkProvider>
    )}
  </React.StrictMode>
)
