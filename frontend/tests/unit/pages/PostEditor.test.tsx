import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PostEditor from '@/pages/PostEditor'

/**
 * Mock child components to isolate PostEditor testing
 */
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
  PreviewPane: ({ content }: { content: string }) => (
    <div data-testid="preview-pane">
      <div data-testid="preview-content">{content}</div>
    </div>
  ),
}))

/**
 * Mock hooks from @/hooks/usePosts
 */
const mockMutateAsync = vi.fn()
const mockUseDraft = vi.fn()
const mockUseSaveDraft = vi.fn()
const mockUsePublishPost = vi.fn()

vi.mock('@/hooks/usePosts', () => ({
  useDraft: () => mockUseDraft(),
  useSaveDraft: () => mockUseSaveDraft(),
  usePublishPost: () => mockUsePublishPost(),
}))

/**
 * Mock react-router-dom navigation
 */
const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

/**
 * Test suite for PostEditor page component
 *
 * Tests editor workflow, state management, mutations, and user interactions
 * following TDD methodology. Tests written BEFORE implementation exists.
 */
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

  /**
   * Helper to render PostEditor with react-router context
   *
   * When slug is provided or defaulted to 'test-post', we simulate the edit route /editor/:slug
   * When slug is explicitly null, we simulate the creation route /editor with no slug
   */
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

  /**
   * RED phase: Test loading state while fetching draft
   * Expected to FAIL if loading spinner not shown during isLoading
   */
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
    // Spinner is decorative (aria-hidden), so we check for the animated element by class
    const spinner = loadingContainer.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  /**
   * RED phase: Test error state when draft fetch fails
   * Expected to FAIL if error Alert not displayed with error message
   */
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

  /**
   * RED phase: Test error state when draft not found (null data)
   * Expected to FAIL if default error message not shown
   */
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

  /**
   * RED phase: Test successful draft load renders editor interface
   * Expected to FAIL if MarkdownEditor and action buttons not rendered
   */
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

  /**
   * RED phase: Test draft content populates editor on load
   * Expected to FAIL if editor value not synced from draft.content
   */
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

  /**
   * RED phase: Test Save button calls useSaveDraft mutation
   * Expected to FAIL if mutateAsync not called with correct params
   */
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

  /**
   * RED phase: Test Ctrl+S keyboard shortcut triggers save
   * Expected to FAIL if MarkdownEditor onSave callback not wired to handleSave
   */
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

  /**
   * RED phase: Test Publish button shows confirmation AlertDialog
   * Expected to FAIL if AlertDialog not opened when Publish clicked
   */
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

  /**
   * RED phase: Test publish confirmation calls usePublishPost
   * Expected to FAIL if mutateAsync not called when confirm clicked
   */
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

  /**
   * RED phase: Test navigation after successful publish
   * Expected to FAIL if navigate not called with /posts/:slug
   */
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

  /**
   * RED phase: Test success message shown after save
   * Expected to FAIL if success Alert not displayed after mutateAsync resolves
   */
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

  /**
   * RED phase: Test error Alert when save fails
   * Expected to FAIL if error message not displayed in Alert
   */
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

  /**
   * RED phase: Test error Alert when publish fails
   * Expected to FAIL if publish error not displayed
   */
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

  /**
   * RED phase: Test preview toggle on mobile (single view)
   * Expected to FAIL if preview doesn't replace editor on mobile toggle
   */
  it('toggles between editor and preview on mobile', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    // Initially editor should be visible, preview hidden
    expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()
    expect(screen.queryByTestId('preview-pane')).not.toBeInTheDocument()

    // Click preview toggle button (mobile)
    const mobileToggle = screen.getAllByRole('button', {
      name: /preview|edit/i,
    })[1]
    fireEvent.click(mobileToggle)

    // Preview should be visible, editor hidden (on mobile)
    expect(screen.getByTestId('preview-pane')).toBeInTheDocument()
  })

  /**
   * RED phase: Test both editor and preview visible on desktop when enabled
   * Expected to FAIL if both components not rendered when showPreview true
   */
  it('shows both editor and preview on desktop when preview enabled', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    // Toggle preview on
    const desktopToggle = screen.getAllByRole('button', {
      name: /show preview|hide preview/i,
    })[0]
    fireEvent.click(desktopToggle)

    // Both should be rendered (one hidden on mobile via CSS)
    const editors = screen.getAllByTestId('markdown-editor')
    const previews = screen.getAllByTestId('preview-pane')

    expect(editors.length).toBeGreaterThanOrEqual(1)
    expect(previews.length).toBeGreaterThanOrEqual(1)
  })

  /**
   * RED phase: Test editor content updates when user types
   * Expected to FAIL if content state not synced with textarea value
   */
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

  /**
   * RED phase: Test Save button disabled during save operation
   * Expected to FAIL if button not disabled when isPending true
   */
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

  /**
   * RED phase: Test Publish button disabled during publish operation
   * Expected to FAIL if button not disabled when isPending true
   */
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

  /**
   * RED phase: Test cancel button in publish dialog closes dialog
   * Expected to FAIL if dialog not closed when cancel clicked
   */
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

  /**
   * RED phase: Test updated_at timestamp displayed correctly
   * Expected to FAIL if timestamp not formatted and shown
   */
  it('displays last updated timestamp', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    expect(screen.getByText(/last updated:/i)).toBeInTheDocument()
  })

  /**
   * RED phase: Test PreviewPane receives current content
   * Expected to FAIL if preview not synced with editor content state
   */
  it('passes current content to PreviewPane component', () => {
    mockUseDraft.mockReturnValue({
      data: mockDraft,
      isLoading: false,
      error: null,
    })

    renderPostEditor()

    // Enable preview
    const previewButton = screen.getAllByRole('button', { name: /preview/i })[0]
    fireEvent.click(previewButton)

    // Update content
    const textarea = screen.getByTestId('markdown-textarea')
    fireEvent.change(textarea, { target: { value: '# Updated preview' } })

    // Preview should immediately reflect the new content
    const previewContent = screen.getByTestId('preview-content')
    expect(previewContent).toHaveTextContent('# Updated preview')
  })

  /**
   * Create mode tests - when no slug param is present
   */
  describe('Create mode (no slug)', () => {
    /**
     * Test that PostEditor renders without errors when no slug is provided
     */
    it('renders create mode UI without fetching draft', () => {
      mockUseDraft.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      renderPostEditor(null) // explicitly null for create mode

      // Should show "New Post" title
      expect(screen.getByText(/new post/i)).toBeInTheDocument()

      // Should render editor interface
      expect(screen.getByTestId('markdown-editor')).toBeInTheDocument()

      // useDraft should have been called with empty string (which disables the query)
      expect(mockUseDraft).toHaveBeenCalled()
    })

    /**
     * Test that save button is disabled in create mode
     */
    it('does not save when no slug is present', async () => {
      mockUseDraft.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      renderPostEditor(null) // explicitly null for create mode

      const saveButton = screen.getByRole('button', { name: /save/i })
      fireEvent.click(saveButton)

      // Save mutation should not be called
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

    /**
     * Test that editor allows typing in create mode
     */
    it('allows content editing in create mode', () => {
      mockUseDraft.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      })

      renderPostEditor(null) // explicitly null for create mode

      const textarea = screen.getByTestId('markdown-textarea')
      fireEvent.change(textarea, { target: { value: '# My new post' } })

      expect(textarea).toHaveValue('# My new post')
    })
  })
})
