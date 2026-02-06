import axios, { type AxiosInstance } from 'axios'

/**
 * Health check response for basic application health
 */
export interface HealthResponse {
  status: string
}

/**
 * Health check response for database connectivity
 */
export interface DatabaseHealthResponse extends HealthResponse {
  database?: string
}

/**
 * Health check response for GitHub API connectivity
 */
export interface GitHubHealthResponse extends HealthResponse {
  github?: string
}

/**
 * Health check API service
 *
 * Provides methods to check health status of the application,
 * database, and GitHub API connectivity.
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
})

/**
 * Health service object with async methods for health checks
 */
export const healthService = {
  /**
   * Check application health status
   *
   * @returns Health status response
   * @throws Network or server errors
   */
  async checkHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health')
    return response.data
  },

  /**
   * Check database connectivity
   *
   * @returns Database health status response
   * @throws Network, server, or database connection errors
   */
  async checkDatabase(): Promise<DatabaseHealthResponse> {
    const response = await apiClient.get<DatabaseHealthResponse>('/health/db')
    return response.data
  },

  /**
   * Check GitHub API reachability
   *
   * @returns GitHub API health status response
   * @throws Network, server, or GitHub API errors
   */
  async checkGitHub(): Promise<GitHubHealthResponse> {
    const response = await apiClient.get<GitHubHealthResponse>('/health/github')
    return response.data
  },
}
