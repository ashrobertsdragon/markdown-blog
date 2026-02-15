import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PostForm } from '@/components/post/PostForm'

/**
 * Test suite for PostForm component
 *
 * Tests the form for creating new blog posts with slug and title inputs.
 * Validates slug formatting rules per requirement 8.1:
 * - Lowercase enforcement
 * - Space to hyphen conversion
 * - Special character removal
 * - Non-empty validation
 * - Max 200 character limit
 */
describe('PostForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Form Rendering', () => {
    /**
     * RED phase: Test that form renders with all required fields
     * Expected to FAIL because PostForm component does not exist yet
     */
    it('renders form with slug input field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      expect(slugInput).toBeInTheDocument()
      expect(slugInput).toHaveAttribute('type', 'text')
    })

    /**
     * RED phase: Test that form renders title input field
     * Expected to FAIL because PostForm component does not exist yet
     */
    it('renders form with title input field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const titleInput = screen.getByTestId('post-form-title-input')
      expect(titleInput).toBeInTheDocument()
      expect(titleInput).toHaveAttribute('type', 'text')
    })

    /**
     * RED phase: Test that form renders submit button
     * Expected to FAIL because PostForm component does not exist yet
     */
    it('renders submit button', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).toBeInTheDocument()
      expect(submitButton).toHaveAttribute('type', 'submit')
    })

    /**
     * RED phase: Test that submit button is initially disabled
     * Expected to FAIL because validation logic doesn't exist yet
     */
    it('submit button is disabled when form is empty', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).toBeDisabled()
    })

    /**
     * RED phase: Test that form accepts custom className
     * Expected to FAIL because PostForm doesn't accept className prop yet
     */
    it('accepts and applies className prop to form container', () => {
      const mockOnSubmit = vi.fn()
      const customClass = 'custom-form-class'

      render(<PostForm onSubmit={mockOnSubmit} className={customClass} />)

      const form = screen.getByTestId('post-form')
      expect(form).toHaveClass(customClass)
    })
  })

  describe('Slug Validation - Lowercase Enforcement (Requirement 8.1)', () => {
    /**
     * RED phase: Test that slug input converts uppercase to lowercase
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('converts uppercase letters to lowercase in slug field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'MY-BLOG-POST' } })

      expect(slugInput).toHaveValue('my-blog-post')
    })

    /**
     * RED phase: Test that slug input converts mixed case to lowercase
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('converts mixed case to lowercase in slug field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'My-First-Blog-Post' } })

      expect(slugInput).toHaveValue('my-first-blog-post')
    })
  })

  describe('Slug Validation - Space to Hyphen Conversion (Requirement 8.1)', () => {
    /**
     * RED phase: Test that spaces are converted to hyphens
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('replaces spaces with hyphens in slug field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my blog post' } })

      expect(slugInput).toHaveValue('my-blog-post')
    })

    /**
     * RED phase: Test that multiple consecutive spaces become single hyphen
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('collapses multiple spaces into single hyphen', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my    blog    post' } })

      expect(slugInput).toHaveValue('my-blog-post')
    })

    /**
     * RED phase: Test that leading/trailing spaces are trimmed
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('trims leading and trailing spaces from slug', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: '  my-blog-post  ' } })

      expect(slugInput).toHaveValue('my-blog-post')
    })
  })

  describe('Slug Validation - Special Character Removal (Requirement 8.1)', () => {
    /**
     * RED phase: Test that special characters are removed
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('removes special characters from slug field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my@blog#post!' } })

      expect(slugInput).toHaveValue('myblogpost')
    })

    /**
     * RED phase: Test that punctuation is removed
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('removes punctuation from slug field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my.blog,post;test' } })

      expect(slugInput).toHaveValue('myblogposttest')
    })

    /**
     * RED phase: Test that allowed characters (alphanumeric and hyphens) remain
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('preserves alphanumeric characters and hyphens', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my-blog-post-123' } })

      expect(slugInput).toHaveValue('my-blog-post-123')
    })

    /**
     * RED phase: Test that underscores are handled (converted or removed)
     * Expected to FAIL because slug validation logic doesn't exist yet
     */
    it('removes underscores from slug field', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my_blog_post' } })

      expect(slugInput).toHaveValue('myblogpost')
    })
  })

  describe('Slug Validation - Empty Validation (Requirement 8.1)', () => {
    /**
     * Empty slug validation is tested via disabled submit button state.
     * See "Form Submission Behavior" tests which verify the submit button
     * remains disabled when slug is empty. This prevents form submission
     * rather than showing errors after attempting to click disabled button.
     */
    it('submit button remains disabled when slug is empty', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const titleInput = screen.getByTestId('post-form-title-input')
      fireEvent.change(titleInput, { target: { value: 'My Title' } })

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).toBeDisabled()
    })
  })

  describe('Slug Validation - Max Length (Requirement 8.1)', () => {
    /**
     * RED phase: Test that slug length is capped at 200 characters
     * Expected to FAIL because max length validation doesn't exist yet
     */
    it('prevents slug exceeding 200 characters', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      const longSlug = 'a'.repeat(250)
      fireEvent.change(slugInput, { target: { value: longSlug } })

      expect((slugInput as HTMLInputElement).value.length).toBeLessThanOrEqual(200)
    })

    /**
     * RED phase: Test that slug at exactly 200 characters is valid
     * Expected to FAIL because validation logic doesn't exist yet
     */
    it('accepts slug at exactly 200 characters', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      const maxSlug = 'a'.repeat(200)
      fireEvent.change(slugInput, { target: { value: maxSlug } })

      expect(slugInput).toHaveValue(maxSlug)

      const errorMessage = screen.queryByTestId('slug-error')
      expect(errorMessage).not.toBeInTheDocument()
    })
  })

  describe('Title Validation', () => {
    /**
     * Title validation is tested via disabled submit button state.
     * See "Form Submission Behavior" tests which verify the submit button
     * remains disabled when title is empty. This prevents form submission
     * rather than showing errors after attempting to click disabled button.
     */
    it('submit button remains disabled when title is empty', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      fireEvent.change(slugInput, { target: { value: 'my-slug' } })

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).toBeDisabled()
    })
  })

  describe('Form Submission Behavior', () => {
    /**
     * RED phase: Test that submit button is disabled when fields are invalid
     * Expected to FAIL because validation state management doesn't exist yet
     */
    it('submit button is disabled when slug is invalid', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const titleInput = screen.getByTestId('post-form-title-input')
      fireEvent.change(titleInput, { target: { value: 'My Title' } })

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).toBeDisabled()
    })

    /**
     * RED phase: Test that submit button is disabled when title is invalid
     * Expected to FAIL because validation state management doesn't exist yet
     */
    it('submit button is disabled when title is invalid', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      fireEvent.change(slugInput, { target: { value: 'my-slug' } })

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).toBeDisabled()
    })

    /**
     * RED phase: Test that submit button is enabled when both fields are valid
     * Expected to FAIL because validation state management doesn't exist yet
     */
    it('submit button is enabled when both slug and title are valid', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      const titleInput = screen.getByTestId('post-form-title-input')

      fireEvent.change(slugInput, { target: { value: 'my-blog-post' } })
      fireEvent.change(titleInput, { target: { value: 'My Blog Post' } })

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).not.toBeDisabled()
    })

    /**
     * RED phase: Test that onSubmit callback is called with correct data
     * Expected to FAIL because form submission logic doesn't exist yet
     */
    it('calls onSubmit with slug and title when form is submitted', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      const titleInput = screen.getByTestId('post-form-title-input')

      fireEvent.change(slugInput, { target: { value: 'my-blog-post' } })
      fireEvent.change(titleInput, { target: { value: 'My Blog Post' } })

      const submitButton = screen.getByTestId('post-form-submit')
      fireEvent.click(submitButton)

      expect(mockOnSubmit).toHaveBeenCalledTimes(1)
      expect(mockOnSubmit).toHaveBeenCalledWith({
        slug: 'my-blog-post',
        title: 'My Blog Post',
      })
    })

    /**
     * RED phase: Test that form prevents default submission behavior
     * Expected to FAIL because form submission handler doesn't exist yet
     */
    it('prevents default form submission', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      const titleInput = screen.getByTestId('post-form-title-input')
      const form = screen.getByTestId('post-form')

      fireEvent.change(slugInput, { target: { value: 'my-slug' } })
      fireEvent.change(titleInput, { target: { value: 'My Title' } })

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true })
      const preventDefaultSpy = vi.spyOn(submitEvent, 'preventDefault')

      fireEvent(form, submitEvent)

      expect(preventDefaultSpy).toHaveBeenCalled()
    })

    /**
     * RED phase: Test that form handles submission errors gracefully
     * Expected to FAIL because error handling logic doesn't exist yet
     */
    it('handles onSubmit throwing error gracefully', () => {
      const mockOnSubmit = vi.fn(() => {
        throw new Error('Submission failed')
      })
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      const titleInput = screen.getByTestId('post-form-title-input')

      fireEvent.change(slugInput, { target: { value: 'my-slug' } })
      fireEvent.change(titleInput, { target: { value: 'My Title' } })

      const submitButton = screen.getByTestId('post-form-submit')

      expect(() => {
        fireEvent.click(submitButton)
      }).not.toThrow()

      consoleErrorSpy.mockRestore()
    })
  })

  describe('onChange Callbacks', () => {
    /**
     * RED phase: Test that onChange is called when slug changes
     * Expected to FAIL because onChange prop doesn't exist yet
     */
    it('calls onChange callback when slug changes', () => {
      const mockOnChange = vi.fn()
      const mockOnSubmit = vi.fn()

      render(<PostForm onSubmit={mockOnSubmit} onChange={mockOnChange} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my-slug' } })

      expect(mockOnChange).toHaveBeenCalled()
      expect(mockOnChange).toHaveBeenCalledWith({
        slug: 'my-slug',
        title: '',
      })
    })

    /**
     * RED phase: Test that onChange is called when title changes
     * Expected to FAIL because onChange prop doesn't exist yet
     */
    it('calls onChange callback when title changes', () => {
      const mockOnChange = vi.fn()
      const mockOnSubmit = vi.fn()

      render(<PostForm onSubmit={mockOnSubmit} onChange={mockOnChange} />)

      const titleInput = screen.getByTestId('post-form-title-input')

      fireEvent.change(titleInput, { target: { value: 'My Title' } })

      expect(mockOnChange).toHaveBeenCalled()
      expect(mockOnChange).toHaveBeenCalledWith({
        slug: '',
        title: 'My Title',
      })
    })

    /**
     * RED phase: Test that onChange is called with both values when both fields change
     * Expected to FAIL because onChange prop doesn't exist yet
     */
    it('calls onChange with both values when both fields are populated', () => {
      const mockOnChange = vi.fn()
      const mockOnSubmit = vi.fn()

      render(<PostForm onSubmit={mockOnSubmit} onChange={mockOnChange} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      const titleInput = screen.getByTestId('post-form-title-input')

      fireEvent.change(slugInput, { target: { value: 'my-slug' } })
      fireEvent.change(titleInput, { target: { value: 'My Title' } })

      expect(mockOnChange).toHaveBeenCalledTimes(2)
      expect(mockOnChange).toHaveBeenLastCalledWith({
        slug: 'my-slug',
        title: 'My Title',
      })
    })
  })

  describe('Complex Slug Transformations', () => {
    /**
     * RED phase: Test complex slug transformation with all rules applied
     * Expected to FAIL because complex validation logic doesn't exist yet
     */
    it('applies all slug transformations in combination', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, {
        target: { value: '  My FIRST Blog Post!!!  @2024  ' },
      })

      expect(slugInput).toHaveValue('my-first-blog-post-2024')
    })

    /**
     * RED phase: Test slug with emoji and unicode characters
     * Expected to FAIL because unicode handling doesn't exist yet
     */
    it('removes emoji and unicode characters from slug', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my-blog-post-🎉-test' } })

      expect((slugInput as HTMLInputElement).value).not.toContain('🎉')
      expect((slugInput as HTMLInputElement).value).toMatch(/^[a-z0-9-]+$/)
    })

    /**
     * RED phase: Test slug with consecutive hyphens are collapsed
     * Expected to FAIL because hyphen normalization doesn't exist yet
     */
    it('collapses consecutive hyphens into single hyphen', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: 'my---blog---post' } })

      expect(slugInput).toHaveValue('my-blog-post')
    })

    /**
     * RED phase: Test slug with leading/trailing hyphens are removed
     * Expected to FAIL because hyphen trimming doesn't exist yet
     */
    it('removes leading and trailing hyphens from slug', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')

      fireEvent.change(slugInput, { target: { value: '-my-blog-post-' } })

      expect(slugInput).toHaveValue('my-blog-post')
    })
  })

  describe('Accessibility', () => {
    /**
     * RED phase: Test that form fields have proper labels
     * Expected to FAIL because label elements don't exist yet
     */
    it('has accessible labels for slug and title inputs', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugLabel = screen.getByLabelText(/slug/i)
      const titleLabel = screen.getByLabelText(/title/i)

      expect(slugLabel).toBeInTheDocument()
      expect(titleLabel).toBeInTheDocument()
    })

    /**
     * RED phase: Test that aria-invalid is false when inputs are empty (not yet touched)
     */
    it('marks inputs with aria-invalid false when untouched', () => {
      const mockOnSubmit = vi.fn()
      render(<PostForm onSubmit={mockOnSubmit} />)

      const slugInput = screen.getByTestId('post-form-slug-input')
      const titleInput = screen.getByTestId('post-form-title-input')

      expect(slugInput).toHaveAttribute('aria-invalid', 'false')
      expect(titleInput).toHaveAttribute('aria-invalid', 'false')
    })
  })

  describe('Initial Values', () => {
    /**
     * RED phase: Test that form accepts initial slug value
     * Expected to FAIL because initialValues prop doesn't exist yet
     */
    it('renders with initial slug value when provided', () => {
      const mockOnSubmit = vi.fn()
      render(
        <PostForm onSubmit={mockOnSubmit} initialValues={{ slug: 'existing-slug', title: '' }} />
      )

      const slugInput = screen.getByTestId('post-form-slug-input')
      expect(slugInput).toHaveValue('existing-slug')
    })

    /**
     * RED phase: Test that form accepts initial title value
     * Expected to FAIL because initialValues prop doesn't exist yet
     */
    it('renders with initial title value when provided', () => {
      const mockOnSubmit = vi.fn()
      render(
        <PostForm onSubmit={mockOnSubmit} initialValues={{ slug: '', title: 'Existing Title' }} />
      )

      const titleInput = screen.getByTestId('post-form-title-input')
      expect(titleInput).toHaveValue('Existing Title')
    })

    /**
     * RED phase: Test that form enables submit button when initial values are valid
     * Expected to FAIL because validation doesn't check initial values yet
     */
    it('enables submit button when initial values are valid', () => {
      const mockOnSubmit = vi.fn()
      render(
        <PostForm
          onSubmit={mockOnSubmit}
          initialValues={{ slug: 'valid-slug', title: 'Valid Title' }}
        />
      )

      const submitButton = screen.getByTestId('post-form-submit')
      expect(submitButton).not.toBeDisabled()
    })
  })
})
