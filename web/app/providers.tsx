'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { ThemeProvider } from '@/components/ThemeProvider'
import { VoiceProvider } from '@/contexts/VoiceContext'

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient())
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <VoiceProvider>{children}</VoiceProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
