'use client'

import { useState, useEffect } from 'react'

export type BgTheme = 'dark' | 'moody' | 'vivid'

const OVERLAYS: Record<BgTheme, string> = {
  dark: 'rgba(0,0,0,0.78)',
  moody: 'rgba(0,0,0,0.62)',
  vivid: 'rgba(0,0,0,0.22)',
}

const VALID_THEMES = new Set<string>(['dark', 'moody', 'vivid'])

function applyOverlay(theme: BgTheme) {
  document.documentElement.style.setProperty('--bg-overlay', OVERLAYS[theme])
}

export function useTheme() {
  const [theme, setThemeState] = useState<BgTheme>('moody')

  useEffect(() => {
    const saved = localStorage.getItem('bgTheme')
    const initial: BgTheme = saved && VALID_THEMES.has(saved) ? (saved as BgTheme) : 'moody'
    setThemeState(initial)
    applyOverlay(initial)
  }, [])

  function setTheme(t: BgTheme) {
    setThemeState(t)
    applyOverlay(t)
    localStorage.setItem('bgTheme', t)
  }

  return { theme, setTheme }
}
