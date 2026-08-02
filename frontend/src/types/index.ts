export interface Customer {
  customer_id: string
  name: string
  parent_customer_id: string | null
  segment: 'strategic' | 'mid_tier' | 'small'
  strategic: boolean
  credit_limit: number
  annual_revenue: number
  payment_terms: string
  contact_name: string
  contact_email: string
  avg_days_to_pay: number
}

export interface Invoice {
  invoice_id: string
  customer_id: string
  amount: number
  issue_date: string
  due_date: string
  status: string
  amount_paid: number
  paid_date: string | null
  days_overdue?: number
  days_until_due?: number
  is_overdue?: boolean
}

export interface Payment {
  payment_id: string
  customer_id: string
  invoice_id: string
  amount: number
  date: string
  method: string
}

export interface Communication {
  comm_id: string
  customer_id: string
  invoice_id: string
  direction: 'inbound' | 'outbound'
  type: string
  date: string
  content: string
  status: string
}

export interface Workflow {
  workflow_id: string
  invoice_id: string
  customer_id: string
  status: string
  plan_json?: string
  plan?: any
  reasoning: string
  confidence: number
  reason_code: string
  last_updated: string
}

export interface Activity {
  activity_id: string
  customer_id: string
  invoice_id: string
  type: string
  date: string
  details: string
  outcome: string
}

export interface CallTask {
  activity_id: string
  customer_id: string
  customer_name: string
  invoice_id: string
  details: string
  date: string
  script: string
}

export interface AgentResult {
  date: string
  cycle_number: number
  iterations: number
  tool_calls: number
  tool_calls_log: Array<{tool: string, input: any, result_preview: string}>
  agent_reasoning: string
  status: string
}

export interface SystemState {
  current_date: string
  last_cycle_date: string | null
  cycle_count: number
}

export interface AgingSummary {
  aging: Record<string, number>
  total: number
  current_date: string
}

export interface CreditExposure {
  customer_id: string
  credit_limit: number
  current_exposure: number
  available_credit: number
  percentage_used: number
  status: string
}

export interface DisputeCase {
  dispute_id: string
  customer_id: string
  customer_name: string
  invoice_id: string
  type: string
  amount: number
  reason: string
  status: 'OPEN' | 'UNDER_REVIEW' | 'NEEDS_INFORMATION' | 'RESOLVED'
  owner?: string
  created_date: string
  assigned_date?: string
  investigation_notes?: string
  decision?: string
  approved_amount?: number
  team_response?: string
  resolved_by?: string
  resolved_date?: string
  remaining_balance?: number
  updated_date?: string
  invoice_amount: number
  amount_paid: number
  outstanding_amount: number
  due_date?: string
}

export interface RoleNotification {
  notification_id: string
  event_type: string
  title: string
  message: string
  date: string
  customer_id: string
  customer_name: string
  invoice_id?: string
  dispute_id?: string
  activity_id?: string
  status?: string
  severity: 'info' | 'warning' | 'urgent' | 'success'
  action_required: boolean
  target_url: string
}
