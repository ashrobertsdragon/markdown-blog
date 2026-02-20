import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PostEditor from '@/pages/PostEditor'

vi.mock('@/components/post/MarkdownEditor', () => ({
  MarkdownEditor: ({
    value,
    onChange,
    onSave,
  }: {
    value: string
    onChange: (val: string) => void
    onSave?: () => void
  }) => (
    <div data-testid="markdown-editor">
      <textarea
        data-testid="markdown-textarea"
        value={value}
        onChange={e => onChange(e.target.value)}
      />
      <button
        type="button"
        data-testid="editor-save-trigger"
        onClick={onSave}
        style={{ display: 'none' }}
      >
        Save via Ctrl+S
      </button>
    </div>
  ),
}))

vi.mock('@/components/post/PreviewPane', () => ({
  PreviewPane: ({ markdown }: { markdown: string }) => (
    <div data-testid="preview-pane">
      <div data-testid="preview-content">{markdown}</div>
    </div>
  ),
}))

const mockMutateAsync = vi.fn()
const mockUseDraft = vi.fn()
const mockUseSaveDraft = vi.fn()
const mockUsePublishPost = vi.fn()

vi.mock('@/hooks/usePosts', () => ({
  useDraft: () => mockUseDraft(),
  useSaveDraft: () => mockUseSaveDraft(),
  usePublishPost: () => mockUsePublishPost(),
}))

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('PostEditor Component', () => {
  const mockDraft = {
    slug: 'test-post',
    title: 'Test Post Title',
    content: '# Existing content',
    status: 'draft' as const,
    created_at: '2025-01-01T12:00:00Z',
    updated_at: '2025-01-01T12:30:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()

    mockUseSaveDraft.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      error: null,
    })

    mockUsePublishPost.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      error: null,
    })
  })

  function renderPostEditor(slug: string | null = 'test-post') {
    const initialEntries = slug ? [`/editor/${slug}`] : ['/editor']

    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          {/* Creation route – no slug param */}
          <Route path="/editor" element={<PostEditor />} />
          {/* Edit route – matches existing draft by slug */}
          <Route path="/editor/:slug" element={<PostEditor />} />
        </Routes>
      </MemoryRouter>
    )
  }

  it('renders loading state while fetching draft', () => {
    mockUseDraft.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    })

    renderPostEditor()

    expect(screen.getByText(/loading draft/i)).toBeInTheDocument()
    const loadingContainer = screen.getByRole('status')
    expect(loadingContainer).toBeInTheDocument()

    const spinner = loadingContainer.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('renders error state when draft fetch fails', () => {
    mockUseDraft.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Network error'),
    })

    renderPostEditor()

    expect(screen.getByText(/error loading draft/i)).toBeInTheDocument()
    expect(screen.getByText(/network error/i)).toBeInTheDocument()
  })

  it('renders error state when draft not found', () => {
    mockUseDraft.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    expect(screen.getByText(/error loading draft/i)).toBeInTheDocument()
    expect(screen.getByText(/draft not found/i)).toBeInTheDocument()
  })

  it('renders editor interface when draft loads successfully', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    expect(screen.getByText('Test Post Title')).toBeInTheDocument()
    expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument()
  })

  it('populates editor with draft content on mount', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const textarea = screen.getByTestId('markdown-textarea')
    expect(textarea).toHaveValue('# Existing content')
  })

  it('calls useSaveDraft when Save button clicked', async () => {
    mockMutateAsync.mockResolvedValue(mockDraft)
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const saveButton = screen.getByRole('button', { name: /save/i })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        slug: 'test-post',
        content: '# Existing content',
      })
    })
  })

  it('calls useSaveDraft when Ctrl+S pressed via MarkdownEditor', async () => {
    mockMutateAsync.mockResolvedValue(mockDraft)
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const ctrlSSaveButton = screen.getByTestId('editor-save-trigger')
    fireEvent.click(ctrlSSaveButton)

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        slug: 'test-post',
        content: '# Existing content',
      })
    })
  })

  it('shows AlertDialog when Publish button clicked', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const publishButton = screen.getByRole('button', { name: /publish/i })
    fireEvent.click(publishButton)

    expect(screen.getByText(/are you sure you want to publish/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('calls usePublishPost when publish confirmed in dialog', async () => {
    mockMutateAsync.mockResolvedValue(mockDraft)
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const publishButton = screen.getByRole('button', { name: /^publish$/i })
    fireEvent.click(publishButton)

    const confirmButton = await screen.findByRole('button', { name: /^publish$/i, hidden: false })
    fireEvent.click(confirmButton)

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith('test-post')
    })
  })

  it('navigates to /posts/:slug after successful publish', async () => {
    mockMutateAsync.mockResolvedValue(mockDraft)
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const publishButton = screen.getByRole('button', { name: /^publish$/i })
    fireEvent.click(publishButton)

    const confirmButton = await screen.findByRole('button', { name: /^publish$/i, hidden: false })
    fireEvent.click(confirmButton)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/posts/test-post')
    })
  })

  it('shows success message after successful save', async () => {
    mockMutateAsync.mockResolvedValue(mockDraft)
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const saveButton = screen.getByRole('button', { name: /save/i })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/draft saved successfully/i)).toBeInTheDocument()
    })
  })

  it('auto-dismisses success message after 3 seconds', async () => {
    mockMutateAsync.mockResolvedValue(mockDraft)
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const saveButton = screen.getByRole('button', { name: /save/i })
    fireEvent.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/draft saved successfully/i)).toBeInTheDocument()
    })

    await waitFor(
      () => {
        expect(screen.queryByText(/draft saved successfully/i)).not.toBeInTheDocument()
      },
      { timeout: 4000 }
    )
  })

  it('shows error Alert when save fails', async () => {
    const saveError = new Error('Save failed: network timeout')

    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    mockUseSaveDraft.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      error: saveError,
    })

    renderPostEditor()

    expect(screen.getByText(/save failed/i)).toBeInTheDocument()
    expect(screen.getByText(/network timeout/i)).toBeInTheDocument()
  })

  it('shows error Alert when publish fails', async () => {
    const publishError = new Error('Publish failed: unauthorized')

    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    mockUsePublishPost.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
      error: publishError,
    })

    renderPostEditor()

    expect(screen.getByText(/publish failed/i)).toBeInTheDocument()
    expect(screen.getByText(/unauthorized/i)).toBeInTheDocument()
  })

  it('toggles between editor and preview on mobile', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
    expect(screen.queryByTestId('preview-pane')).not.toBeInTheDocument()

    const mobileToggle = screen.getAllByRole('button', {
      name: /preview|edit/i,
    })[1]
    fireEvent.click(mobileToggle)

    expect(screen.getByTestId('preview-pane')).toBeInTheDocument()
  })

  it('shows both editor and preview on desktop when preview enabled', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const desktopToggle = screen.getAllByRole('button', {
      name: /show preview|hide preview/i,
    })[0]
    fireEvent.click(desktopToggle)

    const editors = screen.getAllByTestId('markdown-editor')
    const previews = screen.getAllByTestId('preview-pane')

    expect(editors.length).toBeGreaterThanOrEqual(1)
    expect(previews.length).toBeGreaterThanOrEqual(1)
  })

  it('updates content state when user edits markdown', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const textarea = screen.getByTestId('markdown-textarea')
    fireEvent.change(textarea, { target: { value: '# New content' } })

    expect(textarea).toHaveValue('# New content')
  })

  it('disables Save button during save operation', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    mockUseSaveDraft.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: true,
      error: null,
    })

    renderPostEditor()

    const saveButton = screen.getByRole('button', { name: /saving/i })
    expect(saveButton).toBeDisabled()
    expect(saveButton).toHaveTextContent('Saving...')
  })

  it('disables Publish button during publish operation', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    mockUsePublishPost.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: true,
      error: null,
    })

    renderPostEditor()

    const publishButton = screen.getByRole('button', { name: /publishing/i })
    expect(publishButton).toBeDisabled()
    expect(publishButton).toHaveTextContent('Publishing...')
  })

  it('closes publish dialog when cancel clicked', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const publishButton = screen.getByRole('button', { name: /publish/i })
    fireEvent.click(publishButton)

    expect(screen.getByText(/are you sure/i)).toBeInTheDocument()

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    fireEvent.click(cancelButton)

    expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument()
  })

  it('displays last updated timestamp', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    expect(screen.getByText(/last updated:/i)).toBeInTheDocument()
  })

  it('passes current content to PreviewPane component', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    const previewButton = screen.getAllByRole('button', { name: /preview/i })[0]
    fireEvent.click(previewButton)

    const textarea = screen.getByTestId('markdown-textarea')
    fireEvent.change(textarea, { target: { value: '# Updated preview' } })

    const previewContent = screen.getByTestId('preview-content')
    expect(previewContent).toHaveTextContent('Updated preview')
  })

  describe('Create mode (no slug)', () => {
    it('renders create mode UI without fetching draft', () => {
      mockUseDraft.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      renderPostEditor(null)

      expect(screen.getByText(/new post/i)).toBeInTheDocument()

      expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()

      expect(mockUseDraft).toHaveBeenCalled()
    })

    it('does not save when no slug is present', async () => {
      mockUseDraft.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      renderPostEditor(null)

      const saveButton = screen.getByRole('button', { name: /save/i })
      fireEvent.click(saveButton)

      expect(mockMutateAsync).not.toHaveBeenCalled()
    })

    it('does not publish when no slug is present', async () => {
      mockUseDraft.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })
      mockUsePublishPost.mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
        error: null,
      })

      renderPostEditor(null)

      const publishButtons = screen.getAllByRole('button', { name: /publish/i })
      fireEvent.click(publishButtons[0])

      await waitFor(() => {
        expect(screen.getByText(/are you sure you want to publish/i)).toBeInTheDocument()
      })

      const allPublishButtons = screen.getAllByRole('button', { name: /publish/i })
      const confirmButton = allPublishButtons[allPublishButtons.length - 1]
      fireEvent.click(confirmButton)

      expect(mockMutateAsync).not.toHaveBeenCalled()
    })

    it('allows content editing in create mode', () => {
      mockUseDraft.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      renderPostEditor(null)

      const textarea = screen.getByTestId('markdown-textarea')
      fireEvent.change(textarea, { target: { value: '# My new post' } })

      expect(textarea).toHaveValue('# My new post')
    })
  })
})
