import { z } from 'zod'
import { defineVoiceTool } from './defineVoiceTool'
import type { VoiceTool } from './types'
import type { EditField } from '@/contexts/VoiceContext'

const TAB_VALUES = ['customers', 'reports', 'inspect', 'chat'] as const

const TAB_ROUTES: Record<string, string> = {
  customers: '/customers',
  reports: '/reports',
  inspect: '/inspect',
  chat: '/chat',
}

export function createVoiceTools(dispatchers: {
  navigate: (path: string) => void
  selectAgent: (name: string) => boolean
  sendMessage: (text: string) => void
  selectCustomer: (name: string) => void
  selectReport: (query: string) => void
  editLine: (service: string, field: EditField, value: number) => void
  addLine: (service: string, hours: number, rate: number, parts: number) => void
  agentNames?: string[]
}): VoiceTool<any>[] {
  const agentList = dispatchers.agentNames ?? []
  const agentDesc = agentList.length > 0
    ? `Available agents: ${agentList.map(n => `"${n}"`).join(', ')}.`
    : 'Say the agent\'s role name.'
  return [
    defineVoiceTool({
      name: 'navigate_to_tab',
      description: 'Navigate to one of the four main tabs: customers, reports, inspect, or chat.',
      parameters: z.object({
        tab: z.enum(TAB_VALUES).describe('The tab to navigate to'),
      }),
      execute: ({ tab }) => {
        dispatchers.navigate(TAB_ROUTES[tab])
        return { ok: true, tab }
      },
    }),
    defineVoiceTool({
      name: 'scroll',
      description: 'Scroll the current page up or down. Use when the user says "scroll down", "scroll up", "go down", "go up", or similar.',
      parameters: z.object({
        direction: z.enum(['up', 'down']).describe('Direction to scroll'),
        amount: z.enum(['small', 'medium', 'large']).optional().describe('How far: small=200px, medium=500px, large=to bottom/top. Defaults to medium.'),
      }),
      execute: ({ direction, amount = 'medium' }) => {
        const distances: Record<string, number> = { small: 200, medium: 500, large: 99999 }
        const px = distances[amount] ?? 500
        const dy = direction === 'down' ? px : -px
        // Find the largest scrollable container — window.scrollBy won't work in fixed-layout apps
        const scrollable = Array.from(document.querySelectorAll<Element>('*'))
          .filter(el => {
            const s = window.getComputedStyle(el)
            return (s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight
          })
          .sort((a, b) => (b.clientHeight * b.scrollWidth) - (a.clientHeight * a.scrollWidth))[0]
        if (scrollable) {
          scrollable.scrollBy({ top: dy, behavior: 'smooth' })
        } else {
          window.scrollBy({ top: dy, behavior: 'smooth' })
        }
        return { ok: true, direction, amount }
      },
    }),
    defineVoiceTool({
      name: 'select_agent',
      description: `Switch to a chat agent by name. ${agentDesc}`,
      parameters: z.object({
        name: z.string().describe('Agent name or role, e.g. "Service Advisor", "Technician"'),
      }),
      execute: ({ name }) => {
        const ok = dispatchers.selectAgent(name)
        const available = agentList.length > 0 ? agentList.join(', ') : 'unknown'
        return ok ? { ok: true } : { ok: false, message: `No agent found matching "${name}". Available: ${available}.` }
      },
    }),
    defineVoiceTool({
      name: 'send_message',
      description: 'Send a message to the currently selected agent in the chat panel.',
      parameters: z.object({
        text: z.string().describe('The message to send'),
      }),
      execute: ({ text }) => {
        dispatchers.sendMessage(text)
        return { ok: true }
      },
    }),
    defineVoiceTool({
      name: 'select_customer',
      description: 'Navigate to the Customers tab and open a customer record by name. Use for "find customer X", "open X\'s record", "show me X", "do you have a customer named X".',
      parameters: z.object({
        name: z.string().describe('Customer name or partial name, e.g. "John Smith" or "Smith"'),
      }),
      execute: ({ name }) => {
        dispatchers.selectCustomer(name)
        return { ok: true, searching: name }
      },
    }),
    defineVoiceTool({
      name: 'select_report',
      description: 'Navigate to the Reports tab and open a report by vehicle or customer. Use for "do you have a report for X", "show me X\'s report", "find the report for [vehicle/customer]", "open the [year make model] report".',
      parameters: z.object({
        query: z.string().describe('Vehicle name, customer name, or description, e.g. "2019 Toyota Camry", "James", "Civic"'),
      }),
      execute: ({ query }) => {
        dispatchers.selectReport(query)
        return { ok: true, searching: query }
      },
    }),
    defineVoiceTool({
      name: 'edit_estimate_line',
      description: 'Edit hours, hourly rate, or parts cost on an existing estimate line. Use when the user says something like "change the brake line hours to 3" or "set oil change rate to 90".',
      parameters: z.object({
        service: z.string().describe('Partial service name to match, e.g. "brake" or "oil change"'),
        field: z.enum(['hours', 'rate', 'parts']).describe('"hours" for labor hours, "rate" for $/hr, "parts" for parts cost'),
        value: z.number().describe('New numeric value'),
      }),
      execute: ({ service, field, value }) => {
        dispatchers.editLine(service, field as EditField, value)
        return { ok: true, service, field, value }
      },
    }),
    defineVoiceTool({
      name: 'add_estimate_line',
      description: 'Add a new service line to the estimate. Use when the user says "add a service" or "add tire rotation".',
      parameters: z.object({
        service: z.string().describe('Service name, e.g. "Tire rotation"'),
        hours: z.number().describe('Labor hours'),
        rate: z.number().describe('Hourly labor rate in dollars'),
        parts: z.number().describe('Parts cost in dollars'),
      }),
      execute: ({ service, hours, rate, parts }) => {
        dispatchers.addLine(service, hours, rate, parts)
        return { ok: true, service }
      },
    }),
  ]
}
