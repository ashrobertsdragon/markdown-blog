import { type FormEvent, useState } from 'react'
import { cn } from '@/lib/utils'

/**
 * Props for the PostForm component
 */
interface PostFormProps {
  /** Callback invoked when form is submitted with valid data */
  onSubmit: (data: { slug: string; title: string }) => void
  /** Optional initial values for form fields */
  initialValues?: {
    slug?: string
    title?: string
  }
  /** Optional callback invoked whenever form values change */
  onChange?: (data: { slug: string; title: string }) => void
  /** Optional CSS class name to apply to the form container */
  className?: string
}

/**
 * Form validation error state
 */
interface ValidationErrors {
  slug?: string
  title?: string
}

/**
 * Base normalization for a slug:
 * - Converts to lowercase
 * - Replaces spaces with hyphens
 * - Removes special characters (keeps only alphanumeric and hyphens)
 * - Collapses consecutive hyphens
 * - Trims leading/trailing hyphens
 */
function baseNormalizeSlug(input: string): string {
  return input
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/**
 * Normalizes a slug according to requirement 8.1 and enforces max 200 character limit.
 */
function _normalizeSlug(input: string): string {
  return baseNormalizeSlug(input).slice(0, 200)
}

/**
 * Validates form data and returns errors
 */
function validateForm(slug: string, title: string): ValidationErrors {
  const errors: ValidationErrors = {}

  const trimmedSlug = slug.trim()
  if (!trimmedSlug) {
    errors.slug = 'Slug is required'
  } else if (trimmedSlug.length > 200) {
    errors.slug = 'Slug must not exceed 200 characters'
  }

  const trimmedTitle = title.trim()
  if (!trimmedTitle) {
    errors.title = 'Title is required'
  }

  return errors
}

/**
 * PostForm component for creating new blog posts
 *
 * Provides a form interface with slug and title fields.
 * Implements client-side slug validation per requirement 8.1:
 * - Lowercase conversion
 * - Space to hyphen conversion
 * - Special character removal
 * - Non-empty validation
 * - Max 200 character limit
 *
 * Submit button is disabled until both fields are valid.
 * Validation errors are shown inline with proper accessibility attributes.
 */
export function PostForm({ onSubmit, initialValues, onChange, className }: PostFormProps) {
  const [slug, setSlug] = useState(initialValues?.slug ?? '')
  const [title, setTitle] = useState(initialValues?.title ?? '')
  const [errors, setErrors] = useState<ValidationErrors>(() => {
    const initialSlug = initialValues?.slug ?? ''
    const initialTitle = initialValues?.title ?? ''
    return validateForm(initialSlug, initialTitle)
  })
  const [touched, setTouched] = useState({ slug: false, title: false })
  const [submitAttempted, setSubmitAttempted] = useState(false)

  const handleSlugChange = (value: string) => {
    const normalized = normalizeSlug(value)

    setSlug(normalized)
    setTouched(prev => ({ ...prev, slug: true }))

    const validationErrors = validateForm(normalized, title)

    if (baseNormalizeSlug(value).length > 200) {
      validationErrors.slug = 'Slug must not exceed 200 characters'
    }

    setErrors(validationErrors)

    if (onChange) {
      onChange({ slug: normalized, title })
    }
  }

  const handleTitleChange = (value: string) => {
    setTitle(value)
    setTouched(prev => ({ ...prev, title: true }))

    const validationErrors = validateForm(slug, value)
    setErrors(validationErrors)

    if (onChange) {
      onChange({ slug, title: value })
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    setSubmitAttempted(true)
    setTouched({ slug: true, title: true })

    const validationErrors = validateForm(slug, title)
    setErrors(validationErrors)

    if (Object.keys(validationErrors).length === 0) {
      try {
        onSubmit({ slug, title })
      } catch (error) {
        console.error('Error submitting form:', error)
      }
    }
  }

  const isValid = !errors.slug && !errors.title && slug.trim() !== '' && title.trim() !== ''
  const showSlugError = (touched.slug || submitAttempted) && errors.slug
  const showTitleError = (touched.title || submitAttempted) && errors.title

  return (
    <form onSubmit={handleSubmit} data-testid="post-form" className={cn('space-y-6', className)}>
      <div className="space-y-2">
        <label htmlFor="post-form-slug" className="block text-sm font-medium text-gray-700">
          Slug
        </label>
        <input
          id="post-form-slug"
          type="text"
          data-testid="post-form-slug-input"
          value={slug}
          onChange={e => handleSlugChange(e.target.value)}
          aria-invalid={showSlugError ? 'true' : 'false'}
          aria-describedby={showSlugError ? 'slug-error' : undefined}
          className={cn(
            'w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500',
            showSlugError && 'border-red-500 focus:border-red-500 focus:ring-red-500'
          )}
        />
        {showSlugError && (
          <p id="slug-error" data-testid="slug-error" className="text-sm text-red-600" role="alert">
            {errors.slug}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="post-form-title" className="block text-sm font-medium text-gray-700">
          Title
        </label>
        <input
          id="post-form-title"
          type="text"
          data-testid="post-form-title-input"
          value={title}
          onChange={e => handleTitleChange(e.target.value)}
          aria-invalid={showTitleError ? 'true' : 'false'}
          aria-describedby={showTitleError ? 'title-error' : undefined}
          className={cn(
            'w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500',
            showTitleError && 'border-red-500 focus:border-red-500 focus:ring-red-500'
          )}
        />
        {showTitleError && (
          <p
            id="title-error"
            data-testid="title-error"
            className="text-sm text-red-600"
            role="alert"
          >
            {errors.title}
          </p>
        )}
      </div>

      <button
        type="submit"
        data-testid="post-form-submit"
        disabled={!isValid}
        className={cn(
          'rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
          isValid ? 'hover:bg-blue-700' : 'cursor-not-allowed opacity-50'
        )}
      >
        Create Post
      </button>
    </form>
  )
}
