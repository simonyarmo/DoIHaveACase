// Mirrors backend/schemas/cases.py

export interface CaseOut {
  id: string
  status: string
  dispute_type: string
  state: string | null
  county: string | null
  created_at: string
}

export interface CaseDetailsOut {
  // Property
  property_address: string | null
  property_state: string | null
  property_county: string | null
  property_type: string | null

  // Landlord
  landlord_type: string | null
  landlord_name_as_entered: string | null
  landlord_legal_name: string | null
  landlord_sos_verified: boolean
  landlord_registered_agent: string | null
  landlord_address: string | null
  landlord_sos_status: string | null
  landlord_sos_lookup_date: string | null

  // Deposit
  deposit_amount: number | null
  amount_returned: number | null
  date_returned: string | null
  move_in_date: string | null
  move_out_date: string | null
  keys_returned_date: string | null
  forwarding_address: string | null
  forwarding_address_proof: boolean

  // Communication
  landlord_communication: string
  itemization_received: boolean
  itemization_date: string | null
  demand_letter_sent: boolean
  demand_letter_date: string | null
  demand_letter_delivery: string | null

  // Notice
  notice_provided: boolean | null
  notice_date: string | null
  notice_method: string | null
  notice_days: number | null
  lease_required_notice_days: number | null

  // Computed by research agent
  days_overdue: number | null
  deadline_date: string | null
  violation_confirmed: boolean | null
  bad_faith_indicators: Record<string, unknown> | null
  estimated_recovery_min: number | null
  estimated_recovery_max: number | null
  penalty_multiplier: number | null
}

// Partial update payload — Steps 2-4 send only the fields they collect.
export type CaseDetailsUpdate = Partial<
  Pick<
    CaseDetailsOut,
    | "property_address"
    | "property_state"
    | "property_county"
    | "property_type"
    | "landlord_type"
    | "landlord_name_as_entered"
    | "landlord_address"
    | "deposit_amount"
    | "amount_returned"
    | "date_returned"
    | "move_in_date"
    | "move_out_date"
    | "keys_returned_date"
    | "forwarding_address"
    | "forwarding_address_proof"
    | "landlord_communication"
    | "itemization_received"
    | "itemization_date"
    | "demand_letter_sent"
    | "demand_letter_date"
    | "demand_letter_delivery"
    | "notice_provided"
    | "notice_date"
    | "notice_method"
    | "notice_days"
  >
>

export interface TenantInfo {
  full_legal_name?: string | null
  address?: string | null
  phone?: string | null
}

export interface CaseUpdateRequest {
  state?: string | null
  county?: string | null
  tenant?: TenantInfo | null
  details?: CaseDetailsUpdate | null
}

export interface PartyOut {
  id: string
  role: string
  full_legal_name: string
  entity_type: string | null
  address: string | null
}

export interface DocumentOut {
  id: string
  type: string
  status: string
  file_name: string | null
  file_type: string | null
  file_size: number | null
  uploaded_at: string | null
}

export interface CaseDetailResponse {
  case: CaseOut
  details: CaseDetailsOut
  parties: PartyOut[]
  documents: DocumentOut[]
}

export interface SubmitResponse {
  status: string
  session_id: string
}

export type DocumentType =
  | "lease"
  | "move_in_inspection"
  | "move_out_inspection"
  | "photos_move_in"
  | "photos_move_out"
  | "communications"
  | "forwarding_proof"
  | "deposit_proof"

// Progress events published over /ws/cases/{case_id} (services/progress_bus.py)
export interface ProgressEvent {
  tool: string
  status: "running" | "complete" | "error"
  result?: unknown
  error?: string
}

// Messages received over /ws/cases/{case_id}
export type WsServerMessage =
  | ProgressEvent
  | { type: "token"; content: string }
  | { type: "done" }

export interface ConversationMessageOut {
  id: string
  role: string
  message_type: string
  content: string | null
  form_schema: DynamicFormSchema | null
  form_response: Record<string, unknown> | null
  created_at: string
}

export interface DynamicFormField {
  name: string
  label: string
  type: "text" | "number" | "date" | "select" | "checkbox" | "textarea"
  options?: string[]
  required?: boolean
}

export interface DynamicFormSchema {
  title?: string
  fields: DynamicFormField[]
}
