'use client'

/** Pick male (0) or female (1) based on a hash of the email string. */
function genderIndex(email: string): 0 | 1 {
  let h = 0
  for (let i = 0; i < email.length; i++) {
    h = (h * 31 + email.charCodeAt(i)) >>> 0
  }
  return (h % 2) as 0 | 1
}

function MaleIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="16" fill="#d97706" />
      {/* head */}
      <circle cx="16" cy="11" r="5" fill="white" />
      {/* shoulders — squared */}
      <path d="M7 28c0-5 4-8 9-8s9 3 9 8" fill="white" />
    </svg>
  )
}

function FemaleIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="16" fill="#7c3aed" />
      {/* head */}
      <circle cx="16" cy="11" r="5" fill="white" />
      {/* shoulders — rounded/narrower */}
      <path d="M9 28c0-4.5 3-7 7-7s7 2.5 7 7" fill="white" />
    </svg>
  )
}

export function PersonAvatar({ email, size = 32 }: { email: string; size?: number }) {
  const gender = email ? genderIndex(email) : 0
  return gender === 1
    ? <FemaleIcon size={size} />
    : <MaleIcon size={size} />
}

/** @deprecated use PersonAvatar */
export function pravatarUrl(id: string, size = 40): string {
  if (!id) return `https://i.pravatar.cc/${size}?img=1`
  const img = (id.charCodeAt(0) % 70) + 1
  return `https://i.pravatar.cc/${size}?img=${img}`
}
