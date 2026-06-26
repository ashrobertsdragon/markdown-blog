import { useMutation } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { imagesApi } from '@/services/imagesApi'

/**
 * Hook for uploading images to a post.
 *
 * Wraps imagesApi.uploadImage in a React Query mutation so callers get
 * declarative isPending/error state without owning async orchestration.
 *
 * @param slug - Post slug the uploaded image belongs to
 * @returns uploadImage function, isUploading boolean, and error value
 */
export function useImageUpload(slug: string): {
  uploadImage: (file: File) => Promise<string>
  isUploading: boolean
  error: Error | null
} {
  const auth = useAuth()

  const mutation = useMutation({
    mutationFn: async (file: File): Promise<string> => {
      const token = await auth.getToken()
      if (!token) throw new Error('Authentication required')
      const response = await imagesApi.uploadImage(slug, file, token)
      return response.url
    },
  })

  return {
    uploadImage: mutation.mutateAsync,
    isUploading: mutation.isPending,
    error: mutation.error,
  }
}
