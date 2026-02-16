import { useAuth as useClerkAuth, useUser } from '@clerk/clerk-react'
import type { UserResource } from '@clerk/shared/types'
import type { ReactNode } from 'react'
import { createContext, useContext } from 'react'

export type UserType = UserResource

export interface AuthContextType {
  user: UserType | null | undefined
  isLoaded: boolean
  isSignedIn: boolean | undefined
  role: 'authenticated' | 'author' | 'admin'
  getToken: (options?: { template?: string }) => Promise<string | null>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export interface AuthProviderProps {
  children: ReactNode
}

function ClerkAuthProvider({ children }: AuthProviderProps) {
  const { user: clerkUser, isLoaded: clerkIsLoaded, isSignedIn: clerkIsSignedIn } = useUser()
  const { getToken: clerkGetToken } = useClerkAuth()

  const roleValue = clerkUser?.publicMetadata?.role
  const role: AuthContextType['role'] =
    roleValue === 'admin' || roleValue === 'author' || roleValue === 'authenticated'
      ? roleValue
      : 'authenticated'

  const value: AuthContextType = {
    user: clerkUser,
    isLoaded: clerkIsLoaded,
    isSignedIn: clerkIsSignedIn,
    role,
    getToken: clerkGetToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function MockAuthProvider({ children }: AuthProviderProps) {
  const testMock =
    typeof window !== 'undefined'
      ? (window as { __CLERK_TEST_MOCK__?: UserType }).__CLERK_TEST_MOCK__
      : undefined

  const isSignedIn = testMock !== undefined && testMock !== null
  const roleValue = testMock?.publicMetadata?.role
  const role: AuthContextType['role'] =
    roleValue === 'admin' || roleValue === 'author' || roleValue === 'authenticated'
      ? roleValue
      : 'authenticated'

  const value: AuthContextType = {
    user: testMock,
    isLoaded: true,
    isSignedIn,
    role,
    getToken: async () => (isSignedIn ? 'mock_token_123' : null),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function AuthProvider({ children }: AuthProviderProps) {
  // Check if we're in test mode (property exists on window, even if undefined)
  const isTestMode =
    typeof window !== 'undefined' &&
    '__CLERK_TEST_MOCK__' in (window as { __CLERK_TEST_MOCK__?: UserType })

  // Use different provider based on test mode
  if (isTestMode) {
    return <MockAuthProvider>{children}</MockAuthProvider>
  }

  return <ClerkAuthProvider>{children}</ClerkAuthProvider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
