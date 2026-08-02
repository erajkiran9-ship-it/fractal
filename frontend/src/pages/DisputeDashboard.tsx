import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  ClipboardCheck,
  Clock,
  FileQuestion,
  MessageSquare,
  RefreshCw,
  Scale,
  UserCheck,
} from 'lucide-react'

import api from '../api/client'
import { DisputeCase } from '../types/index'

type QueueFilter = 'active' | 'resolved' | 'all'
type ResolutionDecision =
  | 'accepted'
  | 'partially_accepted'
  | 'rejected'
  | 'more_information_required'

const ACTIVE_STATUSES = new Set(['OPEN', 'UNDER_REVIEW', 'NEEDS_INFORMATION'])

function money(value: number | undefined) {
  return Number(value || 0).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  })
}

function humanize(value: string | undefined) {
  if (!value) return 'Not available'
  return value
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function statusClasses(status: string) {
  switch (status) {
    case 'OPEN':
      return 'bg-red-50 text-red-700 border-red-200'
    case 'UNDER_REVIEW':
      return 'bg-blue-50 text-blue-700 border-blue-200'
    case 'NEEDS_INFORMATION':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'RESOLVED':
      return 'bg-green-50 text-green-700 border-green-200'
    default:
      return 'bg-gray-50 text-gray-600 border-gray-200'
  }
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-1 text-[11px] font-semibold ${statusClasses(
        status
      )}`}
    >
      {humanize(status)}
    </span>
  )
}

export default function DisputeDashboard() {
  const { disputeId } = useParams<{ disputeId: string }>()
  const navigate = useNavigate()
  const [disputes, setDisputes] = useState<DisputeCase[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<QueueFilter>('active')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [owner, setOwner] = useState('Dispute Team')
  const [investigationNote, setInvestigationNote] = useState('')
  const [investigator, setInvestigator] = useState('Dispute Team')
  const [decision, setDecision] = useState<ResolutionDecision>('accepted')
  const [approvedAmount, setApprovedAmount] = useState('')
  const [teamResponse, setTeamResponse] = useState('')
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [resolvedBy, setResolvedBy] = useState('Dispute Team')

  const fetchQueue = useCallback(async (preferredId?: string | null) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/disputes/queue?include_resolved=true')
      const items: DisputeCase[] = response.data.disputes
      setDisputes(items)
      setSelectedId((current) => {
        const target = preferredId || current
        if (target && items.some((item) => item.dispute_id === target)) {
          return target
        }
        return (
          items.find((item) => ACTIVE_STATUSES.has(item.status))?.dispute_id ||
          items[0]?.dispute_id ||
          null
        )
      })
    } catch (requestError: any) {
      setError(
        requestError.response?.data?.detail || 'Unable to load the dispute queue.'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchQueue(disputeId)
  }, [disputeId, fetchQueue])

  const selected = disputes.find((item) => item.dispute_id === selectedId) || null

  useEffect(() => {
    if (!disputeId) return
    const target = disputes.find((item) => item.dispute_id === disputeId)
    if (target?.status === 'RESOLVED') setFilter('resolved')
    else if (target) setFilter('active')
  }, [disputeId, disputes])

  useEffect(() => {
    if (!selected) return
    setOwner(selected.owner || 'Dispute Team')
    setApprovedAmount(
      selected.amount ? String(Number(selected.amount).toFixed(2)) : ''
    )
    setTeamResponse('')
    setResolutionNotes('')
    setInvestigationNote('')
    setDecision('accepted')
  }, [selectedId])

  const counts = useMemo(
    () => ({
      open: disputes.filter((item) => item.status === 'OPEN').length,
      review: disputes.filter((item) => item.status === 'UNDER_REVIEW').length,
      info: disputes.filter((item) => item.status === 'NEEDS_INFORMATION').length,
      resolved: disputes.filter((item) => item.status === 'RESOLVED').length,
    }),
    [disputes]
  )

  const filtered = disputes.filter((item) => {
    if (filter === 'active') return ACTIVE_STATUSES.has(item.status)
    if (filter === 'resolved') return item.status === 'RESOLVED'
    return true
  })

  const runAction = async (action: () => Promise<unknown>, message: string) => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await action()
      setSuccess(message)
      await fetchQueue(selectedId)
    } catch (requestError: any) {
      setError(
        requestError.response?.data?.detail || 'The dispute action could not be saved.'
      )
    } finally {
      setSaving(false)
    }
  }

  const assign = () => {
    if (!selected || !owner.trim()) return
    runAction(
      () => api.post(`/disputes/${selected.dispute_id}/assign`, { owner }),
      `${selected.dispute_id} is now under review.`
    )
  }

  const addNote = () => {
    if (!selected || !investigationNote.trim()) return
    runAction(
      () =>
        api.post(`/disputes/${selected.dispute_id}/investigation`, {
          notes: investigationNote,
          investigator,
        }),
      'Investigation note added.'
    )
  }

  const resolve = () => {
    if (!selected || !teamResponse.trim()) return
    runAction(
      () =>
        api.post(`/disputes/${selected.dispute_id}/resolve`, {
          decision,
          approved_amount:
            decision === 'partially_accepted'
              ? Number(approvedAmount)
              : decision === 'accepted'
              ? selected.amount
              : 0,
          response: teamResponse,
          notes: resolutionNotes,
          resolved_by: resolvedBy,
        }),
      decision === 'more_information_required'
        ? 'Information request sent; collections remain paused.'
        : 'Decision recorded and the collection workflow was updated.'
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <Link
              to="/disputes"
              className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
            >
              <ArrowLeft className="h-4 w-4" /> Notifications
            </Link>
            <div className="h-6 w-px bg-gray-200" />
            <div>
              <h1 className="flex items-center gap-2 text-xl font-semibold">
                <Scale className="h-5 w-5 text-blue-600" /> Dispute Resolution Desk
              </h1>
              <p className="mt-0.5 text-xs text-gray-500">
                Investigate customer claims and return invoices to the correct collection path.
              </p>
            </div>
          </div>
          <button
            onClick={() => fetchQueue(selectedId)}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] space-y-5 px-6 py-5">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            ['Open', counts.open, AlertCircle, 'text-red-600', 'bg-red-50'],
            ['Under Review', counts.review, Clock, 'text-blue-600', 'bg-blue-50'],
            ['Needs Information', counts.info, FileQuestion, 'text-amber-600', 'bg-amber-50'],
            ['Resolved', counts.resolved, CheckCircle, 'text-green-600', 'bg-green-50'],
          ].map(([label, count, Icon, color, background]) => {
            const CardIcon = Icon as typeof AlertCircle
            return (
              <div key={String(label)} className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                      {String(label)}
                    </p>
                    <p className="mt-1 text-2xl font-semibold">{String(count)}</p>
                  </div>
                  <div className={`rounded-lg p-2.5 ${String(background)}`}>
                    <CardIcon className={`h-5 w-5 ${String(color)}`} />
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {success && (
          <div className="rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            {success}
          </div>
        )}

        <div className="grid min-h-[650px] grid-cols-1 overflow-hidden rounded-xl border border-gray-200 bg-white lg:grid-cols-[370px_1fr]">
          <aside className="border-b border-gray-200 lg:border-b-0 lg:border-r">
            <div className="border-b border-gray-100 p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">Dispute Queue</h2>
                <span className="text-xs text-gray-400">{filtered.length} cases</span>
              </div>
              <div className="mt-3 flex rounded-md bg-gray-100 p-1 text-xs">
                {(['active', 'resolved', 'all'] as QueueFilter[]).map((value) => (
                  <button
                    key={value}
                    onClick={() => setFilter(value)}
                    className={`flex-1 rounded px-2 py-1.5 font-medium ${
                      filter === value
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-800'
                    }`}
                  >
                    {humanize(value)}
                  </button>
                ))}
              </div>
            </div>

            <div className="max-h-[720px] overflow-y-auto">
              {loading ? (
                <div className="p-8 text-center text-sm text-gray-400">Loading disputes…</div>
              ) : filtered.length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-400">No disputes in this queue.</div>
              ) : (
                filtered.map((item) => (
                  <button
                    key={item.dispute_id}
                    onClick={() => {
                      setSelectedId(item.dispute_id)
                      navigate(`/disputes/case/${item.dispute_id}`)
                    }}
                    className={`w-full border-b border-gray-100 p-4 text-left transition-colors ${
                      selectedId === item.dispute_id
                        ? 'bg-blue-50/70'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold">{item.dispute_id}</p>
                        <p className="mt-0.5 text-xs text-gray-500">{item.customer_name}</p>
                      </div>
                      <StatusBadge status={item.status} />
                    </div>
                    <div className="mt-3 flex items-end justify-between">
                      <div>
                        <p className="text-xs text-gray-400">{item.invoice_id}</p>
                        <p className="mt-0.5 text-xs text-gray-500">{humanize(item.type)}</p>
                      </div>
                      <p className="text-sm font-semibold text-gray-800">{money(item.amount)}</p>
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>

          <section className="p-5 lg:p-6">
            {!selected ? (
              <div className="flex h-full flex-col items-center justify-center text-center text-gray-400">
                <ClipboardCheck className="mb-3 h-10 w-10 text-gray-300" />
                <p className="font-medium">Select a dispute to begin review</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-semibold">{selected.dispute_id}</h2>
                      <StatusBadge status={selected.status} />
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                      {selected.customer_name} · {selected.invoice_id} · Raised {selected.created_date}
                    </p>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <p>Routing owner</p>
                    <p className="mt-1 font-semibold text-gray-800">
                      {humanize(selected.owner || 'Unassigned')}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    ['Invoice Total', money(selected.invoice_amount)],
                    ['Disputed Amount', money(selected.amount)],
                    ['Outstanding Balance', money(selected.outstanding_amount)],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-400">{label}</p>
                      <p className="mt-1 text-lg font-semibold">{value}</p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <div className="rounded-lg border border-gray-200 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Customer Claim
                    </p>
                    <p className="mt-2 text-sm font-medium text-gray-800">{humanize(selected.type)}</p>
                    <p className="mt-2 text-sm leading-relaxed text-gray-600">{selected.reason}</p>
                  </div>
                  <div className="rounded-lg border border-gray-200 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                      Investigation Notes
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-gray-600">
                      {selected.investigation_notes || 'No investigation notes have been added.'}
                    </p>
                  </div>
                </div>

                {selected.status === 'RESOLVED' ? (
                  <div className="rounded-lg border border-green-200 bg-green-50/60 p-5">
                    <div className="flex items-center gap-2 text-green-800">
                      <CheckCircle className="h-5 w-5" />
                      <h3 className="font-semibold">Decision completed</h3>
                    </div>
                    <div className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
                      <div><p className="text-xs text-gray-500">Decision</p><p className="mt-1 font-medium">{humanize(selected.decision)}</p></div>
                      <div><p className="text-xs text-gray-500">Approved adjustment</p><p className="mt-1 font-medium">{money(selected.approved_amount)}</p></div>
                      <div><p className="text-xs text-gray-500">Remaining balance</p><p className="mt-1 font-medium">{money(selected.remaining_balance)}</p></div>
                    </div>
                    <div className="mt-4 border-t border-green-200 pt-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-green-700">Customer response</p>
                      <p className="mt-2 text-sm leading-relaxed text-gray-700">{selected.team_response}</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="grid gap-4 xl:grid-cols-2">
                      <div className="rounded-lg border border-gray-200 p-4">
                        <h3 className="flex items-center gap-2 text-sm font-semibold">
                          <UserCheck className="h-4 w-4 text-blue-600" /> Assignment and investigation
                        </h3>
                        <label className="mt-4 block text-xs font-medium text-gray-600">Owner</label>
                        <div className="mt-1 flex gap-2">
                          <input value={owner} onChange={(event) => setOwner(event.target.value)} className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                          <button onClick={assign} disabled={saving || !owner.trim()} className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">Start Review</button>
                        </div>
                        <div className="mt-4 grid gap-2 sm:grid-cols-2">
                          <input value={investigator} onChange={(event) => setInvestigator(event.target.value)} placeholder="Investigator" className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                          <input value={investigationNote} onChange={(event) => setInvestigationNote(event.target.value)} placeholder="Investigation note" className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                        </div>
                        <button onClick={addNote} disabled={saving || !investigationNote.trim()} className="mt-2 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">Add Note</button>
                      </div>

                      <div className="rounded-lg border border-blue-200 bg-blue-50/30 p-4">
                        <h3 className="flex items-center gap-2 text-sm font-semibold">
                          <MessageSquare className="h-4 w-4 text-blue-600" /> Team decision
                        </h3>
                        <label className="mt-4 block text-xs font-medium text-gray-600">Decision</label>
                        <select value={decision} onChange={(event) => setDecision(event.target.value as ResolutionDecision)} className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                          <option value="accepted">Accept dispute</option>
                          <option value="partially_accepted">Partially accept</option>
                          <option value="rejected">Reject dispute</option>
                          <option value="more_information_required">Request more information</option>
                        </select>

                        {decision === 'partially_accepted' && (
                          <div className="mt-3">
                            <label className="block text-xs font-medium text-gray-600">Approved adjustment</label>
                            <input type="number" min="0" max={selected.amount} step="0.01" value={approvedAmount} onChange={(event) => setApprovedAmount(event.target.value)} className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                          </div>
                        )}

                        <label className="mt-3 block text-xs font-medium text-gray-600">Response to customer</label>
                        <textarea value={teamResponse} onChange={(event) => setTeamResponse(event.target.value)} rows={4} placeholder="Explain the decision and what happens next…" className="mt-1 w-full resize-none rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />

                        <div className="mt-3 grid gap-2 sm:grid-cols-2">
                          <input value={resolvedBy} onChange={(event) => setResolvedBy(event.target.value)} placeholder="Resolved by" className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                          <input value={resolutionNotes} onChange={(event) => setResolutionNotes(event.target.value)} placeholder="Internal resolution notes" className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                        </div>

                        <button onClick={resolve} disabled={saving || !teamResponse.trim()} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
                          <ClipboardCheck className="h-4 w-4" />
                          {decision === 'more_information_required' ? 'Send Information Request' : 'Submit Decision'}
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}
