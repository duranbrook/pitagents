'use client'

import { useRef, useState } from 'react'
import { uploadImage } from '@/lib/api'

interface Props {
  onImageUrl: (url: string) => void
  disabled?: boolean
}

export function ImageAttach({ onImageUrl, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const url = await uploadImage(file)
      onImageUrl(url)
    } catch (err) {
      console.error('Image upload failed:', err)
      alert('Image upload failed. Please try again.')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const isDisabled = disabled || uploading

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif"
        className="hidden"
        onChange={handleChange}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isDisabled}
        title={uploading ? 'Uploading…' : 'Attach image'}
        className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors flex-shrink-0 ${
          uploading
            ? 'bg-indigo-700 text-white animate-pulse'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </button>
    </>
  )
}
