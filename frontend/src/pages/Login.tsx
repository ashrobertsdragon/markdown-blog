import { SignIn } from '@clerk/clerk-react'
import { Component, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

interface LocationState {
  from?: {
    pathname: string
  }
}

class SignInErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) return null
    return this.props.children
  }
}

export default function Login() {
  const location = useLocation()
  const state = location.state as LocationState | null | undefined

  const redirectUrl = state?.from?.pathname || '/'

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
      <div className="w-full max-w-md px-4">
        <h1 className="mb-6 text-center text-4xl font-bold text-gray-800">
          Sign In to Your Account
        </h1>
        <div className="flex justify-center">
          <SignInErrorBoundary>
            <SignIn redirectUrl={redirectUrl} afterSignInUrl={redirectUrl} />
          </SignInErrorBoundary>
        </div>
      </div>
    </div>
  )
}
