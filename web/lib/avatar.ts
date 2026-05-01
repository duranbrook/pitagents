/**
 * Returns a Pravatar URL seeded from an ID string.
 * UUID hex chars have code points 48–102; % 70 + 1 maps to Pravatar's 1–70 range.
 */
export function pravatarUrl(id: string, size = 40): string {
  const img = (id.charCodeAt(0) % 70) + 1
  return `https://i.pravatar.cc/${size}?img=${img}`
}
