import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

interface IntakeState {
  caseId: string | null
  setCaseId: (id: string) => void
  reset: () => void
}

/** Tracks the in-progress case across the 5-step intake wizard. Persisted to
 * sessionStorage so a page refresh mid-wizard doesn't orphan the case. */
export const useIntakeStore = create<IntakeState>()(
  persist(
    (set) => ({
      caseId: null,
      setCaseId: (id) => set({ caseId: id }),
      reset: () => set({ caseId: null }),
    }),
    { name: "depositshield-intake", storage: createJSONStorage(() => sessionStorage) }
  )
)
