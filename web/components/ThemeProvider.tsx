'use client'

import { createContext, useContext, useEffect, useState } from 'react'

const STORAGE_KEY = 'accent'
const DEFAULT_ACCENT = '#d97706'

interface ThemeCtx {
  accent: string
  setAccent: (color: string) => void
}

const Ctx = createContext<ThemeCtx>({ accent: DEFAULT_ACCENT, setAccent: () => {} })

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [accent, setAccentState] = useState(DEFAULT_ACCENT)

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      setAccentState(saved)
      document.documentElement.style.setProperty('--accent', saved)
    }
  }, [])

  function setAccent(color: string) {
    setAccentState(color)
    localStorage.setItem(STORAGE_KEY, color)
    document.documentElement.style.setProperty('--accent', color)
  }

  return <Ctx.Provider value={{ accent, setAccent }}>{children}</Ctx.Provider>
}

export function useAccent() {
  return useContext(Ctx)
}
