import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useImageUpload } from '@/hooks/useImageUpload'
import { imagesApi } from '@/services/imagesApi'

vi.mock('@/services/imagesApi')
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn(async () => 'mock-token'),
  })),
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
    },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('useImageUpload', () => {
  const mockFile = new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns the uploaded image URL on success', async () => {
    vi.mocked(imagesApi.uploadImage).mockResolvedValue({ url: '/uploads/my-post/photo.jpg' })

    const { result } = renderHook(() => useImageUpload('my-post'), {
      wrapper: createWrapper(),
    })

    let url: string | undefined
    await waitFor(async () => {
      url = await result.current.uploadImage(mockFile)
    })

    expect(url).toBe('/uploads/my-post/photo.jpg')
    expect(imagesApi.uploadImage).toHaveBeenCalledWith('my-post', mockFile, 'mock-token')
  })

  it('isUploading is false before mutation starts', () => {
    const { result } = renderHook(() => useImageUpload('my-post'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isUploading).toBe(false)
  })

  it('sets error when upload fails', async () => {
    const uploadError = new Error('Upload failed')
    vi.mocked(imagesApi.uploadImage).mockRejectedValue(uploadError)

    const { result } = renderHook(() => useImageUpload('my-post'), {
      wrapper: createWrapper(),
    })

    await expect(result.current.uploadImage(mockFile)).rejects.toThrow('Upload failed')

    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
    })
  })
})
