import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as api from './api'

interface Auth {
  /** null while loading; false when the server has accounts switched off. */
  enabled: boolean | null
  user: api.Me | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  /** Called when the server says the session is gone. */
  expire: () => void
}

const AuthContext = createContext<Auth | null>(null)

/** Sign-in state. The session itself is an HttpOnly cookie the page cannot read; only
 *  the CSRF token is held here, in memory. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [user, setUser] = useState<api.Me | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      const features = await api.getFeatures().catch(() => ({ accounts: false }))
      const me = features.accounts ? await api.getMe().catch(() => null) : null
      if (!cancelled) {
        setUser(me)
        setEnabled(features.accounts)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    setUser(await api.login(email, password))
  }, [])
  const signOut = useCallback(async () => {
    if (user) await api.logout(user.csrf_token).catch(() => undefined)
    setUser(null)
  }, [user])
  const expire = useCallback(() => setUser(null), [])

  const value = useMemo(() => ({ enabled, user, signIn, signOut, expire }), [enabled, user, signIn, signOut, expire])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth outside AuthProvider')
  return auth
}
