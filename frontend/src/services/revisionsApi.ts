import { apiClient } from './postsApi'

/**
 * Author metadata for a revision
 */
export interface RevisionAuthor {
  id: string
  name: string
}

/**
 * Abbreviated revision information for list views
 */
export interface RevisionListItem {
  id: string
  commit_sha: string
  short_sha: string
  author: RevisionAuthor
  timestamp: string
  relative_time: string
  commit_message: string
  is_revert: boolean
}

/**
 * Full revision details including content
 */
export interface RevisionDetail {
  id: string
  commit_sha: string
  short_sha: string
  author: RevisionAuthor
  timestamp: string
  commit_message: string
  markdown_content: string
  html_content: string
  is_current: boolean
  is_revert: boolean
}

/**
 * Paginated list of revisions response
 */
export interface ListRevisionsResponse {
  revisions: RevisionListItem[]
  total_count: number
  has_more: boolean
}

/**
 * Abbreviated revision metadata for diff context
 */
export interface DiffRevisionMeta {
  sha: string
  timestamp: string
}

/**
 * Single line in a diff view
 */
export interface DiffLine {
  type: 'context' | 'addition' | 'deletion'
  content: string
  lineNumber?: number
}

/**
 * Diff comparison between two revisions
 */
export interface DiffResponse {
  from_revision: DiffRevisionMeta
  to_revision: DiffRevisionMeta
  diff_lines: DiffLine[]
}

/**
 * Response from revert operation
 */
export interface RevertResponse {
  success: boolean
  message: string
  new_commit_sha: string
  redirect_url: string
}

/**
 * Helper to create authorization header config
 */
const getAuthHeaders = (token: string) => ({
  headers: { Authorization: `Bearer ${token}` },
})

/**
 * Revisions API service object
 */
export const revisionsApi = {
  /**
   * List revision history for a post with pagination
   *
   * @param slug - Post slug identifier
   * @param skip - Number of revisions to skip (offset)
   * @param limit - Maximum number of revisions to return
   * @param token - JWT authentication token
   * @returns Paginated list of revisions with metadata
   * @throws AxiosError on not found (404), forbidden (403), or unauthorized (401)
   */
  async listRevisions(
    slug: string,
    skip: number,
    limit: number,
    token: string
  ): Promise<ListRevisionsResponse> {
    const response = await apiClient.get<ListRevisionsResponse>(`/posts/${slug}/revisions`, {
      params: { skip, limit },
      ...getAuthHeaders(token),
    })
    return response.data
  },

  /**
   * Retrieve full details of a specific revision including content
   *
   * @param slug - Post slug identifier
   * @param sha - Git commit SHA (full or short)
   * @param token - JWT authentication token
   * @returns Complete revision data with markdown and HTML content
   * @throws AxiosError on not found (404), forbidden (403), or server error (500)
   */
  async getRevision(slug: string, sha: string, token: string): Promise<RevisionDetail> {
    const response = await apiClient.get<RevisionDetail>(
      `/posts/${slug}/revisions/${sha}`,
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Get diff between two revisions
   *
   * @param slug - Post slug identifier
   * @param sha1 - First revision SHA (older)
   * @param sha2 - Second revision SHA (newer)
   * @param token - JWT authentication token
   * @returns Diff lines with context, additions, and deletions
   * @throws AxiosError on not found (404), forbidden (403), or server error (500)
   */
  async getDiff(slug: string, sha1: string, sha2: string, token: string): Promise<DiffResponse> {
    const response = await apiClient.get<DiffResponse>(
      `/posts/${slug}/revisions/${sha1}/diff/${sha2}`,
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Revert post to a previous revision
   *
   * @param slug - Post slug identifier
   * @param targetSha - SHA of revision to revert to
   * @param token - JWT authentication token
   * @returns Success confirmation with new commit SHA and redirect URL
   * @throws AxiosError on not found (404), forbidden (403), unauthorized (401), or server error (500)
   */
  async revertToRevision(slug: string, targetSha: string, token: string): Promise<RevertResponse> {
    const response = await apiClient.post<RevertResponse>(
      `/posts/${slug}/revert`,
      { target_sha: targetSha },
      getAuthHeaders(token)
    )
    return response.data
  },
}
