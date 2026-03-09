import { useRef, useState } from 'react'
import { useReplyToComment } from '@/hooks/useComments'
import type { CommentResponse } from '@/services/commentsApi'

export interface ReplyFormProps {
  parentComment: CommentResponse
  postSlug: string
  onCancel: () => void
}

const MAX_LENGTH = 5000

/**
 * Form for replying to an existing comment.
 *
 * Pre-fills the mention with the parent comment author and follows
 * the same validation patterns as CommentForm (character limits,
 * rate limiting, error handling).
 */
export function ReplyForm({ parentComment, postSlug, onCancel }: ReplyFormProps) {
  const mutation = useReplyToComment()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [charCount, setCharCount] = useState(0)

  const parentMention = `@comment${parentComment.id} `
  const isDisabled =
    charCount === 0 || charCount + parentMention.length > MAX_LENGTH || mutation.isPending

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setCharCount(e.target.value.replace(parentMention, '').length)
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fullText = textareaRef.current?.value ?? ''
    const replyText = fullText.replace(parentMention, '')

    if (!replyText.trim()) return

    mutation.mutate(
      { slug: postSlug, parentId: parentComment.id, text: fullText },
      {
        onSuccess: () => {
          onCancel()
        },
      }
    )
  }

  const retryAfter = (mutation.error as Record<string, unknown> | null)?.retryAfter
  const errorMessage = retryAfter
    ? `Please wait ${retryAfter} seconds before posting again`
    : mutation.error?.message

  return (
    <form onSubmit={handleSubmit} className="reply-form">
      <textarea
        name="reply-text"
        ref={textareaRef}
        onChange={handleChange}
        defaultValue={parentMention}
        placeholder="Write your reply..."
        className="w-full p-2 border rounded text-sm"
        rows={3}
      />
      <span className="text-xs text-gray-500">
        {charCount} / {MAX_LENGTH - parentMention.length}
      </span>
      <div className="flex gap-2 mt-2">
        <button
          type="submit"
          disabled={isDisabled}
          className="px-3 py-1 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
        >
          Reply
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1 bg-gray-300 text-gray-800 rounded text-sm hover:bg-gray-400"
        >
          Cancel
        </button>
      </div>
      {mutation.isError && (
        <p role="alert" className="text-red-600 text-sm mt-2">
          {errorMessage}
        </p>
      )}
    </form>
  )
}
