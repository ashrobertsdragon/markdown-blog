import { useRef, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { usePostComment } from '@/hooks/useComments'

export interface CommentFormProps {
  postSlug: string
  onCommentPosted?: () => void
}

const MAX_LENGTH = 5000

/**
 * Renders a comment submission form gated on authentication state.
 *
 * Uses an uncontrolled textarea with a ref so that test environments can
 * simulate typing via DOM events without re-render timing issues. Character
 * count is tracked separately via onChange to keep the counter reactive.
 *
 * Rate-limit errors surface a human-readable wait time when the error object
 * carries a `retryAfter` property, distinguishing them from generic failures
 * so users know exactly when they can retry.
 */
export function CommentForm({ postSlug, onCommentPosted }: CommentFormProps) {
  const { isSignedIn } = useAuth()
  const mutation = usePostComment()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [charCount, setCharCount] = useState(0)

  if (!isSignedIn) {
    return <p>Sign in to comment</p>
  }

  const isDisabled = charCount === 0 || charCount > MAX_LENGTH || mutation.isPending

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setCharCount(e.target.value.length)
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const text = textareaRef.current?.value ?? ''
    mutation.mutate(
      { slug: postSlug, text },
      {
        onSuccess: () => {
          if (textareaRef.current) {
            textareaRef.current.value = ''
          }
          setCharCount(0)
          onCommentPosted?.()
        },
      }
    )
  }

  const retryAfter = (mutation.error as Record<string, unknown> | null)?.retryAfter
  const errorMessage = retryAfter
    ? `Please wait ${retryAfter} seconds before posting again`
    : mutation.error?.message

  return (
    <form onSubmit={handleSubmit}>
      <textarea name="text" ref={textareaRef} onChange={handleChange} />
      <span>
        {charCount} / {MAX_LENGTH}
      </span>
      <button type="submit" disabled={isDisabled}>
        Submit
      </button>
      {mutation.isError && <p role="alert">{errorMessage}</p>}
    </form>
  )
}
