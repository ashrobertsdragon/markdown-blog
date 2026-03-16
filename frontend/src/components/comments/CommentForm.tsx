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
 * Rate-limit errors (429) surface the API error message directly so users
 * see the "Too many comments" text from the backend. A 202 response means
 * the comment was accepted but is pending moderation — shown as an info
 * message rather than an error.
 */
export function CommentForm({ postSlug, onCommentPosted }: CommentFormProps) {
  const { isSignedIn } = useAuth()
  const mutation = usePostComment()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [charCount, setCharCount] = useState(0)
  const [pendingModeration, setPendingModeration] = useState(false)

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
    setPendingModeration(false)
    mutation.mutate(
      { slug: postSlug, text },
      {
        onSuccess: data => {
          const isPending = data?.status === 'pending' || typeof data?.message === 'string'
          if (isPending) {
            setPendingModeration(true)
          }
          if (textareaRef.current) {
            textareaRef.current.value = ''
          }
          setCharCount(0)
          if (!isPending) {
            onCommentPosted?.()
          }
        },
      }
    )
  }

  const retryAfter = (mutation.error as Record<string, unknown> | null)?.retryAfter
  const errorMessage =
    mutation.error?.message ??
    (retryAfter ? `Please wait ${retryAfter} seconds before posting again` : undefined)

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        name="text"
        ref={textareaRef}
        onChange={handleChange}
        placeholder="Leave a comment..."
      />
      <span>
        {charCount} / {MAX_LENGTH}
      </span>
      <button type="submit" disabled={isDisabled}>
        Post Comment
      </button>
      {mutation.isError && <p role="alert">{errorMessage}</p>}
      {pendingModeration && <output>Your comment is pending moderation</output>}
    </form>
  )
}
