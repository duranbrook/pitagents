'use client'

import { useState, useEffect } from 'react'

export type BgTheme = 'dark' | 'moody' | 'vivid'

const OVERLAYS: Record<BgTheme, string> = {
  dark: 'rgba(0,0,0,0.78)',
  moody: 'rgba(0,0,0,0.62)',
  vivid: 'rgba(0,0,0,0.22)',
}

const VALID_THEMES = new Set(['dark', 'moody', 'vivid'])

function applyOverlay(theme: BgTheme) {
  document.documentElement.style.setProperty('--bg-overlay', OVERLAYS[theme])
}

export function useTheme() {
  const [theme, setThemeState] = useState<BgTheme>(() => {
    if (typeof window === 'undefined') return 'moody'
    const saved = localStorage.getItem('bg-theme')
    return (saved && VALID_THEMES.has(saved) ? saved : 'moody') as BgTheme
  })

  // Apply the CSS overlay on mount only
  useEffect(() => {
    applyOverlay(theme)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function setTheme(t: BgTheme) {
    setThemeState(t)
    localStorage.setItem('bg-theme', t)
    applyOverlay(t)
  }

  return { theme, setTheme }
}
