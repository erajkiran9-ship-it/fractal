import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Send, DollarSign, AlertTriangle, FileText, MessageSquare } from 'lucide-react'
import api from '../api/client'
import { Customer, Invoice, Payment, Communication, CreditExposure } from '../types/index'

interface Dispute {
  dispute_id?: string
  customer_id: string
  invoice_id: string
  type: string
  amount: number
  reason: string
  status?: string
  created_date?: string
  updated_date?: string
  team_response?: string
  decision?: string
  remaining_balance?: number
}

export default function CustomerPortal() {
  const { customerId } = useParams<{ customerId: string }>()
  const [searchParams] = useSearchParams()
  const focusedSection = searchParams.get('section')
  const focusedInvoiceId = searchParams.get('invoiceId')
  const focusedDisputeId = searchParams.get('disputeId')

  const [customer, setCustomer] = useState<Customer | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [payments, setPayments] = useState<Payment[]>([])
  const [communications, setCommunications] = useState<Communication[]>([])
  const [creditExposure, setCreditExposure] = useState<CreditExposure | null>(null)
  const [disputes, setDisputes] = useState<Dispute[]>([])

  const [loading, setLoading] = useState(true)
  const [replyText, setReplyText] = useState('')
  const [sendingReply, setSendingReply] = useState(false)

  // Pay Now modal state
  const [payingInvoiceId, setPayingInvoiceId] = useState<string | null>(null)
  const [payAmount, setPayAmount] = useState('')
  const [submittingPayment, setSubmittingPayment] = useState(false)

  // Dispute modal state
  const [disputeInvoiceId, setDisputeInvoiceId] = useState<string | null>(null)
  const [disputeType, setDisputeType] = useState('pricing_dispute')
  const [disputeAmount, setDisputeAmount] = useState('')
  const [disputeReason, setDisputeReason] = useState('')
  const [submittingDispute, setSubmittingDispute] = useState(false)

  const fetchCustomer = useCallback(async () => {
    try {
      const res = await api.get(`/customers/${customerId}`)
      setCustomer(res.data.customer)
    } catch (err) {
      console.error('Failed to fetch customer', err)
    }
  }, [customerId])

  const fetchInvoices = useCallback(async () => {
    try {
      const res = await api.get(`/invoices/customer/${customerId}`)
      setInvoices(res.data.invoices)
    } catch (err) {
      console.error('Failed to fetch invoices', err)
    }
  }, [customerId])

  const fetchPayments = useCallback(async () => {
    try {
      const res = await api.get(`/payments/customer/${customerId}`)
      setPayments(res.data.payments)
    } catch (err) {
      console.error('Failed to fetch payments', err)
    }
  }, [customerId])

  const fetchCommunications = useCallback(async () => {
    try {
      const res = await api.get(`/communications/customer/${customerId}`)
      setCommunications(res.data.communications)
    } catch (err) {
      console.error('Failed to fetch communications', err)
    }
  }, [customerId])

  const fetchCreditExposure = useCallback(async () => {
    try {
      const res = await api.get('/simulation/credit-exposure')
      const match = res.data.credit_exposure.find(
        (c: CreditExposure) => c.customer_id === customerId
      )
      if (match) setCreditExposure(match)
    } catch (err) {
      console.error('Failed to fetch credit exposure', err)
    }
  }, [customerId])

  const fetchDisputes = useCallback(async () => {
    try {
      const res = await api.get(`/disputes/customer/${customerId}`)
      setDisputes(res.data.disputes)
    } catch (err) {
      // endpoint may not exist yet
      setDisputes([])
    }
  }, [customerId])

  const fetchAll = useCallback(async () => {
    setLoading(true)
    await Promise.all([
      fetchCustomer(),
      fetchInvoices(),
      fetchPayments(),
      fetchCommunications(),
      fetchCreditExposure(),
      fetchDisputes(),
    ])
    setLoading(false)
  }, [fetchCustomer, fetchInvoices, fetchPayments, fetchCommunications, fetchCreditExposure, fetchDisputes])

  useEffect(() => {
    if (customerId) fetchAll()
  }, [customerId, fetchAll])

  useEffect(() => {
    if (loading || !focusedSection) return
    window.setTimeout(() => {
      document.getElementById(`customer-section-${focusedSection}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }, 50)
  }, [focusedSection, loading])

  // Derived data
  const openInvoices = invoices.filter((inv) => inv.status !== 'CLOSED' && inv.status !== 'PAID')
  const totalDue = openInvoices.reduce((sum, inv) => sum + (inv.amount - inv.amount_paid), 0)
  const overdueAmount = openInvoices
    .filter((inv) => inv.is_overdue || inv.status === 'OVERDUE')
    .reduce((sum, inv) => sum + (inv.amount - inv.amount_paid), 0)
  const openDisputeCount = disputes.filter(
    (d) => !['RESOLVED', 'CLOSED'].includes(String(d.status || '').toUpperCase())
  ).length
  const mostRecentOpenInvoice = openInvoices.length > 0 ? openInvoices[0] : null

  // Actions
  const handlePay = async () => {
    if (!payingInvoiceId || !payAmount) return
    setSubmittingPayment(true)
    try {
      await api.post('/payments', {
        customer_id: customerId,
        invoice_id: payingInvoiceId,
        amount: parseFloat(payAmount),
      })
      setPayingInvoiceId(null)
      setPayAmount('')
      await Promise.all([fetchInvoices(), fetchPayments()])
    } catch (err) {
      console.error('Payment failed', err)
    } finally {
      setSubmittingPayment(false)
    }
  }

  const handleDispute = async () => {
    if (!disputeInvoiceId || !disputeReason) return
    setSubmittingDispute(true)
    try {
      await api.post('/disputes', {
        customer_id: customerId,
        invoice_id: disputeInvoiceId,
        type: disputeType,
        amount: parseFloat(disputeAmount) || 0,
        reason: disputeReason,
      })
      setDisputeInvoiceId(null)
      setDisputeType('pricing_dispute')
      setDisputeAmount('')
      setDisputeReason('')
      await fetchDisputes()
    } catch (err) {
      console.error('Dispute submission failed', err)
    } finally {
      setSubmittingDispute(false)
    }
  }

  const handleReply = async () => {
    if (!replyText.trim()) return
    setSendingReply(true)
    try {
      await api.post('/communications/reply', {
        customer_id: customerId,
        invoice_id: mostRecentOpenInvoice?.invoice_id || '',
        content: replyText,
      })
      setReplyText('')
      await fetchCommunications()
    } catch (err) {
      console.error('Reply failed', err)
    } finally {
      setSendingReply(false)
    }
  }

  const getStatusBadge = (invoice: Invoice) => {
    if (invoice.status === 'PAID') {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">PAID</span>
    }
    if (invoice.is_overdue || invoice.status === 'OVERDUE') {
      return <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">OVERDUE</span>
    }
    return <span className="px-2 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800">DUE SOON</span>
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-500 text-lg">Loading portal...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to={`/customer/${customerId}`} className="text-gray-500 hover:text-gray-700">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Collections Portal</h1>
              {customer && (
                <p className="text-sm text-gray-600">
                  Welcome, {customer.contact_name} - {customer.name}
                </p>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Account Summary */}
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Account Summary</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                <DollarSign className="w-4 h-4" />
                Total Due
              </div>
              <div className="text-2xl font-bold text-gray-900">${totalDue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                <AlertTriangle className="w-4 h-4" />
                Overdue
              </div>
              <div className="text-2xl font-bold text-red-600">${overdueAmount.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                <DollarSign className="w-4 h-4" />
                Credit Used
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {creditExposure ? `${creditExposure.percentage_used.toFixed(1)}%` : 'N/A'}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                <FileText className="w-4 h-4" />
                Open Disputes
              </div>
              <div className="text-2xl font-bold text-gray-900">{openDisputeCount}</div>
            </div>
          </div>
        </section>

        {/* Open Invoices */}
        <section id="customer-section-invoices" className="scroll-mt-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Open Invoices</h2>
          {openInvoices.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6 text-center text-gray-500">
              No open invoices.
            </div>
          ) : (
            <div className="space-y-3">
              {openInvoices.map((inv) => (
                <div
                  id={`customer-invoice-${inv.invoice_id}`}
                  key={inv.invoice_id}
                  className={`bg-white rounded-lg border p-4 ${
                    inv.invoice_id === focusedInvoiceId
                      ? 'border-blue-400 ring-2 ring-blue-100'
                      : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-4">
                      <div>
                        <span className="font-medium text-gray-900">{inv.invoice_id}</span>
                        <span className="ml-3 text-gray-600">
                          ${inv.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div className="text-sm text-gray-500">Due: {inv.due_date}</div>
                      {getStatusBadge(inv)}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => { setPayingInvoiceId(inv.invoice_id); setPayAmount('') }}
                        className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                      >
                        Pay Now
                      </button>
                      <button
                        onClick={() => { setDisputeInvoiceId(inv.invoice_id); setDisputeAmount(String(inv.amount - inv.amount_paid)) }}
                        className="px-3 py-1.5 text-sm bg-amber-600 text-white rounded hover:bg-amber-700"
                      >
                        Raise Dispute
                      </button>
                      <button
                        className="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      >
                        Upload Document
                      </button>
                    </div>
                  </div>

                  {/* Pay Now inline form */}
                  {payingInvoiceId === inv.invoice_id && (
                    <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-3">
                      <input
                        type="number"
                        placeholder="Amount"
                        value={payAmount}
                        onChange={(e) => setPayAmount(e.target.value)}
                        className="border border-gray-300 rounded px-3 py-1.5 text-sm w-40"
                      />
                      <button
                        onClick={handlePay}
                        disabled={submittingPayment || !payAmount}
                        className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                      >
                        {submittingPayment ? 'Processing...' : 'Submit Payment'}
                      </button>
                      <button
                        onClick={() => setPayingInvoiceId(null)}
                        className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  )}

                  {/* Dispute inline form */}
                  {disputeInvoiceId === inv.invoice_id && (
                    <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                      <div className="flex items-center gap-3 flex-wrap">
                        <select
                          value={disputeType}
                          onChange={(e) => setDisputeType(e.target.value)}
                          className="border border-gray-300 rounded px-3 py-1.5 text-sm"
                        >
                          <option value="pricing_dispute">Pricing Dispute</option>
                          <option value="quantity_dispute">Quantity Dispute</option>
                          <option value="quality_dispute">Quality Dispute</option>
                          <option value="delivery_dispute">Delivery Dispute</option>
                          <option value="trade_deduction">Trade Deduction</option>
                          <option value="promotional_allowance">Promotional Allowance</option>
                          <option value="damage_claim">Damage Claim</option>
                          <option value="duplicate_invoice">Duplicate Invoice</option>
                        </select>
                        <input
                          type="number"
                          placeholder="Amount"
                          value={disputeAmount}
                          onChange={(e) => setDisputeAmount(e.target.value)}
                          className="border border-gray-300 rounded px-3 py-1.5 text-sm w-32"
                        />
                      </div>
                      <textarea
                        placeholder="Reason for dispute..."
                        value={disputeReason}
                        onChange={(e) => setDisputeReason(e.target.value)}
                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                        rows={2}
                      />
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleDispute}
                          disabled={submittingDispute || !disputeReason}
                          className="px-3 py-1.5 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
                        >
                          {submittingDispute ? 'Submitting...' : 'Submit Dispute'}
                        </button>
                        <button
                          onClick={() => setDisputeInvoiceId(null)}
                          className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Disputes */}
        <section id="customer-section-disputes" className="scroll-mt-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Disputes
          </h2>
          {disputes.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-6 text-center text-gray-500">
              No disputes have been submitted.
            </div>
          ) : (
            <div className="space-y-3">
              {[...disputes]
                .sort((a, b) =>
                  String(b.updated_date || b.created_date || '').localeCompare(
                    String(a.updated_date || a.created_date || '')
                  )
                )
                .map((dispute) => {
                  const status = String(dispute.status || 'OPEN').toUpperCase()
                  const resolved = status === 'RESOLVED'
                  return (
                    <div
                      key={dispute.dispute_id || `${dispute.invoice_id}-${dispute.type}`}
                      className={`rounded-lg border bg-white p-4 ${
                        dispute.dispute_id === focusedDisputeId
                          ? 'border-amber-400 ring-2 ring-amber-100'
                          : 'border-gray-200'
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-gray-900">
                              {dispute.dispute_id || 'Dispute'}
                            </span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                                resolved
                                  ? 'bg-green-100 text-green-800'
                                  : status === 'NEEDS_INFORMATION'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-blue-100 text-blue-800'
                              }`}
                            >
                              {status.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-gray-500">
                            {dispute.invoice_id} · {dispute.type.replace(/_/g, ' ')}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-gray-900">
                            ${Number(dispute.amount || 0).toLocaleString('en-US', {
                              minimumFractionDigits: 2,
                            })}
                          </p>
                          <p className="mt-0.5 text-xs text-gray-400">
                            {dispute.updated_date || dispute.created_date || ''}
                          </p>
                        </div>
                      </div>
                      <p className="mt-3 text-sm text-gray-600">{dispute.reason}</p>
                      {dispute.team_response && (
                        <div className="mt-3 rounded-md bg-gray-50 px-3 py-2">
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                            Dispute team response
                          </p>
                          <p className="mt-1 text-sm text-gray-700">{dispute.team_response}</p>
                        </div>
                      )}
                    </div>
                  )
                })}
            </div>
          )}
        </section>

        {/* Messages / Communications */}
        <section id="customer-section-messages" className="scroll-mt-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Messages
          </h2>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="space-y-3 max-h-96 overflow-y-auto mb-4">
              {communications.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No messages yet.</p>
              ) : (
                [...communications]
                  .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
                  .map((comm) => (
                    <div
                      key={comm.comm_id}
                      className={`flex ${comm.direction === 'outbound' ? 'justify-start' : 'justify-end'}`}
                    >
                      <div
                        className={`max-w-[75%] rounded-lg px-4 py-2 ${
                          comm.direction === 'outbound'
                            ? 'bg-blue-100 text-blue-900'
                            : 'bg-green-100 text-green-900'
                        }`}
                      >
                        <div className="text-xs text-gray-500 mb-1">
                          {comm.direction === 'outbound' ? 'Collections' : 'You'} - {comm.date}
                        </div>
                        <div className="text-sm whitespace-pre-wrap">{comm.content}</div>
                      </div>
                    </div>
                  ))
              )}
            </div>
            <div className="flex items-center gap-2 border-t border-gray-100 pt-3">
              <input
                type="text"
                placeholder="Type your reply..."
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleReply() } }}
                className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
              />
              <button
                onClick={handleReply}
                disabled={sendingReply || !replyText.trim()}
                className="p-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </section>

        {/* Payment History */}
        <section id="customer-section-payments" className="scroll-mt-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Payment History</h2>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {payments.length === 0 ? (
              <div className="p-6 text-center text-gray-500">No payments recorded.</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Date</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Amount</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Invoice</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Method</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {payments.map((p) => (
                    <tr key={p.payment_id}>
                      <td className="px-4 py-2 text-gray-700">{p.date}</td>
                      <td className="px-4 py-2 text-gray-900 font-medium">
                        ${p.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-2 text-gray-700">{p.invoice_id}</td>
                      <td className="px-4 py-2 text-gray-700">{p.method}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
