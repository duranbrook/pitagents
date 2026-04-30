'use client'
import { createContext, useContext, useRef, useMemo } from 'react'

type VoiceContextValue = {
  registerSelectAgent: (fn: (name: string) => boolean) => void
  registerSendMessage: (fn: (text: string) => void) => void
  selectAgent: (name: string) => boolean
  sendMessage: (text: string) => void
}

const VoiceContext = createContext<VoiceContextValue | null>(null)

export function VoiceProvider({ children }: { children: React.ReactNode }) {
  const fns = useRef({
    selectAgent: null as ((name: string) => boolean) | null,
    sendMessage: null as ((text: string) => void) | null,
  }).current

  const value = useMemo<VoiceContextValue>(() => ({
    registerSelectAgent: fn => { fns.selectAgent = fn },
    registerSendMessage: fn => { fns.sendMessage = fn },
    selectAgent: name => fns.selectAgent?.(name) ?? false,
    sendMessage: text => fns.sendMessage?.(text),
  }), []) // eslint-disable-line react-hooks/exhaustive-deps

  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>
}

export function useVoiceContext() {
  const ctx = useContext(VoiceContext)
  if (!ctx) throw new Error('useVoiceContext must be used within VoiceProvider')
  return ctx
}
