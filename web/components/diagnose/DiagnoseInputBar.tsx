'use client'
import { useState } from 'react'

interface Props {
  onAnalyze: (params: { year: number; make: string; model: string; mileage: number; dtcs: string[] }) => void
  loading: boolean
}

export function DiagnoseInputBar({ onAnalyze, loading }: Props) {
  const [year, setYear] = useState('')
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [mileage, setMileage] = useState('')
  const [dtcInput, setDtcInput] = useState('')
  const [dtcs, setDtcs] = useState<string[]>([])

  const addDtc = () => {
    const code = dtcInput.trim().toUpperCase()
    if (code && !dtcs.includes(code)) {
      setDtcs(prev => [...prev, code])
    }
    setDtcInput('')
  }

  const removeDtc = (code: string) => setDtcs(prev => prev.filter(d => d !== code))

  const handleAnalyze = () => {
    if (!year || !make || !model) return
    onAnalyze({ year: parseInt(year), make, model, mileage: parseInt(mileage) || 0, dtcs })
  }

  const inputStyle = {
    background: '#1a1a1a',
    border: '1px solid #333',
    color: '#fff',
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '14px',
    outline: 'none',
  }

  return (
    <div style={{ background: '#141414', border: '1px solid #222', borderRadius: '10px', padding: '20px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
        <input
          placeholder="Year"
          value={year}
          onChange={e => setYear(e.target.value)}
          style={{ ...inputStyle, width: '80px' }}
          type="number"
        />
        <input
          placeholder="Make (e.g. Toyota)"
          value={make}
          onChange={e => setMake(e.target.value)}
          style={{ ...inputStyle, flex: 1, minWidth: '140px' }}
        />
        <input
          placeholder="Model (e.g. Camry)"
          value={model}
          onChange={e => setModel(e.target.value)}
          style={{ ...inputStyle, flex: 1, minWidth: '140px' }}
        />
        <input
          placeholder="Mileage"
          value={mileage}
          onChange={e => setMileage(e.target.value)}
          style={{ ...inputStyle, width: '120px' }}
          type="number"
        />
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: dtcs.length ? '12px' : '0', flexWrap: 'wrap' }}>
        <input
          placeholder="DTC code (e.g. P0300)"
          value={dtcInput}
          onChange={e => setDtcInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addDtc()}
          style={{ ...inputStyle, flex: 1, minWidth: '200px' }}
        />
        <button onClick={addDtc} style={{ background: '#222', border: '1px solid #333', color: '#aaa', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer', fontSize: '14px' }}>
          + Add Code
        </button>
        <button
          onClick={handleAnalyze}
          disabled={loading || !year || !make || !model}
          style={{
            background: loading ? '#333' : '#d97706',
            color: '#000',
            border: 'none',
            borderRadius: '6px',
            padding: '8px 24px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: '14px',
          }}
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {dtcs.length > 0 && (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {dtcs.map(code => (
            <span
              key={code}
              style={{ background: '#1f2937', color: '#fbbf24', border: '1px solid #374151', borderRadius: '20px', padding: '4px 12px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {code}
              <button onClick={() => removeDtc(code)} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '14px', lineHeight: 1 }}>×</button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
