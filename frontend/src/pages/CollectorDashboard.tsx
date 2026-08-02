import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Phone, PhoneOff, PhoneMissed, CheckCircle, ArrowLeft, FileText, Clock } from 'lucide-react'
import api from '../api/client'
import { CallTask } from '../types/index'

interface CompletedCall {
  activity_id: string
  customer_id: string
  customer_name: string
  invoice_id: string
  outcome: string
  call_status: string
  date: string
  notes: string
}

interface TaskWithMeta extends CallTask {
  amount?: number
  priority?: 'URGENT' | 'HIGH' | 'MEDIUM' | 'LOW'
  reason?: string
}

type CallStatus = 'Connected' | 'No Answer' | 'Voicemail'
type Outcome =
  | 'Promise to Pay'
  | 'Dispute Raised'
  | 'Payment Confirmed'
  | 'Requested Callback'
  | 'Refused to Pay'
  | 'Documents Needed'
  | 'Other'

const OUTCOMES: Outcome[] = [
  'Promise to Pay',
  'Dispute Raised',
  'Payment Confirmed',
  'Requested Callback',
  'Refused to Pay',
  'Documents Needed',
  'Other',
]

function getPriorityBadge(priority: string | undefined) {
  switch (priority) {
    case 'URGENT':
      return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-red-100 text-red-800">URGENT</span>
    case 'HIGH':
      return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-orange-100 text-orange-800">HIGH</span>
    case 'MEDIUM':
      return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">MEDIUM</span>
    case 'LOW':
      return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-green-100 text-green-800">LOW</span>
    default:
      return <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">--</span>
  }
}

function getCallStatusIcon(status: CallStatus) {
  switch (status) {
    case 'Connected':
      return <Phone className="w-4 h-4 text-green-600" />
    case 'No Answer':
      return <PhoneMissed className="w-4 h-4 text-red-500" />
    case 'Voicemail':
      return <PhoneOff className="w-4 h-4 text-amber-500" />
  }
}

export default function CollectorDashboard() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const focusedActivityId = searchParams.get('taskId')
  const focusedInvoiceId = searchParams.get('invoiceId')
  const [tasks, setTasks] = useState<TaskWithMeta[]>([])
  const [completedCalls, setCompletedCalls] = useState<CompletedCall[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedScript, setExpandedScript] = useState<string | null>(null)
  const [expandedOutcome, setExpandedOutcome] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Outcome form state
  const [callStatus, setCallStatus] = useState<CallStatus>('Connected')
  const [outcome, setOutcome] = useState<Outcome>('Promise to Pay')
  const [ptpAmount, setPtpAmount] = useState('')
  const [ptpDate, setPtpDate] = useState('')
  const [notes, setNotes] = useState('')

  const fetchTasks = useCallback(async () => {
    try {
      const [tasksRes, completedRes] = await Promise.all([
        api.get('/collector/tasks'),
        api.get('/collector/completed'),
      ])
      setTasks(tasksRes.data.tasks)
      setCompletedCalls(completedRes.data.completed)
    } catch (err) {
      console.error('Failed to fetch collector data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  useEffect(() => {
    if (loading) return
    const matchingTask =
      tasks.find((task) => task.activity_id === focusedActivityId) ||
      tasks.find((task) => task.invoice_id === focusedInvoiceId)
    const elementId = matchingTask
      ? `collector-item-${matchingTask.activity_id}`
      : focusedActivityId
      ? `collector-item-${focusedActivityId}`
      : null
    if (matchingTask) setExpandedScript(matchingTask.activity_id)
    if (!elementId) return
    window.setTimeout(() => {
      document.getElementById(elementId)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }, 50)
  }, [focusedActivityId, focusedInvoiceId, loading, tasks])

  const resetForm = () => {
    setCallStatus('Connected')
    setOutcome('Promise to Pay')
    setPtpAmount('')
    setPtpDate('')
    setNotes('')
  }

  const handleSubmitOutcome = async (task: TaskWithMeta) => {
    setSubmitting(true)
    try {
      const payload: any = {
        customer_id: task.customer_id,
        invoice_id: task.invoice_id,
        call_status: callStatus,
        outcome,
        notes,
      }
      if (outcome === 'Promise to Pay') {
        payload.ptp_amount = parseFloat(ptpAmount) || 0
        payload.ptp_date = ptpDate
      }
      await api.post('/collector/outcome', payload)
      setSuccessMessage(`Outcome logged for ${task.customer_name}`)
      setExpandedOutcome(null)
      resetForm()
      await fetchTasks()
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      console.error('Failed to submit outcome:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const toggleScript = (activityId: string) => {
    setExpandedScript(expandedScript === activityId ? null : activityId)
  }

  const toggleOutcome = (activityId: string) => {
    if (expandedOutcome === activityId) {
      setExpandedOutcome(null)
    } else {
      setExpandedOutcome(activityId)
      resetForm()
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500 flex items-center gap-2">
          <Clock className="w-5 h-5 animate-spin" />
          Loading tasks...
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/collector')}
              className="flex items-center gap-1 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Notifications</span>
            </button>
            <div className="h-6 w-px bg-gray-300" />
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Phone className="w-5 h-5 text-blue-600" />
              Collector Dashboard
            </h1>
          </div>
          <div className="text-sm text-gray-600">
            Welcome, <span className="font-medium text-gray-900">John Smith</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-8">
        {/* Success Message */}
        {successMessage && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2 text-green-800">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm font-medium">{successMessage}</span>
          </div>
        )}

        {/* Today's Call Tasks */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Phone className="w-5 h-5 text-blue-600" />
            Today's Call Tasks
            <span className="text-sm font-normal text-gray-500">({tasks.length} pending)</span>
          </h2>

          {tasks.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-500">
              <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
              <p>All calls completed for today. Great work!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {tasks.map((task) => (
                <div
                  id={`collector-item-${task.activity_id}`}
                  key={task.activity_id}
                  className={`bg-white rounded-lg border shadow-sm transition-colors ${
                    task.activity_id === focusedActivityId ||
                    (!focusedActivityId && task.invoice_id === focusedInvoiceId)
                      ? 'border-blue-400 ring-2 ring-blue-100'
                      : 'border-gray-200'
                  }`}
                >
                  {/* Task Header */}
                  <div className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="font-semibold text-gray-900">{task.customer_name}</h3>
                          {getPriorityBadge(task.priority)}
                        </div>
                        <div className="text-sm text-gray-600 space-y-0.5">
                          <p>
                            <span className="font-medium">Invoice:</span> {task.invoice_id}
                            {task.amount != null && (
                              <span className="ml-3 font-medium text-gray-900">
                                ${task.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </span>
                            )}
                          </p>
                          {task.reason && (
                            <p>
                              <span className="font-medium">Reason:</span> {task.reason}
                            </p>
                          )}
                          {task.details && !task.reason && (
                            <p>
                              <span className="font-medium">Details:</span> {task.details}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleScript(task.activity_id)}
                          className={`px-3 py-1.5 text-sm rounded-md border transition-colors flex items-center gap-1.5 ${
                            expandedScript === task.activity_id
                              ? 'bg-blue-50 border-blue-300 text-blue-700'
                              : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          <FileText className="w-3.5 h-3.5" />
                          View Script
                        </button>
                        <button
                          onClick={() => toggleOutcome(task.activity_id)}
                          className={`px-3 py-1.5 text-sm rounded-md border transition-colors flex items-center gap-1.5 ${
                            expandedOutcome === task.activity_id
                              ? 'bg-green-50 border-green-300 text-green-700'
                              : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          <CheckCircle className="w-3.5 h-3.5" />
                          Log Outcome
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Script */}
                  {expandedScript === task.activity_id && task.script && (
                    <div className="border-t border-gray-200 p-4 bg-blue-50/30">
                      <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                        <FileText className="w-4 h-4 text-blue-600" />
                        Call Script
                      </h4>
                      <div className="bg-white rounded-md border border-blue-200 p-4 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed font-mono">
                        {task.script}
                      </div>
                    </div>
                  )}

                  {/* Expanded Outcome Form */}
                  {expandedOutcome === task.activity_id && (
                    <div className="border-t border-gray-200 p-4 bg-green-50/30">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        Log Call Outcome
                      </h4>
                      <div className="space-y-4">
                        {/* Call Status */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Call Status</label>
                          <div className="flex items-center gap-4">
                            {(['Connected', 'No Answer', 'Voicemail'] as CallStatus[]).map((status) => (
                              <label
                                key={status}
                                className="flex items-center gap-2 cursor-pointer"
                              >
                                <input
                                  type="radio"
                                  name={`status-${task.activity_id}`}
                                  value={status}
                                  checked={callStatus === status}
                                  onChange={() => setCallStatus(status)}
                                  className="text-blue-600 focus:ring-blue-500"
                                />
                                <span className="flex items-center gap-1 text-sm text-gray-700">
                                  {getCallStatusIcon(status)}
                                  {status}
                                </span>
                              </label>
                            ))}
                          </div>
                        </div>

                        {/* Outcome Dropdown */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Outcome</label>
                          <select
                            value={outcome}
                            onChange={(e) => setOutcome(e.target.value as Outcome)}
                            className="w-full max-w-xs border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
                          >
                            {OUTCOMES.map((o) => (
                              <option key={o} value={o}>
                                {o}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Promise to Pay Fields */}
                        {outcome === 'Promise to Pay' && (
                          <div className="flex items-center gap-4">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Promise Amount ($)
                              </label>
                              <input
                                type="number"
                                value={ptpAmount}
                                onChange={(e) => setPtpAmount(e.target.value)}
                                placeholder="0.00"
                                className="border border-gray-300 rounded-md px-3 py-2 text-sm w-40 focus:ring-blue-500 focus:border-blue-500"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Promise Date
                              </label>
                              <input
                                type="date"
                                value={ptpDate}
                                onChange={(e) => setPtpDate(e.target.value)}
                                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
                              />
                            </div>
                          </div>
                        )}

                        {/* Notes */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                          <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Add any relevant notes about the call..."
                            rows={3}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500 resize-none"
                          />
                        </div>

                        {/* Submit Button */}
                        <div>
                          <button
                            onClick={() => handleSubmitOutcome(task)}
                            disabled={submitting}
                            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          >
                            {submitting ? 'Submitting...' : 'Submit Outcome'}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Completed Calls */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            Completed Calls
            <span className="text-sm font-normal text-gray-500">({completedCalls.length})</span>
          </h2>

          {completedCalls.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6 text-center text-gray-500">
              <p className="text-sm">No completed calls yet today.</p>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Customer</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Invoice</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Outcome</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {completedCalls.map((call) => (
                    <tr
                      id={`collector-item-${call.activity_id}`}
                      key={call.activity_id}
                      className={`hover:bg-gray-50 ${
                        call.activity_id === focusedActivityId ||
                        (!focusedActivityId && call.invoice_id === focusedInvoiceId)
                          ? 'bg-blue-50 ring-1 ring-inset ring-blue-200'
                          : ''
                      }`}
                    >
                      <td className="px-4 py-3 text-gray-600">{call.date}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{call.customer_name}</td>
                      <td className="px-4 py-3 text-gray-600">{call.invoice_id}</td>
                      <td className="px-4 py-3 text-gray-600">{call.call_status}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800">
                          {call.outcome}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{call.notes || '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
