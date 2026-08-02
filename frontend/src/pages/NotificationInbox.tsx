import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  Bell,
  CheckCircle,
  ChevronRight,
  FileQuestion,
  Inbox,
  MessageSquare,
  Phone,
  RefreshCw,
  Scale,
  Users,
} from 'lucide-react'

import api from '../api/client'
import { RoleNotification } from '../types/index'

type InboxRole = 'disputes' | 'collector' | 'customer'

interface NotificationInboxProps {
  role: InboxRole
}

const roleConfig = {
  disputes: {
    title: 'Dispute Notifications',
    subtitle: 'New cases and dispute-team updates for the simulation day.',
    Icon: Scale,
    accent: 'text-blue-600 bg-blue-50',
  },
  collector: {
    title: 'Collector Notifications',
    subtitle: 'Call tasks and account events requiring collector awareness.',
    Icon: Phone,
    accent: 'text-indigo-600 bg-indigo-50',
  },
  customer: {
    title: 'Account Notifications',
    subtitle: 'Messages, payments, promises, and dispute updates for your account.',
    Icon: Bell,
    accent: 'text-sky-600 bg-sky-50',
  },
} as const

function severityClasses(severity: RoleNotification['severity']) {
  switch (severity) {
    case 'urgent':
      return 'border-red-200 bg-red-50/40 text-red-700'
    case 'warning':
      return 'border-amber-200 bg-amber-50/40 text-amber-700'
    case 'success':
      return 'border-green-200 bg-green-50/40 text-green-700'
    default:
      return 'border-blue-200 bg-blue-50/40 text-blue-700'
  }
}

function NotificationIcon({ notification }: { notification: RoleNotification }) {
  if (notification.severity === 'success') {
    return <CheckCircle className="h-5 w-5" />
  }
  if (notification.event_type.includes('message')) {
    return <MessageSquare className="h-5 w-5" />
  }
  if (notification.event_type.includes('call')) {
    return <Phone className="h-5 w-5" />
  }
  if (notification.event_type.includes('dispute')) {
    return <FileQuestion className="h-5 w-5" />
  }
  return <AlertCircle className="h-5 w-5" />
}

function humanize(value?: string) {
  if (!value) return ''
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export default function NotificationInbox({ role }: NotificationInboxProps) {
  const { customerId } = useParams<{ customerId: string }>()
  const navigate = useNavigate()
  const config = roleConfig[role]
  const [notifications, setNotifications] = useState<RoleNotification[]>([])
  const [currentDate, setCurrentDate] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const endpoint =
    role === 'customer'
      ? `/notifications/customer/${customerId}`
      : `/notifications/${role}`

  const workbenchUrl =
    role === 'disputes'
      ? '/disputes/workbench'
      : role === 'collector'
      ? '/collector/workbench'
      : `/customer/${customerId}/portal`

  const workbenchLabel =
    role === 'disputes'
      ? 'Open dispute desk'
      : role === 'collector'
      ? 'Open collector workbench'
      : 'Open full customer portal'

  const fetchNotifications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get(endpoint)
      setNotifications(response.data.notifications || [])
      setCurrentDate(response.data.date || '')
    } catch (requestError: any) {
      setError(
        requestError.response?.data?.detail || 'Unable to load notifications.'
      )
    } finally {
      setLoading(false)
    }
  }, [endpoint])

  useEffect(() => {
    fetchNotifications()
  }, [fetchNotifications])

  const actionRequired = notifications.filter(
    (notification) => notification.action_required
  ).length
  const distinctCustomers = useMemo(
    () => new Set(notifications.map((notification) => notification.customer_id)).size,
    [notifications]
  )

  const RoleIcon = config.Icon

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <Link
              to="/manager"
              className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
            >
              <ArrowLeft className="h-4 w-4" /> Manager
            </Link>
            <div className="h-7 w-px bg-gray-200" />
            <div className={`rounded-lg p-2 ${config.accent}`}>
              <RoleIcon className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">{config.title}</h1>
              <p className="mt-0.5 text-xs text-gray-500">{config.subtitle}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchNotifications}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
            <Link
              to={workbenchUrl}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              {workbenchLabel} <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-5 px-6 py-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              Simulation date
            </p>
            <p className="mt-1 text-lg font-semibold">{currentDate || '—'}</p>
          </div>
          <p className="text-sm text-gray-500">
            Each business event is shown separately, including multiple events on the same day.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {[
            ['Updates today', notifications.length, Inbox, 'text-blue-600 bg-blue-50'],
            ['Action required', actionRequired, AlertCircle, 'text-amber-600 bg-amber-50'],
            ['Customers affected', distinctCustomers, Users, 'text-violet-600 bg-violet-50'],
          ].map(([label, value, Icon, classes]) => {
            const SummaryIcon = Icon as typeof Inbox
            return (
              <div key={String(label)} className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                      {String(label)}
                    </p>
                    <p className="mt-1 text-2xl font-semibold">{String(value)}</p>
                  </div>
                  <div className={`rounded-lg p-2.5 ${String(classes)}`}>
                    <SummaryIcon className="h-5 w-5" />
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

        <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <div>
              <h2 className="font-semibold">Today&apos;s notifications</h2>
              <p className="mt-0.5 text-xs text-gray-500">
                Select an item to open its exact customer, invoice, task, or dispute context.
              </p>
            </div>
            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
              {notifications.length}
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-sm text-gray-400">
              Loading notifications…
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-12 text-center">
              <CheckCircle className="mx-auto h-10 w-10 text-green-500" />
              <p className="mt-3 font-medium text-gray-700">No updates for this simulation day</p>
              <p className="mt-1 text-sm text-gray-500">
                The full workbench remains available for previous and open records.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {notifications.map((notification) => (
                <button
                  key={notification.notification_id}
                  onClick={() => navigate(notification.target_url)}
                  className="group flex w-full items-start gap-4 px-5 py-4 text-left transition-colors hover:bg-gray-50"
                >
                  <div
                    className={`mt-0.5 rounded-lg border p-2.5 ${severityClasses(
                      notification.severity
                    )}`}
                  >
                    <NotificationIcon notification={notification} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{notification.title}</h3>
                      {notification.action_required && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
                          Action required
                        </span>
                      )}
                      {notification.status && (
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                          {humanize(notification.status)}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-600">{notification.message}</p>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
                      <span className="font-medium text-gray-600">
                        {notification.customer_name}
                      </span>
                      {notification.invoice_id && <span>{notification.invoice_id}</span>}
                      {notification.dispute_id && <span>{notification.dispute_id}</span>}
                      <span>{notification.date}</span>
                    </div>
                  </div>
                  <ChevronRight className="mt-3 h-5 w-5 flex-none text-gray-300 transition-transform group-hover:translate-x-0.5 group-hover:text-gray-500" />
                </button>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
