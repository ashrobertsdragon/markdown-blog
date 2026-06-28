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

function deriveRoleFromMetadata(
  user?: { publicMetadata?: { role?: AuthContextType['role'] | string } } | null
): AuthContextType['role'] {
  const roleValue = user?.publicMetadata?.role
  return roleValue === 'admin' || roleValue === 'author' || roleValue === 'authenticated'
    ? (roleValue as AuthContextType['role'])
    : 'authenticated'
}

function ClerkAuthProvider({ children }: AuthProviderProps) {
  const { user: clerkUser, isLoaded: clerkIsLoaded, isSignedIn: clerkIsSignedIn } = useUser()
  const { getToken: clerkGetToken } = useClerkAuth()

  const role = deriveRoleFromMetadata(clerkUser)

  const value: AuthContextType = {
    user: clerkUser,
    isLoaded: clerkIsLoaded,
    isSignedIn: clerkIsSignedIn,
    role,
    getToken: clerkGetToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function AuthProvider({ children }: AuthProviderProps) {
  return <ClerkAuthProvider>{children}</ClerkAuthProvider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
