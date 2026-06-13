import { supabase } from "@/lib/supabase"
import type {
  AssessmentResponse,
  CaseDetailResponse,
  CaseOut,
  CaseSummary,
  CaseUpdateRequest,
  ConversationMessageOut,
  DocumentOut,
  DocumentType,
  SubmitResponse,
} from "@/types/case"
import type { ExpenseCreate, ExpenseOut, ExpenseUpdate } from "@/types/expense"
import type { UserOut } from "@/types/user"

const API_URL = import.meta.env.VITE_API_URL as string

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail))
    this.status = status
    this.detail = detail
  }
}

async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getAccessToken()
  const headers = new Headers(init?.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, headers })

  if (!response.ok) {
    let detail: unknown
    try {
      detail = (await response.json()).detail
    } catch {
      detail = response.statusText
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function createCase(): Promise<CaseOut> {
  return request<CaseOut>("/cases", { method: "POST" })
}

export async function listCases(): Promise<CaseSummary[]> {
  return request<CaseSummary[]>("/cases")
}

export async function getCase(caseId: string): Promise<CaseDetailResponse> {
  return request<CaseDetailResponse>(`/cases/${caseId}`)
}

export async function updateCase(caseId: string, payload: CaseUpdateRequest): Promise<CaseDetailResponse> {
  return request<CaseDetailResponse>(`/cases/${caseId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export async function uploadDocument(caseId: string, file: File, type: DocumentType): Promise<DocumentOut> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("type", type)
  return request<DocumentOut>(`/cases/${caseId}/documents`, { method: "POST", body: formData })
}

export async function submitCase(caseId: string): Promise<SubmitResponse> {
  return request<SubmitResponse>(`/cases/${caseId}/submit`, { method: "POST" })
}

export async function getCurrentUser(): Promise<UserOut> {
  return request<UserOut>("/auth/me")
}

export async function getMessages(caseId: string): Promise<ConversationMessageOut[]> {
  return request<ConversationMessageOut[]>(`/cases/${caseId}/messages`)
}

export async function getCaseSocketUrl(caseId: string): Promise<string> {
  const token = await getAccessToken()
  const wsBase = API_URL.replace(/^http/, "ws")
  return `${wsBase}/ws/cases/${caseId}?token=${encodeURIComponent(token ?? "")}`
}

export async function getAssessment(caseId: string): Promise<AssessmentResponse> {
  return request<AssessmentResponse>(`/cases/${caseId}/assessment`)
}

export async function refreshAssessment(caseId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/cases/${caseId}/assessment/refresh`, { method: "POST" })
}

export async function listExpenses(caseId: string): Promise<ExpenseOut[]> {
  return request<ExpenseOut[]>(`/cases/${caseId}/expenses`)
}

export async function createExpense(caseId: string, payload: ExpenseCreate): Promise<ExpenseOut> {
  return request<ExpenseOut>(`/cases/${caseId}/expenses`, { method: "POST", body: JSON.stringify(payload) })
}

export async function updateExpense(caseId: string, expenseId: string, payload: ExpenseUpdate): Promise<ExpenseOut> {
  return request<ExpenseOut>(`/cases/${caseId}/expenses/${expenseId}`, { method: "PUT", body: JSON.stringify(payload) })
}

export async function deleteExpense(caseId: string, expenseId: string): Promise<void> {
  return request<void>(`/cases/${caseId}/expenses/${expenseId}`, { method: "DELETE" })
}
