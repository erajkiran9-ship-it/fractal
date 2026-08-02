import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Calendar,
  ChevronRight,
  Play,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react'
import api from '../api/client'
import {
  Customer,
  Workflow,
  AgentResult,
  SystemState,
  AgingSummary,
} from '../types/index'

function parseWorkflowPlan(plan: unknown): Record<string, any> | null {
  let parsed = plan
  for (let depth = 0; depth < 3 && typeof parsed === 'string'; depth += 1) {
    try {
      parsed = JSON.parse(parsed)
    } catch {
      const text = String(parsed).trim()
      if (text.startsWith('{\\"') || text.startsWith('[\\"')) {
        parsed = text.replace(/\\"/g, '"')
        continue
      }
      return null
    }
  }
  return parsed && typeof parsed === 'object'
    ? (parsed as Record<string, any>)
    : null
}

type PlanActionRow = {
  action: string
  date?: string
  details?: string
  status: string
}

function humanize(value: unknown): string {
  if (!value) return 'Unspecified action'
  return String(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatPlanDate(value?: string): string {
  if (!value) return '—'
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return value
  const date = new Date(
    Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  )
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}

function describePlanAction(action: Record<string, any>): string {
  if (action.description) return String(action.description)
  if (action.reason) return String(action.reason)
  if (action.outcome) return `Outcome: ${humanize(action.outcome)}`

  const relativeDays = action.days_relative ?? action.days_offset
  if (typeof relativeDays === 'number') {
    if (relativeDays === 0) return 'On the invoice due date'
    return `${Math.abs(relativeDays)} day${Math.abs(relativeDays) === 1 ? '' : 's'} ${
      relativeDays < 0 ? 'before' : 'after'
    } the due date`
  }
  return '—'
}

function toPlanRow(
  entry: unknown,
  fallbackStatus: string,
  fallbackAction?: string
): PlanActionRow {
  const action =
    entry && typeof entry === 'object'
      ? (entry as Record<string, any>)
      : { action: entry }
  return {
    action: humanize(
      action.type || action.action || action.name || fallbackAction
    ),
    date: action.date || action.scheduled_date || action.due_date,
    details: describePlanAction(action),
    status: String(action.status || action.state || fallbackStatus).toLowerCase(),
  }
}

function getPlanRows(plan: Record<string, any>): PlanActionRow[] {
  const rows: PlanActionRow[] = []
  const addRows = (entries: unknown, status: string) => {
    if (!Array.isArray(entries)) return
    entries.forEach((entry) => rows.push(toPlanRow(entry, status)))
  }

  addRows(plan.scheduled_actions, 'scheduled')
  addRows(plan.completed_actions, 'completed')

  if (Array.isArray(plan.contingencies)) {
    addRows(plan.contingencies, 'contingency')
  } else if (plan.contingencies && typeof plan.contingencies === 'object') {
    Object.entries(plan.contingencies).forEach(([name, value]) => {
      if (value && typeof value === 'object') {
        rows.push(toPlanRow(value, 'contingency', name))
      } else {
        rows.push({
          action: humanize(name),
          details: String(value),
          status: 'contingency',
        })
      }
    })
  }

  addRows(plan.cancelled_actions, 'cancelled')

  if (rows.length === 0) {
    addRows(plan.actions || plan.steps, 'planned')
  }
  return rows
}

function getPlanFlags(plan: Record<string, any>): string[] {
  if (Array.isArray(plan.flags)) return plan.flags.map(humanize)
  if (!plan.flags || typeof plan.flags !== 'object') return []
  return Object.entries(plan.flags)
    .filter(([, value]) => Boolean(value))
    .map(([name, value]) =>
      value === true ? humanize(name) : `${humanize(name)}: ${humanize(value)}`
    )
}

function PlanStatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  const styles =
    normalized === 'completed' || normalized === 'done'
      ? 'bg-green-50 text-green-700 border-green-200'
      : normalized === 'scheduled' || normalized === 'in_progress'
      ? 'bg-blue-50 text-blue-700 border-blue-200'
      : normalized === 'cancelled' || normalized === 'skipped'
      ? 'bg-red-50 text-red-700 border-red-200'
      : normalized === 'contingency'
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-gray-50 text-gray-600 border-gray-200'

  const icon =
    normalized === 'completed' || normalized === 'done' ? (
      <CheckCircle className="w-3.5 h-3.5" />
    ) : normalized === 'cancelled' || normalized === 'skipped' ? (
      <XCircle className="w-3.5 h-3.5" />
    ) : normalized === 'contingency' ? (
      <AlertTriangle className="w-3.5 h-3.5" />
    ) : (
      <Clock className="w-3.5 h-3.5" />
    )

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full border text-[11px] font-medium ${styles}`}
    >
      {icon}
      {humanize(normalized)}
    </span>
  )
}

function WorkflowPlanTable({ plan: rawPlan }: { plan: unknown }) {
  const plan = parseWorkflowPlan(rawPlan)
  if (!plan) {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
        This workflow's plan could not be displayed because its stored format is invalid.
      </div>
    )
  }

  const rows = getPlanRows(plan)
  const flags = getPlanFlags(plan)
  const scheduledCount = rows.filter((row) => row.status === 'scheduled').length
  const completedCount = rows.filter((row) => row.status === 'completed').length

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Projected Plan
        </h4>
        <div className="flex items-center gap-2 text-[11px]">
          {scheduledCount > 0 && (
            <span className="text-blue-700">{scheduledCount} scheduled</span>
          )}
          {completedCount > 0 && (
            <span className="text-green-700">{completedCount} completed</span>
          )}
        </div>
      </div>

      {rows.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-[11px] uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-3 py-2.5 font-semibold">Status</th>
                <th className="px-3 py-2.5 font-semibold">Action</th>
                <th className="px-3 py-2.5 font-semibold whitespace-nowrap">Date</th>
                <th className="px-3 py-2.5 font-semibold">Context</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {rows.map((row, index) => (
                <tr key={`${row.status}-${row.action}-${row.date || index}`}>
                  <td className="px-3 py-3 align-top">
                    <PlanStatusBadge status={row.status} />
                  </td>
                  <td className="px-3 py-3 align-top font-medium text-gray-800">
                    {row.action}
                  </td>
                  <td className="px-3 py-3 align-top whitespace-nowrap text-gray-600">
                    {formatPlanDate(row.date)}
                  </td>
                  <td className="px-3 py-3 align-top text-gray-500">
                    {row.details}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-md bg-gray-50 px-3 py-3 text-xs text-gray-500">
          No actions have been added to this workflow yet.
        </div>
      )}

      {(flags.length > 0 || plan.tone || plan.risk_level) && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
            Signals
          </span>
          {plan.risk_level && (
            <span className="rounded-full bg-red-50 px-2 py-1 text-[11px] font-medium text-red-700">
              Risk: {humanize(plan.risk_level)}
            </span>
          )}
          {plan.tone && (
            <span className="rounded-full bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-700">
              Tone: {humanize(plan.tone)}
            </span>
          )}
          {flags.map((flag) => (
            <span
              key={flag}
              className="rounded-full bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700"
            >
              {flag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ManagerDashboard() {
  const [systemState, setSystemState] = useState<SystemState | null>(null)
  const [agingSummary, setAgingSummary] = useState<AgingSummary | null>(null)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null)
  const [agentResult, setAgentResult] = useState<AgentResult | null>(null)
  const [reasoningExpanded, setReasoningExpanded] = useState(true)
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [advancingBy, setAdvancingBy] = useState<1 | 3 | null>(null)

  const fetchData = async () => {
    try {
      const [stateRes, agingRes, customersRes, workflowsRes] =
        await Promise.all([
          api.get('/simulation/state'),
          api.get('/simulation/aging-summary'),
          api.get('/customers'),
          api.get('/workflows/active'),
        ])
      setSystemState(stateRes.data)
      setAgingSummary(agingRes.data)
      setCustomers(customersRes.data.customers)
      setWorkflows(workflowsRes.data.workflows)
    } catch (err) {
      console.error('Failed to fetch dashboard data', err)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleAdvanceDays = async (days: 1 | 3) => {
    setAdvancingBy(days)
    setAgentResult(null)
    try {
      const endpoint =
        days === 3
          ? '/simulation/advance-three-days'
          : '/simulation/advance-day'
      const res = await api.post(endpoint)
      setAgentResult(res.data.agent_result)
      await fetchData()
    } catch (err) {
      console.error(`Advance ${days} day(s) failed`, err)
    } finally {
      setAdvancingBy(null)
    }
  }

  const handleReset = async () => {
    try {
      await api.post('/simulation/reset')
      setAgentResult(null)
      setSelectedWorkflow(null)
      setSelectedCustomer(null)
      await fetchData()
    } catch (err) {
      console.error('Reset failed', err)
    }
  }

  // Build customer hierarchy
  const parentCustomers = customers.filter((c) => !c.parent_customer_id)
  const childCustomers = (parentId: string) =>
    customers.filter((c) => c.parent_customer_id === parentId)

  // Filter workflows by selected customer
  const filteredWorkflows = selectedCustomer
    ? workflows.filter((w) => w.customer_id === selectedCustomer)
    : workflows

  const segmentColor = (segment: string) => {
    switch (segment) {
      case 'strategic':
        return 'bg-blue-100 text-blue-800'
      case 'mid_tier':
        return 'bg-amber-100 text-amber-800'
      case 'small':
        return 'bg-gray-100 text-gray-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const statusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'escalated':
        return 'bg-red-100 text-red-800'
      case 'completed':
        return 'bg-blue-100 text-blue-800'
      case 'paused':
        return 'bg-gray-100 text-gray-600'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const renderActionTimeline = (workflow: Workflow) => {
    if (!workflow.plan) return null
    const plan = parseWorkflowPlan(workflow.plan)
    if (!plan) return null
    const actions = plan.actions || plan.steps || plan.scheduled_actions || []
    if (!Array.isArray(actions) || actions.length === 0) return null

    return (
      <div className="flex items-center gap-1 mt-2 flex-wrap">
        {actions.map((action: any, idx: number) => {
          const status = action.status || action.state || 'planned'
          let icon
          let lineClass = 'bg-gray-200'
          if (status === 'completed' || status === 'done') {
            icon = <CheckCircle className="w-4 h-4 text-green-600" />
            lineClass = 'bg-green-400'
          } else if (status === 'scheduled' || status === 'in_progress') {
            icon = <Clock className="w-4 h-4 text-blue-600" />
            lineClass = 'bg-blue-400'
          } else if (status === 'cancelled' || status === 'skipped') {
            icon = <XCircle className="w-4 h-4 text-red-400" />
            lineClass = 'bg-red-200'
          } else {
            icon = (
              <div className="w-3 h-3 rounded-full bg-gray-300 border border-gray-400" />
            )
          }

          return (
            <div key={idx} className="flex items-center gap-1">
              <div className="flex flex-col items-center">
                {icon}
                <span
                  className={`text-[10px] mt-0.5 max-w-[60px] truncate ${
                    status === 'cancelled' ? 'line-through text-red-400' : 'text-gray-500'
                  }`}
                >
                  {humanize(action.type || action.action || `Step ${idx + 1}`)}
                </span>
              </div>
              {idx < actions.length - 1 && (
                <div className={`w-6 h-0.5 ${lineClass} self-start mt-2`} />
              )}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold text-gray-900">
              AI Collections Workflow Agent
            </h1>
            {systemState && (
              <div className="flex items-center gap-1.5 text-sm text-gray-500">
                <Calendar className="w-4 h-4" />
                <span>{systemState.current_date}</span>
                <span className="text-gray-300 mx-1">|</span>
                <span>Cycle #{systemState.cycle_count}</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <nav className="flex items-center gap-2 mr-4 text-sm">
              <Link
                to="/customer/CUST-001"
                className="text-blue-600 hover:text-blue-800 hover:underline"
              >
                Customer Portal
              </Link>
              <span className="text-gray-300">|</span>
              <Link
                to="/collector"
                className="text-blue-600 hover:text-blue-800 hover:underline"
              >
                Collector View
              </Link>
              <span className="text-gray-300">|</span>
              <Link
                to="/disputes"
                className="text-blue-600 hover:text-blue-800 hover:underline"
              >
                Dispute Team
              </Link>
            </nav>
            <button
              onClick={() => handleAdvanceDays(1)}
              disabled={advancingBy !== null}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {advancingBy === 1 ? (
                <>
                  <svg
                    className="animate-spin w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Agent Thinking...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Advance Day
                </>
              )}
            </button>
            <button
              onClick={() => handleAdvanceDays(3)}
              disabled={advancingBy !== null}
              className="inline-flex items-center gap-2 px-4 py-2 border border-blue-300 bg-blue-50 text-blue-700 text-sm font-medium rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {advancingBy === 3 ? (
                <>
                  <svg
                    className="animate-spin w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Jumping 3 Days...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  +3 Days
                </>
              )}
            </button>
            <button
              onClick={handleReset}
              className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
          </div>
        </div>
      </header>

      {/* Aging Summary */}
      {agingSummary && (
        <div className="px-6 py-4 bg-white border-b border-gray-100">
          <div className="flex items-center gap-4">
            {Object.entries(agingSummary.aging).map(([bucket, amount]) => (
              <div
                key={bucket}
                className="flex-1 bg-gray-50 rounded-lg p-3 border border-gray-100"
              >
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  {bucket}
                </div>
                <div className="text-lg font-semibold text-gray-900 mt-1">
                  ${Number(amount).toLocaleString()}
                </div>
              </div>
            ))}
            <div className="flex-1 bg-blue-50 rounded-lg p-3 border border-blue-100">
              <div className="text-xs font-medium text-blue-600 uppercase tracking-wide">
                Total Outstanding
              </div>
              <div className="text-lg font-semibold text-blue-900 mt-1">
                ${Number(agingSummary.total).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex flex-1">
        {/* Customer Sidebar */}
        <aside className="w-72 bg-white border-r border-gray-200 overflow-y-auto h-[calc(100vh-180px)]">
          <div className="p-4">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              Customers
            </h2>
            {selectedCustomer && (
              <button
                onClick={() => setSelectedCustomer(null)}
                className="text-xs text-blue-600 hover:underline mb-2"
              >
                Clear filter
              </button>
            )}
            <div className="space-y-1">
              {parentCustomers.map((parent) => (
                <div key={parent.customer_id}>
                  <button
                    onClick={() => setSelectedCustomer(parent.customer_id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm flex items-center justify-between transition-colors ${
                      selectedCustomer === parent.customer_id
                        ? 'bg-blue-50 text-blue-800'
                        : 'hover:bg-gray-50 text-gray-800'
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                      <span className="truncate">{parent.name}</span>
                    </div>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0 ${segmentColor(
                        parent.segment
                      )}`}
                    >
                      {parent.segment}
                    </span>
                  </button>
                  {childCustomers(parent.customer_id).map((child) => (
                    <button
                      key={child.customer_id}
                      onClick={() => setSelectedCustomer(child.customer_id)}
                      className={`w-full text-left pl-9 pr-3 py-1.5 rounded-md text-sm flex items-center justify-between transition-colors ${
                        selectedCustomer === child.customer_id
                          ? 'bg-blue-50 text-blue-800'
                          : 'hover:bg-gray-50 text-gray-600'
                      }`}
                    >
                      <span className="truncate">{child.name}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0 ${segmentColor(
                          child.segment
                        )}`}
                      >
                        {child.segment}
                      </span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Workflows Main Area */}
        <main className="flex-1 overflow-y-auto h-[calc(100vh-180px)]">
          <div className="p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Active Workflows
              {selectedCustomer && (
                <span className="ml-2 text-blue-600 normal-case font-normal">
                  (filtered)
                </span>
              )}
            </h2>

            {filteredWorkflows.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                <p className="text-sm">
                  No active workflows. Drop an invoice PDF into{' '}
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono">
                    data/incoming_invoices/
                  </code>{' '}
                  to begin.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredWorkflows.map((wf) => {
                  const customer = customers.find(
                    (c) => c.customer_id === wf.customer_id
                  )
                  return (
                    <div
                      key={wf.workflow_id}
                      onClick={() =>
                        setSelectedWorkflow(
                          selectedWorkflow?.workflow_id === wf.workflow_id
                            ? null
                            : wf
                        )
                      }
                      className={`bg-white border rounded-lg p-4 cursor-pointer transition-all hover:shadow-sm ${
                        selectedWorkflow?.workflow_id === wf.workflow_id
                          ? 'border-blue-300 ring-1 ring-blue-100'
                          : 'border-gray-200'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900 text-sm">
                              {wf.invoice_id}
                            </span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusColor(
                                wf.status
                              )}`}
                            >
                              {wf.status}
                            </span>
                          </div>
                          <div className="text-sm text-gray-500 mt-1">
                            {customer?.name || wf.customer_id}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-3">
                            <div>
                              <div className="text-xs text-gray-400">
                                Confidence
                              </div>
                              <div className="text-sm font-semibold text-gray-800">
                                {Math.round(
                                  wf.confidence <= 1
                                    ? wf.confidence * 100
                                    : wf.confidence
                                )}%
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-400">
                                Reason Code
                              </div>
                              <div className="text-sm font-medium">
                                <span className="inline-flex max-w-72 rounded-full bg-blue-50 px-2 py-1 text-[10px] font-semibold text-blue-700">
                                  {wf.reason_code
                                    ? humanize(wf.reason_code)
                                    : 'Not Available'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Timeline */}
                      {renderActionTimeline(wf)}

                      {/* Expanded Plan View */}
                      {selectedWorkflow?.workflow_id === wf.workflow_id &&
                        wf.plan && (
                          <div className="mt-4 pt-4 border-t border-gray-100">
                            <WorkflowPlanTable plan={wf.plan} />
                            {wf.reasoning && (
                              <div className="mt-4 rounded-lg border border-gray-100 bg-gray-50/70 p-3">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                                  Reasoning
                                </h4>
                                <p className="text-xs text-gray-600 leading-relaxed">
                                  {wf.reasoning}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Agent Reasoning Panel */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg">
        <button
          onClick={() => setReasoningExpanded(!reasoningExpanded)}
          className="w-full px-6 py-2 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <span className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Agent Reasoning
            {agentResult && (
              <span className="text-xs text-green-600 font-normal">
                Last run: {agentResult.date} - {agentResult.status}
              </span>
            )}
          </span>
          <ChevronRight
            className={`w-4 h-4 transition-transform ${
              reasoningExpanded ? 'rotate-90' : ''
            }`}
          />
        </button>

        {reasoningExpanded && (
          <div className="px-6 pb-4 max-h-64 overflow-y-auto">
            {agentResult ? (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Summary */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center gap-3 mb-2">
                    <div>
                      <div className="text-xs text-gray-400">Confidence</div>
                      <div className="text-lg font-bold text-gray-900">
                        {agentResult.iterations} iterations
                      </div>
                    </div>
                    <div className="ml-auto text-right">
                      <div className="text-xs text-gray-400">Tool Calls</div>
                      <div className="text-lg font-bold text-blue-700">
                        {agentResult.tool_calls}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    Cycle #{agentResult.cycle_number} | Status:{' '}
                    <span className="font-medium text-gray-700">
                      {agentResult.status}
                    </span>
                  </div>
                </div>

                {/* Reasoning */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">
                    Agent Reasoning
                  </h4>
                  <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {agentResult.agent_reasoning || 'No reasoning captured.'}
                  </p>
                </div>

                {/* Tool Calls Log */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">
                    Tool Calls Log
                  </h4>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {agentResult.tool_calls_log &&
                    agentResult.tool_calls_log.length > 0 ? (
                      agentResult.tool_calls_log.map((tc, idx) => (
                        <div
                          key={idx}
                          className="text-[11px] font-mono bg-white px-2 py-1 rounded border border-gray-100"
                        >
                          <span className="font-semibold text-blue-700">
                            {tc.tool}
                          </span>
                          <span className="text-gray-400 ml-1">
                            {tc.result_preview}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-gray-400">
                        No tool calls recorded.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-gray-400 text-sm">
                {advancingBy !== null ? (
                  <div className="flex items-center justify-center gap-2">
                    <svg
                      className="animate-spin w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                    Agent is processing after advancing {advancingBy} day
                    {advancingBy === 1 ? '' : 's'}... This may take a moment.
                  </div>
                ) : (
                  'Advance the simulation to run the agent and see reasoning here.'
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
