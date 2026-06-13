import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { EXPENSE_CATEGORY_OPTIONS } from "@/lib/constants"
import { createExpense, deleteExpense, listExpenses } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { ExpenseCreate } from "@/types/expense"

interface ExpenseTrackerProps {
  caseId: string
}

function emptyForm(): ExpenseCreate {
  return {
    description: "",
    amount: 0,
    date: new Date().toISOString().slice(0, 10),
    category: EXPENSE_CATEGORY_OPTIONS[0].value,
    recoverable: true,
  }
}

export function ExpenseTracker({ caseId }: ExpenseTrackerProps) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<ExpenseCreate>(emptyForm)

  const { data: expenses } = useQuery({
    queryKey: ["expenses", caseId],
    queryFn: () => listExpenses(caseId),
  })

  const createMutation = useMutation({
    mutationFn: (payload: ExpenseCreate) => createExpense(caseId, payload),
    onSuccess: async () => {
      setForm(emptyForm())
      await queryClient.invalidateQueries({ queryKey: ["expenses", caseId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (expenseId: string) => deleteExpense(caseId, expenseId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", caseId] })
    },
  })

  const total = (expenses ?? []).filter((e) => e.recoverable).reduce((sum, e) => sum + e.amount, 0)

  return (
    <div className="space-y-3 rounded-md border border-border p-4">
      <h2 className="font-medium">Expenses</h2>

      {expenses && expenses.length > 0 && (
        <ul className="space-y-2">
          {expenses.map((expense) => (
            <li key={expense.id} className="flex items-start justify-between gap-2 text-sm">
              <div>
                <p className={cn(!expense.recoverable && "text-muted-foreground line-through")}>{expense.description}</p>
                <p className="text-xs text-muted-foreground">
                  {expense.date} · {EXPENSE_CATEGORY_OPTIONS.find((c) => c.value === expense.category)?.label ?? expense.category}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">${expense.amount.toFixed(2)}</span>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(expense.id)}
                  className="text-muted-foreground hover:text-destructive"
                  aria-label="Delete expense"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (!form.description || !form.amount) return
          createMutation.mutate(form)
        }}
        className="space-y-2 border-t border-border pt-3"
      >
        <Input
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
        />
        <div className="grid grid-cols-2 gap-2">
          <Input
            type="number"
            step="0.01"
            min="0"
            placeholder="Amount"
            value={form.amount || ""}
            onChange={(e) => setForm((f) => ({ ...f, amount: Number(e.target.value) }))}
          />
          <Input type="date" value={form.date} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} />
        </div>
        <div className="flex items-center gap-2">
          <Select
            className="flex-1"
            value={form.category}
            onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
          >
            {EXPENSE_CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
          <label className="flex items-center gap-2 whitespace-nowrap text-sm">
            <Checkbox
              checked={form.recoverable}
              onChange={(e) => setForm((f) => ({ ...f, recoverable: e.target.checked }))}
            />
            Recoverable
          </label>
        </div>
        <Button type="submit" size="sm" variant="outline" className="w-full" disabled={createMutation.isPending}>
          <Plus className="h-4 w-4" /> Add expense
        </Button>
      </form>

      <div className="flex items-center justify-between border-t border-border pt-3 text-sm font-medium">
        <span>Total recoverable</span>
        <span>${total.toFixed(2)}</span>
      </div>
    </div>
  )
}
