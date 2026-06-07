/**
 * Creates an authorization header config for a given bearer token
 */
export const getAuthHeaders = (token: string) => ({
  headers: { Authorization: `Bearer ${token}` },
})
