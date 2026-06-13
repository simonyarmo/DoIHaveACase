export const US_STATES: { code: string; name: string }[] = [
  { code: "AL", name: "Alabama" },
  { code: "AK", name: "Alaska" },
  { code: "AZ", name: "Arizona" },
  { code: "AR", name: "Arkansas" },
  { code: "CA", name: "California" },
  { code: "CO", name: "Colorado" },
  { code: "CT", name: "Connecticut" },
  { code: "DE", name: "Delaware" },
  { code: "DC", name: "District of Columbia" },
  { code: "FL", name: "Florida" },
  { code: "GA", name: "Georgia" },
  { code: "HI", name: "Hawaii" },
  { code: "ID", name: "Idaho" },
  { code: "IL", name: "Illinois" },
  { code: "IN", name: "Indiana" },
  { code: "IA", name: "Iowa" },
  { code: "KS", name: "Kansas" },
  { code: "KY", name: "Kentucky" },
  { code: "LA", name: "Louisiana" },
  { code: "ME", name: "Maine" },
  { code: "MD", name: "Maryland" },
  { code: "MA", name: "Massachusetts" },
  { code: "MI", name: "Michigan" },
  { code: "MN", name: "Minnesota" },
  { code: "MS", name: "Mississippi" },
  { code: "MO", name: "Missouri" },
  { code: "MT", name: "Montana" },
  { code: "NE", name: "Nebraska" },
  { code: "NV", name: "Nevada" },
  { code: "NH", name: "New Hampshire" },
  { code: "NJ", name: "New Jersey" },
  { code: "NM", name: "New Mexico" },
  { code: "NY", name: "New York" },
  { code: "NC", name: "North Carolina" },
  { code: "ND", name: "North Dakota" },
  { code: "OH", name: "Ohio" },
  { code: "OK", name: "Oklahoma" },
  { code: "OR", name: "Oregon" },
  { code: "PA", name: "Pennsylvania" },
  { code: "RI", name: "Rhode Island" },
  { code: "SC", name: "South Carolina" },
  { code: "SD", name: "South Dakota" },
  { code: "TN", name: "Tennessee" },
  { code: "TX", name: "Texas" },
  { code: "UT", name: "Utah" },
  { code: "VT", name: "Vermont" },
  { code: "VA", name: "Virginia" },
  { code: "WA", name: "Washington" },
  { code: "WV", name: "West Virginia" },
  { code: "WI", name: "Wisconsin" },
  { code: "WY", name: "Wyoming" },
]

export const LANDLORD_TYPE_OPTIONS = [
  { value: "individual", label: "An individual person" },
  { value: "management_company", label: "A property management company" },
  { value: "not_sure", label: "Not sure" },
]

export const COMMUNICATION_OPTIONS = [
  { value: "none", label: "No response at all" },
  { value: "itemized_list", label: "Itemized list of deductions" },
  { value: "partial_explanation", label: "Some explanation, but not a full itemized list" },
  { value: "verbal_only", label: "Verbal explanation only (nothing in writing)" },
]

export const PROPERTY_TYPE_OPTIONS = [
  { value: "apartment", label: "Apartment" },
  { value: "house", label: "Single-family house" },
  { value: "condo", label: "Condo / townhouse" },
  { value: "duplex", label: "Duplex / multi-family" },
  { value: "other", label: "Other" },
]

export interface EvidenceUploadSpec {
  type: "move_in_inspection" | "move_out_inspection" | "photos_move_in" | "photos_move_out" | "communications" | "forwarding_proof" | "deposit_proof"
  label: string
  importance: "Required" | "Strongly recommended" | "If applicable"
  description: string
}

export const EVIDENCE_UPLOADS: EvidenceUploadSpec[] = [
  {
    type: "deposit_proof",
    label: "Proof of deposit payment",
    importance: "Required",
    description: "Receipt, cancelled check, bank statement, or money order showing you paid the deposit.",
  },
  {
    type: "move_in_inspection",
    label: "Move-in inspection report",
    importance: "Strongly recommended",
    description: "Any move-in condition checklist signed by you and/or the landlord.",
  },
  {
    type: "move_out_inspection",
    label: "Move-out inspection report",
    importance: "Strongly recommended",
    description: "Any move-out condition checklist or walkthrough notes.",
  },
  {
    type: "photos_move_in",
    label: "Move-in photos",
    importance: "Strongly recommended",
    description: "Photos showing the condition of the unit when you moved in.",
  },
  {
    type: "photos_move_out",
    label: "Move-out photos",
    importance: "Strongly recommended",
    description: "Photos showing the condition of the unit when you moved out.",
  },
  {
    type: "communications",
    label: "Written communications with landlord",
    importance: "Strongly recommended",
    description: "Emails, texts, or letters about the deposit, move-out, or repairs.",
  },
  {
    type: "forwarding_proof",
    label: "Proof of forwarding address",
    importance: "If applicable",
    description: "A copy of the letter, email, or form where you gave your landlord a forwarding address.",
  },
]

export const EXPENSE_CATEGORY_OPTIONS = [
  { value: "filing_fee", label: "Filing fee" },
  { value: "service_fee", label: "Service fee" },
  { value: "mail", label: "Mail / postage" },
  { value: "notary", label: "Notary" },
  { value: "other", label: "Other" },
]

// Tool names published over the progress WebSocket (agents/intake_agent.py),
// in the order the research agent runs them, with display copy for the
// research-progress panel.
export const RESEARCH_STEPS: { tool: string; label: string }[] = [
  { tool: "sos_lookup", label: "Verifying landlord entity via Secretary of State" },
  { tool: "state_law", label: "Loading security deposit law for your state" },
  { tool: "deadline_calculator", label: "Calculating deadline and days overdue" },
  { tool: "court_lookup", label: "Checking county court filing procedures" },
  { tool: "address_validator", label: "Validating landlord's service address" },
  { tool: "lease_parser", label: "Parsing your lease" },
  { tool: "assessment", label: "Running case assessment" },
]
