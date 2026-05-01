'use client'

import { useState, useRef, useEffect, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import {
  getCustomers,
  getVehicles,
  createSession,
  uploadSessionMedia,
  createQuote,
  transcribeAudio,
} from '@/lib/api'
import type { Customer, Vehicle } from '@/lib/types'

function InspectPageInner() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const preselectedCustomer = searchParams.get('customer')

  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(preselectedCustomer)
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null)
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [transcript, setTranscript] = useState<string>('')
  const [transcribing, setTranscribing] = useState(false)
  const [photos, setPhotos] = useState<File[]>([])
  const [photoPreviews, setPhotoPreviews] = useState<string[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)

  const audioInputRef = useRef<HTMLInputElement>(null)
  const photoInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    return () => {
      photoPreviews.forEach(url => URL.revokeObjectURL(url))
    }
  }, [photoPreviews])

  const { data: customers = [] } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: getCustomers,
  })

  const { data: vehicles = [] } = useQuery<Vehicle[]>({
    queryKey: ['vehicles', selectedCustomerId],
    queryFn: () => getVehicles(selectedCustomerId!),
    enabled: !!selectedCustomerId,
  })

  async function handleAudioChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setAudioFile(file)
    setTranscript('')
    setTranscribing(true)
    try {
      const text = await transcribeAudio(file)
      setTranscript(text)
    } catch {
      // Transcript preview is best-effort; analysis still works without it
      setTranscript('')
    } finally {
      setTranscribing(false)
    }
  }

  function handlePhotosChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? [])
    const remaining = 20 - photos.length
    const toAdd = files.slice(0, remaining)
    setPhotos(prev => [...prev, ...toAdd])
    setPhotoPreviews(prev => [...prev, ...toAdd.map(f => URL.createObjectURL(f))])
    e.target.value = ''
  }

  function removePhoto(index: number) {
    URL.revokeObjectURL(photoPreviews[index])
    setPhotos(prev => prev.filter((_, i) => i !== index))
    setPhotoPreviews(prev => prev.filter((_, i) => i !== index))
  }

  async function handleAnalyze() {
    if (!selectedVehicleId || !audioFile) return
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      const { session_id } = await createSession(selectedVehicleId)

      // Determine media type from file mime
      const isVideo = audioFile.type.startsWith('video/')
      await uploadSessionMedia(session_id, audioFile, isVideo ? 'video' : 'audio')

      for (const photo of photos) {
        await uploadSessionMedia(session_id, photo, 'photo')
      }

      const quote = await createQuote(session_id, transcript)
      router.push(`/quotes/${quote.quote_id}`)
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : 'Analysis failed. Please try again.')
      setAnalyzing(false)
    }
  }

  const selectedVehicle = vehicles.find(v => v.vehicle_id === selectedVehicleId)

  return (
    <AppShell>
      <div className="flex h-full" style={{ padding: 16, gap: 12 }}>
        {/* Left panel: vehicle picker */}
        <div
          className="glass-panel flex-shrink-0 flex flex-col overflow-y-auto"
          style={{ width: 220, borderRadius: 12 }}
        >
          <div
            className="p-3 flex-shrink-0"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
          >
            <span className="text-sm font-semibold text-white">Pick Vehicle</span>
          </div>
          <div className="flex-1 p-2">
            {customers.map(c => (
              <div key={c.customer_id}>
                <button
                  onClick={() =>
                    setSelectedCustomerId(
                      c.customer_id === selectedCustomerId ? null : c.customer_id,
                    )
                  }
                  className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded text-left text-xs font-semibold transition-colors"
                  style={{ color: 'rgba(255,255,255,0.7)' }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
                >
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>
                    {selectedCustomerId === c.customer_id ? '▾' : '▸'}
                  </span>
                  <span className="truncate">{c.name}</span>
                </button>
                {selectedCustomerId === c.customer_id &&
                  vehicles.map(v => (
                    <button
                      key={v.vehicle_id}
                      onClick={() => setSelectedVehicleId(v.vehicle_id)}
                      className="w-full flex items-center gap-2 pl-5 pr-2 py-1.5 rounded text-left text-xs transition-colors"
                      style={selectedVehicleId === v.vehicle_id
                        ? { background: 'rgba(99,102,241,0.25)', color: 'rgba(165,180,252,1)' }
                        : { color: 'rgba(255,255,255,0.45)' }}
                      onMouseEnter={e => { if (selectedVehicleId !== v.vehicle_id) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)' }}
                      onMouseLeave={e => { if (selectedVehicleId !== v.vehicle_id) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                    >
                      <span>🚗</span>
                      <span className="truncate">
                        {v.year} {v.make} {v.model}
                      </span>
                    </button>
                  ))}
              </div>
            ))}
          </div>
        </div>

        {/* Right panel: upload flow */}
        <div className="glass-panel flex-1 overflow-y-auto" style={{ borderRadius: 12, padding: '20px 24px' }}>
          {!selectedVehicleId ? (
            <div className="flex h-full items-center justify-center text-sm" style={{ color: 'rgba(255,255,255,0.25)' }}>
              Select a vehicle to start an inspection
            </div>
          ) : (
            <div className="max-w-2xl space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {selectedVehicle
                    ? `${selectedVehicle.year} ${selectedVehicle.make} ${selectedVehicle.model}`
                    : 'Inspection'}
                </h1>
                <p className="text-sm mt-0.5" style={{ color: 'rgba(255,255,255,0.45)' }}>
                  Upload inspection recording then photos
                </p>
              </div>

              {/* Audio upload */}
              <section className="glass-card rounded-xl p-5">
                <p
                  className="text-xs uppercase tracking-widest font-semibold mb-3"
                  style={{ color: 'rgba(255,255,255,0.3)' }}
                >
                  Audio / Video Recording
                </p>
                {!audioFile ? (
                  <div
                    onClick={() => audioInputRef.current?.click()}
                    className="rounded-xl p-8 text-center cursor-pointer transition-colors"
                    style={{ border: '2px dashed rgba(255,255,255,0.15)' }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.3)'}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.15)'}
                  >
                    <p className="text-4xl mb-3">🎙</p>
                    <p className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.55)' }}>
                      Drop audio or video, or click to browse
                    </p>
                    <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.25)' }}>MP3, M4A, MP4, MOV, WAV</p>
                    <input
                      ref={audioInputRef}
                      type="file"
                      accept="audio/*,video/mp4,video/quicktime,video/webm"
                      onChange={handleAudioChange}
                      className="hidden"
                    />
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div
                      className="flex items-center gap-3 rounded-lg p-3"
                      style={{ background: 'rgba(255,255,255,0.06)' }}
                    >
                      <span className="text-xl">🎙</span>
                      <p className="text-sm text-white flex-1 truncate">{audioFile.name}</p>
                      <button
                        onClick={() => {
                          setAudioFile(null)
                          setTranscript('')
                        }}
                        className="text-sm transition-colors"
                        style={{ color: 'rgba(255,255,255,0.35)' }}
                        onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.7)'}
                        onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.35)'}
                      >
                        ✕
                      </button>
                    </div>
                    {transcribing && (
                      <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>Transcribing preview…</p>
                    )}
                    {transcript && !transcribing && (
                      <div className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.06)' }}>
                        <p className="text-xs mb-1.5" style={{ color: 'rgba(255,255,255,0.35)' }}>Transcript preview</p>
                        <p className="text-xs leading-relaxed line-clamp-6" style={{ color: 'rgba(255,255,255,0.6)' }}>
                          {transcript}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </section>

              {/* Photo upload */}
              <section className="glass-card rounded-xl p-5">
                <p
                  className="text-xs uppercase tracking-widest font-semibold mb-3"
                  style={{ color: 'rgba(255,255,255,0.3)' }}
                >
                  Inspection Photos{' '}
                  <span className="normal-case font-normal" style={{ color: 'rgba(255,255,255,0.2)' }}>(optional, up to 20)</span>
                </p>
                <div className="flex flex-wrap gap-3">
                  {photoPreviews.map((src, i) => (
                    <div
                      key={i}
                      className="relative w-20 h-20 rounded-lg overflow-hidden"
                      style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                    >
                      <img
                        src={src}
                        alt={`Photo ${i + 1}`}
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={() => removePhoto(i)}
                        className="absolute top-0.5 right-0.5 bg-black/70 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center hover:bg-black"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  {photos.length < 20 && (
                    <button
                      onClick={() => photoInputRef.current?.click()}
                      className="w-20 h-20 rounded-lg flex flex-col items-center justify-center transition-colors text-xs gap-1"
                      style={{ border: '2px dashed rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.3)' }}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.3)'
                        ;(e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.6)'
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.15)'
                        ;(e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.3)'
                      }}
                    >
                      <span className="text-xl">+</span>
                      <span>Add</span>
                      <input
                        ref={photoInputRef}
                        type="file"
                        accept="image/*"
                        multiple
                        onChange={handlePhotosChange}
                        className="hidden"
                      />
                    </button>
                  )}
                </div>
              </section>

              {analyzeError && (
                <p
                  className="text-sm rounded-lg px-4 py-3"
                  style={{ color: '#f87171', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}
                >
                  {analyzeError}
                </p>
              )}

              <button
                onClick={handleAnalyze}
                disabled={!audioFile || !selectedVehicleId || analyzing}
                className="w-full text-white font-semibold py-3 rounded-xl transition-opacity"
                style={{ background: 'var(--accent)', opacity: (!audioFile || !selectedVehicleId || analyzing) ? 0.5 : 1 }}
              >
                {analyzing ? '⏳ Analyzing… (~30 seconds)' : '▶ Analyze Inspection'}
              </button>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}

export default function InspectPage() {
  return (
    <Suspense>
      <InspectPageInner />
    </Suspense>
  )
}
