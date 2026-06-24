import { Loader2 } from 'lucide-react'
import { type ChangeEvent, type DragEvent, useRef } from 'react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/button'
import { useImageUpload } from '@/hooks/useImageUpload'

interface ImageUploadButtonProps {
  /** Post slug the uploaded image belongs to */
  slug: string
  /** Called with a markdown image string on successful upload */
  onInsert: (md: string) => void
}

/**
 * Button that triggers a hidden file input and uploads the selected image.
 *
 * On success, calls onInsert with a markdown image snippet and shows a
 * success toast. On failure, shows an error toast. Supports drag-and-drop
 * onto the button in addition to click-to-browse.
 */
export function ImageUploadButton({ slug, onInsert }: ImageUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const { uploadImage, isUploading } = useImageUpload(slug)

  async function handleFile(file: File) {
    try {
      const url = await uploadImage(file)
      onInsert(`![${file.name}](${url})`)
      toast.success('Image uploaded')
    } catch {
      toast.error('Image upload failed')
    }
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      void handleFile(file)
      e.target.value = ''
    }
  }

  function handleDragOver(e: DragEvent<HTMLButtonElement>) {
    e.preventDefault()
  }

  function handleDrop(e: DragEvent<HTMLButtonElement>) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) void handleFile(file)
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleChange}
        aria-label="Upload image"
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={isUploading}
        onClick={() => inputRef.current?.click()}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {isUploading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Uploading…
          </>
        ) : (
          'Insert image'
        )}
      </Button>
    </>
  )
}
