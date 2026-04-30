'use client'
import { createContext, useContext, useRef, useMemo } from 'react'

export type EditField = 'hours' | 'rate' | 'parts'

type VoiceContextValue = {
  registerSelectAgent: (fn: (name: string) => boolean) => void
  registerSendMessage: (fn: (text: string) => void) => void
  registerEditLine: (fn: (service: string, field: EditField, value: number) => void) => void
  registerAddLine: (fn: (service: string, hours: number, rate: number, parts: number) => void) => void
  selectAgent: (name: string) => boolean
  sendMessage: (text: string) => void
  editLine: (service: string, field: EditField, value: number) => void
  addLine: (service: string, hours: number, rate: number, parts: number) => void
}

const VoiceContext = createContext<VoiceContextValue | null>(null)

export function VoiceProvider({ children }: { children: React.ReactNode }) {
  const fns = useRef({
    selectAgent: null as ((name: string) => boolean) | null,
    sendMessage: null as ((text: string) => void) | null,
    editLine: null as ((service: string, field: EditField, value: number) => void) | null,
    addLine: null as ((service: string, hours: number, rate: number, parts: number) => void) | null,
  }).current

  const value = useMemo<VoiceContextValue>(() => ({
    registerSelectAgent: fn => { fns.selectAgent = fn },
    registerSendMessage: fn => { fns.sendMessage = fn },
    registerEditLine: fn => { fns.editLine = fn },
    registerAddLine: fn => { fns.addLine = fn },
    selectAgent: name => fns.selectAgent?.(name) ?? false,
    sendMessage: text => fns.sendMessage?.(text),
    editLine: (service, field, value) => fns.editLine?.(service, field, value),
    addLine: (service, hours, rate, parts) => fns.addLine?.(service, hours, rate, parts),
  }), []) // eslint-disable-line react-hooks/exhaustive-deps

  return <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>
}

export function useVoiceContext() {
  const ctx = useContext(VoiceContext)
  if (!ctx) throw new Error('useVoiceContext must be used within VoiceProvider')
  return ctx
}
