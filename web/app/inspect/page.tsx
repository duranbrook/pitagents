'use client'

import { useState, useRef, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams, useRouter } from 'next/navigation'
import { AppShell } from '@/components/AppShell'
import {
  getCustomers,
  getVehicles,
  createSession,
  uploadSessionMedia,
  generateReport,
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

      const result = await generateReport(session_id)
      router.push(`/reports?id=${result.report_id}`)
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : 'Analysis failed. Please try again.')
      setAnalyzing(false)
    }
  }

  const selectedVehicle = vehicles.find(v => v.vehicle_id === selectedVehicleId)

  return (
    <AppShell>
      <div className="flex h-full overflow-hidden">
        {/* Left panel: vehicle picker */}
        <div className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col overflow-y-auto">
          <div className="p-3 border-b border-gray-800 flex-shrink-0">
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
                  className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded text-left hover:bg-gray-800 text-xs font-semibold text-gray-300 transition-colors"
                >
                  <span className="text-gray-500">
                    {selectedCustomerId === c.customer_id ? '▾' : '▸'}
                  </span>
                  <span className="truncate">{c.name}</span>
                </button>
                {selectedCustomerId === c.customer_id &&
                  vehicles.map(v => (
                    <button
                      key={v.vehicle_id}
                      onClick={() => setSelectedVehicleId(v.vehicle_id)}
                      className={`w-full flex items-center gap-2 pl-5 pr-2 py-1.5 rounded text-left text-xs transition-colors ${
                        selectedVehicleId === v.vehicle_id
                          ? 'bg-indigo-600/30 text-indigo-300'
                          : 'text-gray-400 hover:bg-gray-800'
                      }`}
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
        <div className="flex-1 bg-gray-950 overflow-y-auto">
          {!selectedVehicleId ? (
            <div className="flex h-full items-center justify-center text-gray-600 text-sm">
              Select a vehicle to start an inspection
            </div>
          ) : (
            <div className="p-6 max-w-2xl space-y-6">
              <div>
                <h1 className="text-xl font-semibold text-white">
                  {selectedVehicle
                    ? `${selectedVehicle.year} ${selectedVehicle.make} ${selectedVehicle.model}`
                    : 'Inspection'}
                </h1>
                <p className="text-sm text-gray-400 mt-0.5">
                  Upload inspection recording then photos
                </p>
              </div>

              {/* Audio upload */}
              <section className="border border-gray-700 rounded-xl p-5">
                <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                  Audio / Video Recording
                </p>
                {!audioFile ? (
                  <div
                    onClick={() => audioInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-700 rounded-xl p-8 text-center cursor-pointer hover:border-gray-500 transition-colors"
                  >
                    <p className="text-4xl mb-3">🎙</p>
                    <p className="text-gray-400 text-sm font-medium">
                      Drop audio or video, or click to browse
                    </p>
                    <p className="text-gray-600 text-xs mt-1">MP3, M4A, MP4, MOV, WAV</p>
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
                    <div className="flex items-center gap-3 bg-gray-800 rounded-lg p-3">
                      <span className="text-xl">🎙</span>
                      <p className="text-sm text-white flex-1 truncate">{audioFile.name}</p>
                      <button
                        onClick={() => {
                          setAudioFile(null)
                          setTranscript('')
                        }}
                        className="text-gray-500 hover:text-gray-300 text-sm"
                      >
                        ✕
                      </button>
                    </div>
                    {transcribing && (
                      <p className="text-xs text-gray-500">Transcribing preview…</p>
                    )}
                    {transcript && !transcribing && (
                      <div className="bg-gray-800 rounded-lg p-3">
                        <p className="text-xs text-gray-500 mb-1.5">Transcript preview</p>
                        <p className="text-xs text-gray-300 leading-relaxed line-clamp-6">
                          {transcript}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </section>

              {/* Photo upload */}
              <section className="border border-gray-700 rounded-xl p-5">
                <p className="text-xs text-gray-500 uppercase tracking-widest font-semibold mb-3">
                  Inspection Photos{' '}
                  <span className="normal-case font-normal text-gray-600">(optional, up to 20)</span>
                </p>
                <div className="flex flex-wrap gap-3">
                  {photoPreviews.map((src, i) => (
                    <div
                      key={i}
                      className="relative w-20 h-20 rounded-lg overflow-hidden bg-gray-800 border border-gray-700"
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
                      className="w-20 h-20 rounded-lg border-2 border-dashed border-gray-700 flex flex-col items-center justify-center text-gray-600 hover:text-gray-400 hover:border-gray-500 transition-colors text-xs gap-1"
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
                <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-4 py-3">
                  {analyzeError}
                </p>
              )}

              <button
                onClick={handleAnalyze}
                disabled={!audioFile || analyzing}
                className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-colors"
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
