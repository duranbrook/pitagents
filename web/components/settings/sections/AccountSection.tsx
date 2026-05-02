'use client'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMe, updateProfile, updatePassword } from '@/lib/api'

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '8px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
  letterSpacing: '.07em', color: 'rgba(255,255,255,0.3)', marginBottom: 10,
}

function SaveButton({ label, pending }: { label: string; pending: boolean }) {
  return (
    <button
      type="submit"
      disabled={pending}
      style={{
        background: 'var(--accent)', color: '#000', border: 'none',
        borderRadius: 6, padding: '7px 16px', fontSize: 12, fontWeight: 700,
        cursor: pending ? 'not-allowed' : 'pointer', opacity: pending ? 0.6 : 1,
      }}
    >
      {pending ? 'Saving…' : label}
    </button>
  )
}

function InlineMsg({ msg }: { msg: { type: 'ok' | 'err'; text: string } | null }) {
  if (!msg) return null
  return (
    <div style={{
      fontSize: 11, marginTop: 8,
      color: msg.type === 'ok' ? 'rgba(74,222,128,0.9)' : 'rgba(239,68,68,0.9)',
    }}>
      {msg.text}
    </div>
  )
}

export function AccountSection() {
  const qc = useQueryClient()
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: getMe })

  const [name, setName] = useState('')
  const [profileMsg, setProfileMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' })
  const [pwdMsg, setPwdMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    if (user) setName(user.name ?? '')
  }, [user])

  const saveProfile = useMutation({
    mutationFn: () => updateProfile(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me'] })
      setProfileMsg({ type: 'ok', text: 'Saved' })
      setTimeout(() => setProfileMsg(null), 2500)
    },
    onError: (e: Error) => setProfileMsg({ type: 'err', text: e.message }),
  })

  const changePwd = useMutation({
    mutationFn: () => {
      if (pwd.next !== pwd.confirm) throw new Error("Passwords don't match")
      if (pwd.next.length < 8) throw new Error('New password must be at least 8 characters')
      return updatePassword(pwd.current, pwd.next)
    },
    onSuccess: () => {
      setPwd({ current: '', next: '', confirm: '' })
      setPwdMsg({ type: 'ok', text: 'Password changed' })
      setTimeout(() => setPwdMsg(null), 2500)
    },
    onError: (e: Error) => setPwdMsg({ type: 'err', text: e.message }),
  })

  return (
    <div>
      {/* Profile */}
      <div style={sectionHeadingStyle}>Profile</div>
      <form
        onSubmit={e => { e.preventDefault(); saveProfile.mutate() }}
        style={{ marginBottom: 24 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
            background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ color: '#000', fontSize: 12, fontWeight: 700 }}>
              {(user?.name || user?.email || '?')[0].toUpperCase()}
            </span>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Display name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              style={fieldStyle}
              placeholder="Your name"
            />
          </div>
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>Email</label>
          <input
            value={user?.email ?? ''}
            readOnly
            style={{ ...fieldStyle, color: 'rgba(255,255,255,0.35)', cursor: 'default' }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <SaveButton label="Save Profile" pending={saveProfile.isPending} />
        </div>
        <InlineMsg msg={profileMsg} />
      </form>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', marginBottom: 20 }} />

      {/* Security */}
      <div style={sectionHeadingStyle}>Security</div>
      <form onSubmit={e => { e.preventDefault(); changePwd.mutate() }}>
        <div style={{ marginBottom: 8 }}>
          <label style={labelStyle}>Current password</label>
          <input
            type="password"
            value={pwd.current}
            onChange={e => setPwd(p => ({ ...p, current: e.target.value }))}
            style={fieldStyle}
            autoComplete="current-password"
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <label style={labelStyle}>New password</label>
          <input
            type="password"
            value={pwd.next}
            onChange={e => setPwd(p => ({ ...p, next: e.target.value }))}
            style={fieldStyle}
            autoComplete="new-password"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>Confirm new password</label>
          <input
            type="password"
            value={pwd.confirm}
            onChange={e => setPwd(p => ({ ...p, confirm: e.target.value }))}
            style={fieldStyle}
            autoComplete="new-password"
          />
        </div>
        <SaveButton label="Change Password" pending={changePwd.isPending} />
        <InlineMsg msg={pwdMsg} />
      </form>
    </div>
  )
}
