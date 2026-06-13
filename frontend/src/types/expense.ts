// Mirrors backend/schemas/expenses.py

export interface ExpenseOut {
  id: string
  description: string
  amount: number
  date: string
  category: string
  receipt_doc_id: string | null
  recoverable: boolean
  created_at: string
}

export interface ExpenseCreate {
  description: string
  amount: number
  date: string
  category: string
  receipt_doc_id?: string | null
  recoverable?: boolean
}

export type ExpenseUpdate = Partial<ExpenseCreate>
