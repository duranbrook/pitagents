'use client'

import { useRef, useState } from 'react'
import { transcribeAudio } from '@/lib/api'

interface Props {
  mode: 'hold' | 'toggle'
  onTranscript: (text: string) => void
  disabled?: boolean
}

export function VoiceButton({ mode, onTranscript, disabled }: Props) {
  const [recording, setRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const [permError, setPermError] = useState(false)
  const [hint, setHint] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startTimeRef = useRef<number>(0)

  async function startRecording() {
    setPermError(false)
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setPermError(true)
      return
    }

    // Pick the first mimeType the browser actually supports
    const PREFERRED = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
    const mimeType = PREFERRED.find(t => MediaRecorder.isTypeSupported(t)) ?? ''

    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    chunksRef.current = []
    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const duration = Date.now() - startTimeRef.current
      if (duration < 400) {
        setHint('Hold longer while speaking')
        setTimeout(() => setHint(null), 2500)
        return
      }
      const actualType = recorder.mimeType || mimeType || 'audio/webm'
      const blob = new Blob(chunksRef.current, { type: actualType })
      if (blob.size < 100) {
        setHint('No audio captured')
        setTimeout(() => setHint(null), 2500)
        return
      }
      setLoading(true)
      try {
        const transcript = await transcribeAudio(blob)
        if (transcript) {
          onTranscript(transcript)
        } else {
          setHint('No speech detected')
          setTimeout(() => setHint(null), 2500)
        }
      } finally {
        setLoading(false)
      }
    }
    startTimeRef.current = Date.now()
    recorder.start()
    recorderRef.current = recorder
    setRecording(true)
  }

  function stopRecording() {
    recorderRef.current?.stop()
    recorderRef.current = null
    setRecording(false)
  }

  // Hold mode: mousedown/touchstart to start, mouseup/touchend to stop
  const holdHandlers = mode === 'hold' ? {
    onMouseDown: () => !disabled && startRecording(),
    onMouseUp: stopRecording,
    onMouseLeave: () => recording && stopRecording(),
    onTouchStart: (e: React.TouchEvent) => { e.preventDefault(); !disabled && startRecording() },
    onTouchEnd: stopRecording,
  } : {}

  // Toggle mode: click to start/stop
  const handleClick = mode === 'toggle' ? () => {
    if (disabled) return
    recording ? stopRecording() : startRecording()
  } : undefined

  const isActive = recording || loading
  return (
    <div className="relative flex-shrink-0">
      <button
        type="button"
        onClick={handleClick}
        {...holdHandlers}
        disabled={disabled || loading}
        title={
          permError
            ? 'Microphone access denied'
            : mode === 'hold'
            ? 'Hold to record'
            : recording
            ? 'Tap to stop'
            : 'Tap to record'
        }
        className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
          permError
            ? 'bg-red-900 text-red-400'
            : loading
            ? 'bg-yellow-500 text-white animate-pulse'
            : isActive
            ? 'bg-red-500 text-white scale-110'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        {loading ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2H3v2a9 9 0 0 0 8 8.94V22H9v2h6v-2h-2v-1.06A9 9 0 0 0 21 12v-2h-2z"/>
          </svg>
        )}
      </button>
      {(permError || hint) && (
        <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-800 text-xs px-2 py-1 rounded whitespace-nowrap" style={{ color: permError ? '#f87171' : '#facc15' }}>
          {permError ? 'Mic access denied' : hint}
        </div>
      )}
    </div>
  )
}
