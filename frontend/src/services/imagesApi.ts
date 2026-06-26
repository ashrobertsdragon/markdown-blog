import { getAuthHeaders } from '@/services/auth-headers'
import { apiClient } from './postsApi'

/** Response from a successful image upload */
export interface UploadImageResponse {
  url: string
}

/** Response from listing images for a post */
export interface ListImagesResponse {
  images: string[]
}

/**
 * Images API service — upload, list, and delete post images.
 *
 * Reuses the shared apiClient so API_BASE_URL is never duplicated.
 */
export const imagesApi = {
  /**
   * Upload an image file for a post.
   *
   * Sends the file as multipart/form-data; the browser sets the boundary
   * automatically when FormData is passed directly to axios.
   *
   * @param slug - Post slug the image belongs to
   * @param file - File object selected by the user
   * @param token - JWT authentication token
   * @returns Public URL of the stored image
   */
  async uploadImage(slug: string, file: File, token: string): Promise<UploadImageResponse> {
    const form = new FormData()
    form.append('file', file)
    const response = await apiClient.post<UploadImageResponse>(
      `/posts/${slug}/images`,
      form,
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * List all images uploaded for a post.
   *
   * @param slug - Post slug whose images to retrieve
   * @param token - JWT authentication token
   * @returns Array of public image URL paths
   */
  async listImages(slug: string, token: string): Promise<ListImagesResponse> {
    const response = await apiClient.get<ListImagesResponse>(
      `/posts/${slug}/images`,
      getAuthHeaders(token)
    )
    return response.data
  },

  /**
   * Delete an uploaded image.
   *
   * @param slug - Post slug the image belongs to
   * @param filename - Filename of the image to remove
   * @param token - JWT authentication token
   */
  async deleteImage(slug: string, filename: string, token: string): Promise<void> {
    await apiClient.delete(`/posts/${slug}/images/${filename}`, getAuthHeaders(token))
  },
}
