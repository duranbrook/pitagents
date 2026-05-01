'use client'

import { useState, useEffect } from 'react'

export type BgTheme = 'dark' | 'moody' | 'vivid'

const OVERLAYS: Record<BgTheme, string> = {
  dark: 'rgba(0,0,0,0.78)',
  moody: 'rgba(0,0,0,0.62)',
  vivid: 'rgba(0,0,0,0.22)',
}

function applyOverlay(theme: BgTheme) {
  document.documentElement.style.setProperty('--bg-overlay', OVERLAYS[theme])
}

export function useTheme() {
  const [theme, setThemeState] = useState<BgTheme>('moody')

  useEffect(() => {
    const saved = localStorage.getItem('bgTheme') as BgTheme | null
    const initial: BgTheme = saved && OVERLAYS[saved] ? saved : 'moody'
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
