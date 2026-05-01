/**
 * Returns a Pravatar URL seeded from an ID string.
 * For UUID inputs, the first character is always a hex digit (0–9, a–f),
 * yielding 16 consistent avatar indices. Non-UUID IDs get broader coverage.
 */
export function pravatarUrl(id: string, size = 40): string {
  if (!id) return `https://i.pravatar.cc/${size}?img=1`
  const img = (id.charCodeAt(0) % 70) + 1
  return `https://i.pravatar.cc/${size}?img=${img}`
}
