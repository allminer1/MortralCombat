import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { FormValues, Prediction } from './spec'

/** The last calculation: what was entered, what came back, and when. */
export interface LastCalculation {
  values: FormValues
  prediction: Prediction
  at: Date
}

interface Session {
  last: LastCalculation | null
  setLast: (last: LastCalculation | null) => void
}

const SessionContext = createContext<Session | null>(null)

/** Held in memory only: clinical inputs are never written to the URL or to browser
 *  storage, so they are gone when the tab is closed or reloaded. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [last, setLast] = useState<LastCalculation | null>(null)
  const value = useMemo(() => ({ last, setLast }), [last])
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): Session {
  const session = useContext(SessionContext)
  if (!session) throw new Error('useSession outside SessionProvider')
  return session
}
