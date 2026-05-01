'use client'
import { useState } from 'react'
import { DiagnoseInputBar } from '@/components/diagnose/DiagnoseInputBar'
import { DiagnoseTabs } from '@/components/diagnose/DiagnoseTabs'
import { DiagnoseActionPanel } from '@/components/diagnose/DiagnoseActionPanel'
import {
  diagnoseAnalyze,
  diagnoseTsb,
  diagnoseRecalls,
  diagnoseMaintenance,
} from '@/lib/api'
import type { DiagnosisItem, RepairPlanItem, TsbItem, RecallItem, MaintenanceItem } from '@/lib/types'

type Tab = 'diagnosis' | 'repair' | 'tsb' | 'recalls' | 'maintenance'

interface VehicleContext {
  year: number
  make: string
  model: string
  mileage: number
  dtcs: string[]
}

export default function DiagnosePage() {
  const [activeTab, setActiveTab] = useState<Tab>('diagnosis')
  const [diagnosis, setDiagnosis] = useState<DiagnosisItem[]>([])
  const [repairPlan, setRepairPlan] = useState<RepairPlanItem[]>([])
  const [tsbs, setTsbs] = useState<TsbItem[]>([])
  const [recalls, setRecalls] = useState<RecallItem[]>([])
  const [maintenance, setMaintenance] = useState<MaintenanceItem[]>([])
  const [analyzing, setAnalyzing] = useState(false)

  const hasOpenRecall = recalls.length > 0

  const handleAnalyze = async (params: VehicleContext) => {
    setAnalyzing(true)
    try {
      const [analyzeResult, tsbResult, recallResult, maintenanceResult] = await Promise.all([
        diagnoseAnalyze(params),
        diagnoseTsb(params.year, params.make, params.model),
        diagnoseRecalls(params.year, params.make, params.model),
        diagnoseMaintenance(params.year, params.make, params.model, params.mileage),
      ])
      setDiagnosis(analyzeResult.diagnosis)
      setRepairPlan(analyzeResult.repair_plan)
      setTsbs(tsbResult.tsbs)
      setRecalls(recallResult.recalls)
      setMaintenance(maintenanceResult.maintenance)
    } catch (_) {
      // partial results ok
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div style={{ background: '#0d0d0d', minHeight: '100vh', padding: '32px', color: '#fff', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#f9fafb', marginBottom: '8px' }}>Diagnose</h1>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '24px' }}>Vehicle diagnostic lookup powered by CarMD</p>

      <DiagnoseInputBar onAnalyze={handleAnalyze} loading={analyzing} />

      {hasOpenRecall && (
        <div style={{ background: '#450a0a', border: '1px solid #7f1d1d', borderRadius: '8px', padding: '12px 16px', marginBottom: '20px', color: '#fca5a5', fontWeight: 600, fontSize: '14px' }}>
          ⚠ Open NHTSA Safety Recall — See Recalls tab for details
        </div>
      )}

      <div style={{ display: 'flex', gap: '32px', alignItems: 'flex-start' }}>
        <DiagnoseTabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          diagnosis={diagnosis}
          repairPlan={repairPlan}
          tsbs={tsbs}
          recalls={recalls}
          maintenance={maintenance}
          loading={analyzing}
        />
        <DiagnoseActionPanel
          diagnosis={diagnosis}
          repairPlan={repairPlan}
          jobCardId={null}
          customerId={null}
        />
      </div>
    </div>
  )
}
