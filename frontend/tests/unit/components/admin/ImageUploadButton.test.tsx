import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ImageUploadButton } from '@/components/admin/ImageUploadButton'
import { useImageUpload } from '@/hooks/useImageUpload'

vi.mock('@/hooks/useImageUpload')
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const renderButton = (onInsert = vi.fn()) =>
  render(<ImageUploadButton slug="my-post" onInsert={onInsert} />, {
    wrapper: createWrapper(),
  })

describe('ImageUploadButton', () => {
  const mockUploadImage = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useImageUpload).mockReturnValue({
      uploadImage: mockUploadImage,
      isUploading: false,
      error: null,
    })
  })

  it('renders the insert image button', () => {
    renderButton()
    expect(screen.getByRole('button', { name: /insert image/i })).toBeInTheDocument()
  })

  it('clicking the button triggers the hidden file input', async () => {
    const user = userEvent.setup()
    renderButton()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const clickSpy = vi.spyOn(input, 'click')

    await user.click(screen.getByRole('button', { name: /insert image/i }))

    expect(clickSpy).toHaveBeenCalled()
  })

  it('shows spinner and disables button while uploading', () => {
    vi.mocked(useImageUpload).mockReturnValue({
      uploadImage: mockUploadImage,
      isUploading: true,
      error: null,
    })

    renderButton()

    expect(screen.getByRole('button', { name: /uploading/i })).toBeDisabled()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('calls onInsert with markdown snippet on successful upload', async () => {
    const onInsert = vi.fn()
    mockUploadImage.mockResolvedValue('/uploads/my-post/photo.jpg')

    renderButton(onInsert)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })

    await userEvent.upload(input, file)

    expect(onInsert).toHaveBeenCalledWith('![photo.jpg](/uploads/my-post/photo.jpg)')
  })

  it('shows error toast and does not call onInsert when upload fails', async () => {
    const { toast } = await import('sonner')
    const onInsert = vi.fn()
    mockUploadImage.mockRejectedValue(new Error('Network error'))

    renderButton(onInsert)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['bytes'], 'photo.jpg', { type: 'image/jpeg' })

    await userEvent.upload(input, file)

    expect(onInsert).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith('Image upload failed')
  })
})
